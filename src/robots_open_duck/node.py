"""Package-owned finite Dora lifecycle; trajectories belong to workflows."""
from __future__ import annotations

from dora import Node
from forge_msgs import JointCommand, JointState
from forge_robot import validate_robot_control_arrow

from .driver import OpenDuckDriver


def run_finite_node(driver: OpenDuckDriver) -> int:
    """Run an already connected driver until finish, STOP, or an input error.

    This adds a finish input to the normal action/state contract for finite
    demonstrations. The caller owns connection and final disconnection.
    """
    node = Node()
    for event in node:
        if event.get("kind") not in (None, "dora"):
            continue
        event_type = event.get("type")
        if event_type == "STOP":
            break
        if event_type == "ERROR":
            raise RuntimeError(str(event.get("error", "Dora error")))
        if event_type != "INPUT":
            continue
        input_id = event["id"]
        if input_id == "finish":
            print("Demo finished; closing the Pi session", flush=True)
            break
        if input_id == "tick":
            if driver.config.enable_action and not driver.sdk.actions_enabled:
                driver.prepare_actions()
            node.send_output("state", driver.get_state().to_arrow())
        elif input_id == "action" or input_id.startswith("action/"):
            validate_robot_control_arrow(event["value"], driver.joint_order)
            driver.set_command(JointCommand.from_arrow(event["value"]))
        elif input_id == "master_state":
            state = JointState.from_arrow(event["value"])
            driver.set_command(JointCommand(name=state.name, position=state.position))
    return 0
