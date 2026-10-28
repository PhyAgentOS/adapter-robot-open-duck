"""Rustypot-shaped RPC client; Forge stays on the PC, serial I/O stays on the Pi."""
from __future__ import annotations

from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import queue
import shlex
import subprocess
import threading

from .config import HOME, JOINT_ORDER, MOTOR_IDS, OPEN_DUCK_ACTUATOR_SPECS, OpenDuckNodeConfig


class SSHFeetechIO:
    def __init__(self, config: OpenDuckNodeConfig):
        self.timeout = config.rpc_timeout_seconds
        self._lock = threading.Lock()
        self._responses: queue.Queue = queue.Queue()
        self._sequence = 0
        self._closed = False
        options = {
            "runtime_dir": config.remote_runtime_dir,
            "duck_config_path": config.duck_config_path,
            "port": config.port,
            "enable_action": config.enable_action,
            "command_timeout_seconds": config.command_timeout_seconds,
            "specs": [asdict(spec) for spec in OPEN_DUCK_ACTUATOR_SPECS],
        }
        source = Path(__file__).with_name("pi_bridge.py").read_text(encoding="utf-8")
        command = " ".join(shlex.quote(arg) for arg in (
            config.remote_python, "-u", "-c", source, json.dumps(options),
        ))
        argv = ["ssh", "-T", "-o", "ConnectTimeout=5", "-o", "ServerAliveInterval=2",
                "-o", "ServerAliveCountMax=2"]
        control_path = os.getenv("OPEN_DUCK_SSH_CONTROL_PATH")
        if control_path:
            argv += ["-S", control_path, "-o", "BatchMode=yes"]
        argv += [config.ssh_target, command]
        self._process = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1,
        )
        threading.Thread(target=self._read_responses, daemon=True).start()
        try:
            ready = self._receive(timeout=60.0)
            if not ready.get("ok"):
                raise RuntimeError(ready.get("error", "Pi bridge failed to initialize"))
            metadata = ready["result"]
            if metadata["joint_order"] != list(JOINT_ORDER) or metadata["motor_ids"] != list(MOTOR_IDS):
                raise RuntimeError("Pi joint mapping does not match the Forge robot")
            if any(abs(float(a) - b) > 1e-6 for a, b in zip(metadata["home"], HOME, strict=True)):
                raise RuntimeError("Pi HOME does not match the Forge model")
            self.offsets = dict(metadata["offsets"])
            if set(self.offsets) != set(JOINT_ORDER) or not all(
                math.isfinite(float(value)) for value in self.offsets.values()
            ):
                raise RuntimeError("Pi calibration must contain all 14 finite offsets")
        except BaseException:
            self.close()
            raise

    def _read_responses(self):
        try:
            for line in self._process.stdout:
                self._responses.put(line)
        finally:
            self._responses.put(None)

    def _receive(self, timeout=None):
        try:
            line = self._responses.get(timeout=timeout or self.timeout)
        except queue.Empty as exc:
            raise TimeoutError("Pi bridge response timed out") from exc
        if line is None:
            raise ConnectionError("Pi bridge closed the SSH connection")
        try:
            result = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Pi bridge returned a non-JSON protocol response: {line[:200]!r}") from exc
        if not isinstance(result, dict):
            raise RuntimeError("invalid Pi bridge response")
        return result

    def _call(self, operation, **payload):
        with self._lock:
            if self._closed:
                raise ConnectionError("Pi bridge is closed")
            self._sequence += 1
            message = {"id": self._sequence, "op": operation, **payload}
            self._process.stdin.write(json.dumps(message, allow_nan=False) + "\n")
            self._process.stdin.flush()
            response = self._receive()
            if not response.get("ok"):
                raise RuntimeError(response.get("error", "Pi bridge rejected the request"))
            if response.get("id") != self._sequence:
                raise RuntimeError("Pi bridge response sequence mismatch")
            return response.get("result")

    def read_present_position(self, ids):
        return self._call("read", ids=ids)

    def write_goal_position(self, ids, values):
        self._call("write", ids=ids, values=values)

    def enable_torque(self, ids):
        self._call("enable", ids=ids)

    def disable_torque(self, ids):
        self._call("disable", ids=ids)

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._process.stdin:
            try:
                self._process.stdin.close()
            except (BrokenPipeError, OSError):
                pass
        try:
            self._process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        if self._process.stdout:
            self._process.stdout.close()
