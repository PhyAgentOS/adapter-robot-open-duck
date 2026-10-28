"""Forge BaseRobotDriver implementation for Open Duck Mini v2."""
from __future__ import annotations
import math
import logging
from forge_msgs import JointCommand, JointState
from forge_robot import BaseRobotDriver
from .config import JOINT_ORDER, OPEN_DUCK_ACTUATOR_SPECS, OpenDuckNodeConfig
from .sdk import OpenDuckSDK

logger=logging.getLogger(__name__)


class OpenDuckDriver(BaseRobotDriver):
    def __init__(self, config: OpenDuckNodeConfig, *, sdk: OpenDuckSDK | None = None):
        """Construct an unconnected driver; native I/O starts in connect()."""
        self.config = config
        self.sdk = sdk if sdk is not None else OpenDuckSDK(config)
        self._targets: list[float] | None = None
        self._faulted = False
    @property
    def joint_order(self) -> list[str]: return list(JOINT_ORDER)
    def _disconnect_after_fault(self) -> None:
        self._faulted = True
        # Keep the triggering error visible even if the remote receiver has
        # already disabled torque and closed its connection.
        for cleanup in (self.sdk.stop, self.sdk.disconnect):
            try:
                cleanup()
            except Exception:
                logger.exception("cleanup after driver fault failed")
    def connect(self) -> None:
        self.sdk.connect()
        try: self._targets = self.sdk.read_positions()
        except BaseException:
            self._faulted = True
            self.disconnect()
            raise
        self._faulted = False
    def prepare_actions(self) -> None:
        """Stage and enable motors before publishing the initial action pose."""
        if not self.sdk.connected or self._faulted:
            raise RuntimeError("driver is disconnected or faulted")
        if self.sdk.actions_enabled:
            return
        try:
            self.sdk.enable_actions()
            self._targets = self.sdk.read_positions()
        except BaseException:
            self._disconnect_after_fault()
            raise
    def get_state(self) -> JointState:
        if not self.sdk.connected or self._faulted: raise RuntimeError("driver is disconnected or faulted")
        try: positions = self.sdk.read_positions()
        except BaseException:
            self._disconnect_after_fault()
            raise
        return JointState(name=list(JOINT_ORDER),position=positions,velocity=[],effort=[])
    def set_command(self, command: JointCommand) -> None:
        if not self.sdk.connected or self._faulted: raise RuntimeError("driver is disconnected or faulted")
        if self.sdk.stopped: raise RuntimeError("stop is latched")
        if command.mode != "position": raise ValueError("only position commands are supported")
        n = len(command.name)
        if not n or len(command.position) != n: raise ValueError("position command must contain named values")
        # task_robot fills unused fields with zero arrays. They are placeholders
        # in this position-only adapter; nonzero feedforward/gains are unsupported.
        if any(any(float(value) != 0.0 for value in getattr(command, field))
               for field in ("velocity", "effort", "kp", "kd")):
            raise ValueError("nonzero velocity, effort, kp, and kd payloads are unsupported")
        if len(set(command.name)) != n or set(command.name)-set(JOINT_ORDER): raise ValueError("unknown or duplicate joint name")
        vals = [float(v) for v in command.position]
        if not all(math.isfinite(v) for v in vals): raise ValueError("positions must be finite")
        if not self.config.enable_action: raise PermissionError("actions are disabled by configuration")
        if self._targets is None: raise RuntimeError("no feedback target cache")
        proposed = list(self._targets)
        for name,value in zip(command.name,vals):
            spec = next(s for s in OPEN_DUCK_ACTUATOR_SPECS if s.name == name)
            index = JOINT_ORDER.index(name)
            lower, upper = spec.lower, spec.upper
            if self.config.backend == "ssh":
                # Allow holding an out-of-range startup pose or moving inward.
                # Once inside, the normal operating limits apply permanently.
                lower = min(lower, self._targets[index])
                upper = max(upper, self._targets[index])
            clipped=min(upper,max(lower,value))
            if clipped != value: logger.warning("clipped %s target %.6f rad to %.6f rad",name,value,clipped)
            proposed[index] = clipped
        try:
            self.sdk.write_positions(proposed)
        except BaseException:
            self._disconnect_after_fault()
            raise
        self._targets = proposed
    def stop(self) -> None:
        self.sdk.stop()
        self._targets = None
    def disconnect(self) -> None:
        self.sdk.disconnect()
        self._targets = None
