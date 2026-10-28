"""Exercise the real JSON transport against a subprocess with fake motor hardware."""
from dataclasses import asdict
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

import pytest

from robots_open_duck.config import HOME, JOINT_ORDER, OPEN_DUCK_ACTUATOR_SPECS, OpenDuckNodeConfig
from robots_open_duck.sdk import OpenDuckSDK
from robots_open_duck import ssh_io


@pytest.fixture
def bridge_config(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    package = runtime / "mini_bdx_runtime" / "mini_bdx_runtime"
    package.mkdir(parents=True)
    (package / "__init__.py").touch()
    trace = tmp_path / "trace"
    config_path = tmp_path / "duck.json"
    offsets = {name: 0.1 for name in JOINT_ORDER}
    config_path.write_text(json.dumps({"joints_offsets": offsets, "trace": str(trace)}))
    (package / "duck_config.py").write_text(
        "import json\nclass DuckConfig:\n"
        " def __init__(self, config_json_path):\n"
        "  self.data=json.load(open(config_json_path))\n"
        "  self.joints_offset=self.data['joints_offsets']\n"
    )
    specs = [asdict(spec) for spec in OPEN_DUCK_ACTUATOR_SPECS]
    (package / "rustypot_position_hwi.py").write_text(
        "from pathlib import Path\nimport os\n"
        f"SPECS={specs!r}\n"
        "class IO:\n"
        " def __init__(self, hwi):\n"
        "  self.hwi=hwi\n"
        "  self.values={s['motor_id']:hwi.initial.get(s['name'],s['home'])+hwi.joints_offsets[s['name']] for s in SPECS}\n"
        " def read_present_position(self, ids): return [self.values[i] for i in ids]\n"
        " def write_goal_position(self, ids, values): self.values.update(zip(ids,values))\n"
        " def enable_torque(self, ids): self.hwi.trace('on')\n"
        "class HWI:\n"
        " def __init__(self, config, port):\n"
        "  self.joints={s['name']:s['motor_id'] for s in SPECS}\n"
        "  self.init_pos={s['name']:s['home'] for s in SPECS}\n"
        "  self.joints_offsets=config.joints_offset\n"
        "  self.initial=config.data.get('initial_positions',{})\n"
        "  self.noisy=config.data.get('native_logs',False)\n"
        "  self.path=Path(config.data['trace'])\n"
        "  self.io=IO(self)\n"
        " def trace(self, text):\n"
        "  with self.path.open('a') as f: f.write(text+'\\n')\n"
        " def set_kps(self, values): self.trace('kps')\n"
        " def set_kds(self, values):\n"
        "  self.trace('kds')\n"
        "  if self.noisy:\n"
        "   print('Python SDK diagnostic',flush=True)\n"
        "   os.write(1,b'd_coefficient: [0, 0]\\n')\n"
        " def turn_off(self): self.trace('off')\n"
    )
    actual_popen = subprocess.Popen

    def run_agent_instead_of_ssh(argv, **kwargs):
        # Keep the production source/JSON framing; replace only SSH and hardware.
        import sys
        remote = shlex.split(argv[-1])
        return actual_popen([sys.executable, *remote[1:]], **kwargs)

    monkeypatch.setattr(ssh_io.subprocess, "Popen", run_agent_instead_of_ssh)

    def config(action=True, timeout=1.0):
        return OpenDuckNodeConfig(
            backend="ssh", ssh_target="test.invalid", remote_python=sys.executable,
            remote_runtime_dir=str(runtime), duck_config_path=str(config_path),
            port=str(tmp_path / "fake-serial"), enable_action=action,
            command_timeout_seconds=timeout,
        )
    return config, trace


def test_read_only_bridge_does_not_change_gains_or_torque(bridge_config):
    config, trace = bridge_config
    sdk = OpenDuckSDK(config(action=False))
    sdk.connect()
    assert sdk.read_positions() == pytest.approx(HOME)
    sdk.disconnect()
    assert not trace.exists()


def test_remote_calibration_applied_once_and_shutdown_releases_torque(bridge_config):
    config, trace = bridge_config
    sdk = OpenDuckSDK(config())
    sdk.connect()
    targets = list(HOME)
    targets[0] += 0.03
    sdk.write_positions(targets)
    assert sdk.read_positions() == pytest.approx(targets)
    sdk.disconnect()
    assert trace.read_text().splitlines() == ["kps", "kds", "on", "off"]


def test_native_sdk_stdout_cannot_corrupt_rpc(bridge_config, capfd):
    config_factory, trace = bridge_config
    config = config_factory()
    path = Path(config.duck_config_path)
    data = json.loads(path.read_text())
    data["native_logs"] = True
    path.write_text(json.dumps(data))
    sdk = OpenDuckSDK(config)
    sdk.connect()
    try:
        sdk.write_positions(list(HOME))
        assert sdk.read_positions() == pytest.approx(HOME)
    finally:
        sdk.disconnect()
    captured = capfd.readouterr()
    assert "d_coefficient" in captured.err
    assert "Python SDK diagnostic" in captured.err
    assert trace.read_text().splitlines()[-1] == "off"


def test_outside_startup_pose_recovers_through_driver_and_bridge(bridge_config):
    import importlib.util
    from forge_msgs import JointCommand
    from robots_open_duck.driver import OpenDuckDriver
    config_factory, trace = bridge_config
    config = config_factory()
    initial = [joint.lower - 0.05 if index % 2 else joint.upper + 0.05
               for index, joint in enumerate(OPEN_DUCK_ACTUATOR_SPECS)]
    initial[6] = -1.388
    path = Path(config.duck_config_path)
    data = json.loads(path.read_text())
    data["initial_positions"] = dict(zip(JOINT_ORDER, initial))
    path.write_text(json.dumps(data))
    plan_path = Path(__file__).parents[1] / "examples/03_workflows/real_basic_motion/motion_plan.py"
    spec = importlib.util.spec_from_file_location("recovery_motion_plan", plan_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    driver = OpenDuckDriver(config)
    driver.connect()
    try:
        driver.prepare_actions()
        plan = module.MotionPlan(driver.get_state().position)
        previous, _ = plan.sample(0)
        for step in range(int(plan.home_duration / 0.05) + 2):
            targets, _ = plan.sample(min(step * 0.05, plan.home_duration))
            for old, value, joint in zip(previous, targets, OPEN_DUCK_ACTUATOR_SPECS):
                assert min(joint.lower, old) - 1e-9 <= value <= max(joint.upper, old) + 1e-9
                assert abs(value - old) < 0.08
            driver.set_command(JointCommand(
                name=list(JOINT_ORDER), position=targets,
                velocity=[0.] * 14, effort=[0.] * 14, kp=[0.] * 14, kd=[0.] * 14,
            ))
            previous = targets
        assert driver.get_state().position == pytest.approx(HOME)
    finally:
        driver.disconnect()
    assert trace.read_text().splitlines()[-1] == "off"


def test_invalid_step_is_rejected_and_motor_is_released(bridge_config):
    config, trace = bridge_config
    sdk = OpenDuckSDK(config())
    sdk.connect()
    targets = list(HOME)
    targets[0] += 0.30
    with pytest.raises(RuntimeError, match="position step"):
        sdk.write_positions(targets)
    try:
        sdk.disconnect()
    except (ConnectionError, BrokenPipeError):
        pass
    assert trace.read_text().splitlines()[-1] == "off"


def test_calibrated_sweeps_reach_all_permitted_extremes(bridge_config):
    config, trace = bridge_config
    sdk = OpenDuckSDK(config())
    sdk.connect()
    targets = list(HOME)
    try:
        for index, spec in enumerate(OPEN_DUCK_ACTUATOR_SPECS):
            for goal in (max(spec.lower, HOME[index] - 0.30),
                         min(spec.upper, HOME[index] + 0.30), HOME[index]):
                initial = targets[index]
                for step in range(1, 21):
                    targets[index] = initial + (goal - initial) * step / 20
                    sdk.write_positions(targets)
                assert sdk.read_positions() == pytest.approx(targets)
    finally:
        sdk.disconnect()
    assert trace.read_text().splitlines()[-1] == "off"


def test_watchdog_stops_even_when_pc_sends_no_shutdown_request(bridge_config):
    config, trace = bridge_config
    sdk = OpenDuckSDK(config(timeout=0.1))
    sdk.connect()
    sdk.write_positions(list(HOME))
    time.sleep(0.3)
    assert trace.read_text().splitlines()[-1] == "off"
    with pytest.raises((RuntimeError, ConnectionError, BrokenPipeError)):
        sdk.read_positions()
    try:
        sdk.disconnect()
    except (RuntimeError, ConnectionError, BrokenPipeError):
        pass


def test_motion_plan_all_targets_in_limits_and_only_one_joint_changes():
    import importlib.util
    path = Path(__file__).parents[1] / "examples/03_workflows/real_basic_motion/motion_plan.py"
    spec = importlib.util.spec_from_file_location("hardware_motion_plan", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    initial = [value + 0.02 for value in HOME]
    plan = module.MotionPlan(initial)
    previous, _ = plan.sample(0)
    for step in range(1, int(plan.duration / 0.02) + 2):
        targets, _ = plan.sample(step * 0.02)
        for value, joint in zip(targets, OPEN_DUCK_ACTUATOR_SPECS):
            assert joint.lower <= value <= joint.upper
        assert sum(abs(a - b) > 1e-7 for a, b in zip(previous, targets)) <= 1
        assert max(abs(a - b) for a, b in zip(previous, targets)) < 0.08
        previous = targets
    assert previous == list(HOME)


def test_motion_source_waits_for_feedback_before_advancing(monkeypatch):
    import importlib.util
    from forge_msgs import JointCommand, JointState
    workflow = Path(__file__).parents[1] / "examples/03_workflows/real_basic_motion"
    monkeypatch.syspath_prepend(str(workflow))
    monkeypatch.delenv("OPEN_DUCK_READ_ONLY", raising=False)
    spec = importlib.util.spec_from_file_location("feedback_paced_source", workflow / "motion_source.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    initial = list(HOME)
    initial[6] = -1.388
    feedback = {"type": "INPUT", "id": "proprio_state",
                "value": JointState(name=list(JOINT_ORDER), position=initial).to_arrow()}
    events = []
    for _ in range(3):
        events.append(feedback)
        events.extend({"type": "INPUT", "id": "tick"} for _ in range(20))

    class Node:
        outputs = []
        def __iter__(self): return iter(events)
        def send_output(self, name, value): self.outputs.append((name, value))

    node = Node()
    # Feedback gaps reach 2 seconds: tolerate the workflow's configured 3-second
    # deadline, while still advancing virtual trajectory time by at most 0.05s.
    clock = iter(100.0 + step * 0.1 for step in range(1000))
    monkeypatch.setattr(module, "Node", lambda: node)
    from types import SimpleNamespace
    monkeypatch.setattr(module, "load_config", lambda: SimpleNamespace(command_timeout_seconds=3.0))
    monkeypatch.setattr(module.time, "monotonic", lambda: next(clock))
    module.main()
    commands = [JointCommand.from_arrow(value).position for name, value in node.outputs if name == "action"]
    assert len(commands) == 3  # 60 timer events, only 3 fresh feedback frames.
    assert commands[0] == pytest.approx(initial)
    assert commands[0][6] < commands[1][6] < commands[2][6]
    assert max(abs(a - b) for a, b in zip(commands[1], commands[2])) < 0.08


def test_dora_read_only_workflow_routes_feedback_and_exits(bridge_config, tmp_path, monkeypatch):
    import os
    import signal
    config_factory, trace = bridge_config
    config = config_factory(action=False)
    monkeypatch.undo()  # Dora launches real subprocesses; only the SSH executable is replaced.
    repo = Path(__file__).parents[1]
    dora = repo.parents[1] / "forge_runtime/.venv/bin/dora"
    if not dora.exists():
        pytest.skip("Forge runtime Dora CLI is not present")
    ssh = tmp_path / "bin" / "ssh"
    ssh.parent.mkdir()
    overrides = {"runtime_dir": config.remote_runtime_dir,
                 "duck_config_path": config.duck_config_path, "port": config.port}
    ssh.write_text(
        f"#!{repo / '.venv/bin/python'}\n"
        "import json,os,shlex,sys\n"
        "args=shlex.split(sys.argv[-1])\n"
        "options=json.loads(args[-1])\n"
        f"options.update({overrides!r})\n"
        "os.execv(sys.executable,[sys.executable,*args[1:-1],json.dumps(options)])\n"
    )
    ssh.chmod(0o755)
    node_config = tmp_path / "node.yaml"
    node_config.write_text(json.dumps(asdict(config)))
    env = dict(os.environ, OPEN_DUCK_READ_ONLY="1", OPEN_DUCK_NODE_CONFIG=str(node_config),
               PATH=str(ssh.parent) + os.pathsep + os.environ["PATH"])
    process = subprocess.Popen(
        [str(dora), "run", "dataflow.yaml"], env=env,
        cwd=repo / "examples/03_workflows/real_basic_motion",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=20)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.communicate(timeout=5)
    assert process.returncode == 0, output
    assert "Read-only Forge chain verified" in output
    assert not trace.exists()
