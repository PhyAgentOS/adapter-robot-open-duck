"""Forge locomotion driver backed by the Pi's native ONNX walking loop."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import queue
import shlex
import subprocess
import threading

from forge_msgs import JointCommand, JointState, LocomotionCommand
from forge_robot import BaseRobotDriver
import yaml

from .config import JOINT_ORDER


@dataclass(frozen=True)
class RLWalkConfig:
    ssh_target: str
    remote_python: str
    remote_runtime_dir: str
    duck_config_path: str
    onnx_model_path: str
    port: str = "/dev/ttyACM0"
    control_freq: int = 50
    watchdog_seconds: float = 0.4
    max_vx: float = 0.15
    max_vy: float = 0.2
    max_wz: float = 1.0
    script_sha256: str = ""
    model_sha256: str = ""

    def __post_init__(self):
        for field in ("ssh_target", "remote_python", "remote_runtime_dir",
                      "duck_config_path", "onnx_model_path", "port"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value or "\n" in value or "\0" in value:
                raise ValueError(f"invalid {field}")
        if self.ssh_target.startswith("-"):
            raise ValueError("ssh_target must not begin with '-'")
        if isinstance(self.control_freq, bool) or not isinstance(self.control_freq, int) or self.control_freq <= 0:
            raise ValueError("control_freq must be a positive integer")
        for name, ceiling in (("watchdog_seconds", 2), ("max_vx", 0.15),
                              ("max_vy", 0.2), ("max_wz", 1.0)):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= ceiling:
                raise ValueError(f"invalid {name}")
        for name in ("script_sha256", "model_sha256"):
            value = getattr(self, name)
            if value and (len(value) != 64 or any(c not in "0123456789abcdef" for c in value)):
                raise ValueError(f"invalid {name}")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "RLWalkConfig":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("RL configuration must be a mapping")
        extra = set(data) - set(cls.__dataclass_fields__)
        if extra:
            raise ValueError(f"unknown RL configuration fields: {sorted(extra)}")
        return cls(**data)


class SSHRLWalkIO:
    def __init__(self, config: RLWalkConfig):
        source = Path(__file__).with_name("pi_rl_bridge.py").read_text(encoding="utf-8")
        options = {name: getattr(config, name) for name in (
            "remote_runtime_dir", "duck_config_path", "onnx_model_path", "port",
            "control_freq", "watchdog_seconds", "max_vx", "max_vy", "max_wz",
            "script_sha256", "model_sha256")}
        options["runtime_dir"] = options.pop("remote_runtime_dir")
        remote = " ".join(shlex.quote(arg) for arg in (
            config.remote_python, "-u", "-c", source, json.dumps(options)))
        self._process = subprocess.Popen(
            ["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
             "-o", "ServerAliveInterval=2", "-o", "ServerAliveCountMax=2",
             config.ssh_target, remote],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self._responses: queue.Queue[str | None] = queue.Queue()
        self._lock = threading.Lock()
        self._sequence = 0
        self._closed = False
        threading.Thread(target=self._read, daemon=True).start()
        try:
            ready = self._receive(timeout=90)
            if not ready.get("ok") or not ready.get("result", {}).get("ready"):
                raise RuntimeError(ready.get("error", "Pi RL bridge did not become ready"))
        except BaseException:
            self.close()
            raise

    def _read(self):
        try:
            for line in self._process.stdout:
                self._responses.put(line)
        finally:
            self._responses.put(None)

    def _receive(self, timeout=4):
        try:
            line = self._responses.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError("Pi RL bridge response timed out") from exc
        if line is None:
            raise ConnectionError("Pi RL bridge closed")
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Pi RL bridge returned non-JSON output: {line[:160]!r}") from exc
        if not isinstance(response, dict):
            raise RuntimeError("invalid Pi RL bridge response")
        return response

    def _call(self, op, **payload):
        with self._lock:
            if self._closed:
                raise ConnectionError("Pi RL bridge is closed")
            self._sequence += 1
            request = {"id": self._sequence, "op": op, **payload}
            self._process.stdin.write(json.dumps(request, allow_nan=False) + "\n")
            self._process.stdin.flush()
            response = self._receive()
            if response.get("id") != self._sequence or not response.get("ok"):
                raise RuntimeError(response.get("error", "Pi RL bridge protocol error"))
            return response.get("result")

    def set_velocity(self, vx, vy, wz):
        self._call("set", vx=vx, vy=vy, wz=wz)

    def read_state(self):
        return self._call("read")

    def close(self):
        if self._closed:
            return
        try:
            self.set_velocity(0.0, 0.0, 0.0)
            self._call("shutdown")
        except (OSError, RuntimeError, TimeoutError):
            pass
        self._closed = True
        if self._process.stdin:
            try:
                self._process.stdin.close()
            except OSError:
                pass
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        if self._process.stdout:
            self._process.stdout.close()


class OpenDuckRLDriver(BaseRobotDriver):
    """One serial owner for walking; joint position commands are unsupported in this mode."""

    def __init__(self, config: RLWalkConfig):
        self.config = config
        self.io: SSHRLWalkIO | None = None

    @property
    def joint_order(self):
        return list(JOINT_ORDER)

    def connect(self):
        self.io = SSHRLWalkIO(self.config)

    def get_state(self):
        if self.io is None:
            raise ConnectionError("RL driver is disconnected")
        data = self.io.read_state()
        positions = data["position"]
        velocities = data["velocity"]
        if len(positions) != len(JOINT_ORDER) or len(velocities) != len(JOINT_ORDER):
            raise RuntimeError("Pi RL joint state has an unexpected shape")
        return JointState(name=list(JOINT_ORDER), position=positions, velocity=velocities, effort=[])

    def set_command(self, command: JointCommand):
        raise ValueError("joint position control is unavailable while the RL policy owns the motors")

    def set_locomotion_command(self, command: LocomotionCommand):
        if self.io is None:
            raise ConnectionError("RL driver is disconnected")
        for value, limit in ((command.vx, self.config.max_vx),
                             (command.vy, self.config.max_vy),
                             (command.wz, self.config.max_wz)):
            if abs(value) > limit:
                raise ValueError("locomotion command exceeds RL walk limit")
        self.io.set_velocity(command.vx, command.vy, command.wz)

    def stop(self):
        if self.io is not None:
            self.io.set_velocity(0.0, 0.0, 0.0)

    def disconnect(self):
        if self.io is not None:
            self.io.close()
            self.io = None
