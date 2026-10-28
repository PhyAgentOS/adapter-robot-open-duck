"""Reusable device operations shared by the CLI and external callers."""
from __future__ import annotations
import logging
import math
import time
from collections.abc import Mapping

from forge_msgs import JointCommand
from forge_msgs import JointState
from .config import HOME, JOINT_ORDER, OPEN_DUCK_ACTUATOR_SPECS
from .driver import OpenDuckDriver

logger = logging.getLogger(__name__)


def read_state(driver: OpenDuckDriver) -> JointState:
    """Connect, read one calibrated frame, and disconnect without enabling torque."""
    driver.connect()
    try: return driver.get_state()
    finally: driver.disconnect()


def move_to_positions(
    driver: OpenDuckDriver,
    positions: Mapping[str, float],
    *,
    max_velocity: float = 0.30,
    tolerance: float = 0.08,
    settle_timeout: float = 10.0,
) -> JointState:
    """Smoothly move selected joints, sequentially, on an already connected driver.

    Every step waits for fresh hardware feedback. No individual step advances
    more than 0.05 seconds of trajectory time. Other joints keep their targets.
    The caller retains ownership of the connection and torque on success.
    """
    for label, value in (("max_velocity", max_velocity), ("tolerance", tolerance),
                         ("settle_timeout", settle_timeout)):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{label} must be positive and finite")
    if max_velocity > 0.30:
        raise ValueError("device tools support at most 0.30 rad/s")
    specs = {spec.name: spec for spec in OPEN_DUCK_ACTUATOR_SPECS}
    if not positions or set(positions) - set(specs):
        raise ValueError("expected named Open Duck target positions")
    targets = {name: float(value) for name, value in positions.items()}
    for name, value in targets.items():
        spec = specs[name]
        if not math.isfinite(value) or not spec.lower <= value <= spec.upper:
            raise ValueError(f"target outside model limits: {name}")
    try:
        driver.prepare_actions()
        state = driver.get_state()
        measured = dict(zip(state.name, state.position, strict=True))
        order = sorted(targets, key=lambda name: (
            specs[name].lower <= measured[name] <= specs[name].upper
        ))
        for name in order:
            initial = measured[name]
            goal = targets[name]
            duration = max(1.0, 1.5 * abs(goal - initial) / max_velocity)
            elapsed = 0.0
            last_step = time.monotonic()
            while elapsed < duration:
                now = time.monotonic()
                elapsed = min(duration, elapsed + min(now - last_step, 0.05))
                last_step = now
                fraction = elapsed / duration
                blend = fraction * fraction * (3.0 - 2.0 * fraction)
                value = initial + (goal - initial) * blend
                driver.set_command(JointCommand(name=[name], position=[value]))
                state = driver.get_state()
                measured = dict(zip(state.name, state.position, strict=True))
                time.sleep(0.02)
        deadline = time.monotonic() + settle_timeout
        stable_since = None
        while True:
            driver.set_command(JointCommand(name=list(targets), position=list(targets.values())))
            state = driver.get_state()
            measured = dict(zip(state.name, state.position, strict=True))
            now = time.monotonic()
            if all(abs(measured[name] - goal) <= tolerance for name, goal in targets.items()):
                stable_since = now if stable_since is None else stable_since
                if now - stable_since >= 0.5:
                    return state
            else:
                stable_since = None
            if now >= deadline:
                raise TimeoutError("target positions did not settle within the configured timeout")
            time.sleep(0.02)
    except BaseException:
        try:
            driver.stop()
        except Exception:
            logger.exception("could not stop after device-tool failure")
        raise


def move_home(driver: OpenDuckDriver) -> JointState:
    """Recover from measured startup positions to HOME with feedback confirmation."""
    return move_to_positions(driver, dict(zip(JOINT_ORDER, HOME)))


def move_joint(driver: OpenDuckDriver, name: str, position: float) -> JointState:
    """Move one joint to an absolute logical-radian target without a target jump."""
    return move_to_positions(driver, {name: position})

def safety_stop(driver: OpenDuckDriver) -> None:
    driver.stop()
