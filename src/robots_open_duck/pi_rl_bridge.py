"""Run the Pi's installed RL walk script with a remote command source.

This module is sent over SSH by the host. It does not copy or alter the vendor
runtime. Stdout is reserved for one JSON response per request; runtime logs go
to stderr.
"""
from __future__ import annotations

import _thread
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import threading
import time


_RPC_OUTPUT = None
_REPLY_LOCK = threading.Lock()


def reply(message):
    with _REPLY_LOCK:
        print(json.dumps(message, allow_nan=False), file=_RPC_OUTPUT, flush=True)


def _check_port_free(port):
    real_port = os.path.realpath(port)
    for process_dir in Path("/proc").iterdir():
        if not process_dir.name.isdigit() or process_dir.name == str(os.getpid()):
            continue
        try:
            for fd in (process_dir / "fd").iterdir():
                try:
                    if os.path.realpath(fd) == real_port:
                        raise RuntimeError("serial port already open by PID " + process_dir.name)
                except (PermissionError, FileNotFoundError):
                    continue
        except (PermissionError, FileNotFoundError):
            continue


def _check_hash(path, expected):
    if not expected:
        return
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f"runtime file changed: {path} (sha256 {actual})")


def main():
    options = json.loads(sys.argv[1])
    runtime_dir = Path(options["runtime_dir"]).expanduser()
    script = runtime_dir / "scripts/v2_rl_walk_mujoco.py"
    model = Path(options["onnx_model_path"]).expanduser()
    config = Path(options["duck_config_path"]).expanduser()
    port = options["port"]
    _check_hash(script, options.get("script_sha256"))
    _check_hash(model, options.get("model_sha256"))
    if not config.is_file():
        raise FileNotFoundError(config)
    if not (runtime_dir / "scripts/polynomial_coefficients.pkl").is_file():
        raise FileNotFoundError("polynomial_coefficients.pkl is missing")
    lock_path = "/tmp/open_duck_forge_" + Path(os.path.realpath(port)).name + ".lock"
    with open(lock_path, "a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _check_port_free(port)
        sys.path.insert(0, str(runtime_dir / "mini_bdx_runtime"))
        from mini_bdx_runtime.buttons import Buttons

        class RemoteController:
            def __init__(self, command_freq, only_head_control=False):
                self.buttons = Buttons()
                self._lock = threading.Lock()
                self._command = [0.0] * 7
                self._updated = time.monotonic()
                self._last_rpc = self._updated

            def mark_alive(self):
                with self._lock:
                    self._last_rpc = time.monotonic()

            def set_velocity(self, vx, vy, wz):
                with self._lock:
                    self._command[:3] = [vx, vy, wz]
                    self._updated = time.monotonic()

            def get_last_command(self):
                with self._lock:
                    if time.monotonic() - self._last_rpc > 10.0:
                        raise KeyboardInterrupt("host RPC heartbeat was lost")
                    if time.monotonic() - self._updated > options["watchdog_seconds"]:
                        self._command[:3] = [0.0, 0.0, 0.0]
                    command = list(self._command)
                self.buttons.update(False, False, False, False, False, False, False, False)
                return command, self.buttons, 0.0, 0.0

        spec = importlib.util.spec_from_file_location("open_duck_vendor_rl", script)
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to load RL walk script")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.XBoxController = RemoteController
        state_lock = threading.Lock()
        state_ready = threading.Event()
        state = {}

        class BridgeWalk(module.RLWalk):
            def start(self):
                if not self.dry_run:
                    # Hold the measured pose before enabling torque. The native
                    # start() then moves each joint to HOME with low gains.
                    positions = self.hwi.get_present_positions()
                    joints = list(self.hwi.joints.items())
                    if positions is None or len(positions) != len(joints) or not all(
                        math.isfinite(float(value)) for value in positions
                    ):
                        raise RuntimeError("cannot read the initial joint pose")
                    self.hwi.set_kps([self.hwi.low_torque_kps[0]] * len(joints))
                    self.hwi.set_kds([0] * len(joints))
                    for (name, motor_id), position in zip(joints, positions):
                        self.hwi.io.write_goal_position(
                            [motor_id], [float(position) + self.hwi.joints_offsets[name]]
                        )
                    self.hwi.io.enable_torque([motor_id for _, motor_id in joints])
                super().start()

            def get_obs(self):
                obs = super().get_obs()
                if obs is not None:
                    # Vendor observation: gyro 3, accel 3, commands 7,
                    # joint offsets 14, scaled joint velocities 14, ...
                    with state_lock:
                        state["position"] = (obs[13:27] + self.init_pos).tolist()
                        state["velocity"] = (obs[27:41] / 0.05).tolist()
                        state["time"] = time.monotonic()
                    state_ready.set()
                return obs

        os.chdir(runtime_dir / "scripts")
        walk = BridgeWalk(
            str(model), duck_config_path=str(config), serial_port=port,
            commands=True, control_freq=options["control_freq"],
        )
        # Keep the native HOME targets until the first walking command arrives.
        walk.paused = True
        controller = walk.xbox_controller

        def serve_requests():
            for line in sys.stdin:
                request_id = None
                try:
                    request = json.loads(line)
                    controller.mark_alive()
                    request_id = request.get("id")
                    op = request.get("op")
                    if op == "set":
                        values = [request[k] for k in ("vx", "vy", "wz")]
                        limits = [options[k] for k in ("max_vx", "max_vy", "max_wz")]
                        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > m
                               for v, m in zip(values, limits)):
                            raise ValueError("locomotion command exceeds configured bounds")
                        controller.set_velocity(*values)
                        if any(values):
                            walk.paused = False
                        result = {"accepted": True}
                    elif op == "read":
                        if walk.paused:
                            # The policy does no serial I/O while paused. Read
                            # real feedback here so Forge can become ready.
                            position = walk.hwi.get_present_positions()
                            velocity = walk.hwi.get_present_velocities()
                            if (position is None or velocity is None or
                                    len(position) != walk.num_dofs or
                                    len(velocity) != walk.num_dofs):
                                raise TimeoutError("HOME joint feedback is unavailable")
                            result = {
                                "position": position.tolist(),
                                "velocity": velocity.tolist(),
                                "time": time.monotonic(),
                            }
                        else:
                            if not state_ready.wait(timeout=2.0):
                                raise TimeoutError("RL observation is unavailable")
                            with state_lock:
                                result = dict(state)
                        result["age_seconds"] = time.monotonic() - result.pop("time")
                        if result["age_seconds"] > 2.0:
                            raise TimeoutError("RL observation is stale")
                    elif op == "shutdown":
                        controller.set_velocity(0.0, 0.0, 0.0)
                        reply({"id": request_id, "ok": True, "result": {"stopping": True}})
                        time.sleep(0.6)
                        _thread.interrupt_main()
                        return
                    else:
                        raise ValueError("unknown operation")
                    reply({"id": request_id, "ok": True, "result": result})
                except Exception as error:
                    reply({"id": request_id, "ok": False, "error": str(error)})
            controller.set_velocity(0.0, 0.0, 0.0)
            time.sleep(0.6)
            _thread.interrupt_main()

        threading.Thread(target=serve_requests, daemon=True).start()
        reply({"ok": True, "result": {"ready": True}})
        try:
            walk.run()
        finally:
            controller.set_velocity(0.0, 0.0, 0.0)
            # Match the native RL script: preserve servo holding torque on exit.
            # Releasing torque here can make a grounded biped collapse.


if __name__ == "__main__":
    sys.stdout.flush()
    with os.fdopen(os.dup(sys.stdout.fileno()), "w", buffering=1, encoding="utf-8") as _RPC_OUTPUT:
        os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
        try:
            main()
        except (Exception, KeyboardInterrupt) as error:
            reply({"ok": False, "error": str(error) or "RL bridge interrupted"})
            raise SystemExit(1)
