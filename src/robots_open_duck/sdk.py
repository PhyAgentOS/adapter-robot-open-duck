"""Device-level SDK adapter. Rustypot is imported only on real connect."""
from __future__ import annotations
import importlib.metadata
import math
from typing import Any, Sequence

from .config import JOINT_ORDER, MOTOR_IDS, OpenDuckNodeConfig


class OpenDuckSDK:
    def __init__(self, config: OpenDuckNodeConfig, io: Any | None = None):
        self.config, self.io = config, io
        self._injected_io = io is not None
        self.connected = False
        self.actions_enabled = False
        self.stopped = False
        self._offsets = dict(config.offsets or {})

    def connect(self) -> None:
        if self.connected: return
        # A new connection is the documented recovery boundary for a latched stop.
        self.stopped = False
        if self.io is None and self.config.backend == "ssh":
            from .ssh_io import SSHFeetechIO
            self.io = SSHFeetechIO(self.config)
            self._offsets = self.io.offsets
        if self.io is None:
            try:
                version = importlib.metadata.version("rustypot")
                if version != "0.1.0": raise RuntimeError(f"rustypot 0.1.0 required, found {version}")
                import rustypot
            except importlib.metadata.PackageNotFoundError as e:
                raise RuntimeError("real backend requires hardware extra rustypot==0.1.0") from e
            self.io = rustypot.feetech(self.config.port, self.config.baudrate)
        self.connected = True
        try: self.read_positions()
        except BaseException:
            self.disconnect()
            raise

    def _require(self) -> None:
        if not self.connected or self.io is None: raise RuntimeError("SDK is not connected")

    def read_positions(self) -> list[float]:
        self._require()
        raw = self.io.read_present_position(list(MOTOR_IDS))
        if raw is None or len(raw) != len(JOINT_ORDER): raise RuntimeError("invalid position feedback length")
        offsets = self._offsets
        result = [float(v) - float(offsets.get(n,0.0)) for n,v in zip(JOINT_ORDER,raw)]
        if not all(math.isfinite(v) for v in result): raise RuntimeError("non-finite position feedback")
        return result

    def write_positions(self, values: Sequence[float]) -> None:
        self._require()
        if self.stopped: raise RuntimeError("stop is latched; disconnect and reconnect to resume")
        if not self.config.enable_action: raise PermissionError("actions are disabled by configuration")
        if len(values) != 14 or not all(math.isfinite(float(v)) for v in values):
            raise ValueError("expected 14 finite joint positions")
        if not self.actions_enabled: self.enable_actions()
        offsets = self._offsets
        raw = [float(v)+float(offsets.get(n,0.0)) for n,v in zip(JOINT_ORDER,values)]
        self.io.write_goal_position(list(MOTOR_IDS),raw)
        self.actions_enabled = True

    def enable_actions(self) -> None:
        self._require()
        if not self.config.enable_action: raise PermissionError("actions are disabled by configuration")
        if self.stopped: raise RuntimeError("stop is latched; disconnect and reconnect to resume")
        if hasattr(self.io,"enable_torque"):
            self.io.enable_torque(list(MOTOR_IDS))
        self.actions_enabled = True
        self.stopped = False

    def stop(self) -> None:
        if self.stopped: return
        self.stopped = True
        should_disable=self.connected and self.actions_enabled
        self.actions_enabled = False
        if should_disable and hasattr(self.io,"disable_torque"):
            self.io.disable_torque(list(MOTOR_IDS))

    def disconnect(self) -> None:
        try:
            if self.connected and self.actions_enabled: self.stop()
        finally:
            try:
                if self.io is not None:
                    release = getattr(self.io,"close",None)
                    if callable(release): release()
            finally:
                if not self._injected_io:
                    self.io = None
                self.connected = False
                self.actions_enabled = False
