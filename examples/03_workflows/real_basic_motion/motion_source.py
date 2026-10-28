"""PC action source: sequential HOME transition and +/- 0.30 rad sweeps."""
import json
import os
from pathlib import Path
import time

from dora import Node
from forge_msgs import JointCommand, JointState
import pyarrow as pa
from robots_open_duck.config import HOME, JOINT_ORDER, load_config
from motion_plan import MotionPlan

HOME_TOLERANCE = 0.08
HOME_SETTLE_SECONDS = 0.5
HOME_TIMEOUT_SECONDS = 10.0


def main():
    config = load_config()
    feedback_timeout = config.command_timeout_seconds
    node = Node()
    state = None
    state_time = None
    plan = None
    elapsed = 0.0
    last_tick = None
    label = None
    started = time.monotonic()
    feedback_frames = 0
    home_ready = False
    home_wait_started = None
    home_stable_since = None
    feedback_pending = False
    read_only = os.getenv("OPEN_DUCK_READ_ONLY") == "1"
    for event in node:
        if event.get("kind") not in (None, "dora"):
            continue
        if event["type"] == "STOP":
            break
        if event["type"] == "ERROR":
            raise RuntimeError(str(event.get("error", "Dora error")))
        if event["type"] != "INPUT":
            continue
        now = time.monotonic()
        if event["id"] == "proprio_state":
            feedback = JointState.from_arrow(event["value"])
            state = list(feedback.to_np(list(JOINT_ORDER), "position"))
            state_time = now
            feedback_pending = True
            feedback_frames += 1
            if read_only and feedback_frames >= 20:
                print("Read-only Forge chain verified; 20 feedback frames: " +
                      json.dumps({name: float(value) for name, value in zip(JOINT_ORDER, state)}), flush=True)
                node.send_output("finish", pa.array([True]))
                break
        elif event["id"] == "tick" and state is not None:
            if now - state_time > feedback_timeout:
                raise TimeoutError("Pi feedback is stale")
            if read_only:
                continue
            # Advance only after fresh robot feedback. Serial RPC can be slower
            # than the PC timer; flooding action queues skips trajectory points.
            if not feedback_pending:
                continue
            feedback_pending = False
            if plan is None:
                plan = MotionPlan(state)
                print(f"HOME then 14 joint sweeps, +/-0.30 rad; trajectory time "
                      f"{plan.duration:.0f}s, actual duration follows Pi feedback", flush=True)
            if last_tick is not None:
                # Do not jump ahead after a delayed PC tick.
                elapsed += min(max(0.0, now - last_tick), 0.05)
            last_tick = now
            if not home_ready and elapsed >= plan.home_duration:
                elapsed = plan.home_duration
                if home_wait_started is None:
                    home_wait_started = now
                error = max(abs(actual - goal) for actual, goal in zip(state, HOME))
                if error <= HOME_TOLERANCE:
                    if home_stable_since is None:
                        home_stable_since = now
                    if now - home_stable_since >= HOME_SETTLE_SECONDS:
                        home_ready = True
                        print("HOME feedback confirmed; starting joint sweeps", flush=True)
                else:
                    home_stable_since = None
                if not home_ready and now - home_wait_started > HOME_TIMEOUT_SECONDS:
                    raise TimeoutError(f"HOME not reached; maximum joint error {error:.3f} rad")
            targets, next_label = plan.sample(elapsed)
            if not home_ready and home_wait_started is not None:
                next_label = "Holding HOME; waiting for feedback to settle"
            if next_label != label:
                print(next_label, flush=True)
                label = next_label
            node.send_output("action", JointCommand(
                name=list(JOINT_ORDER), mode="position", position=targets,
            ).to_arrow())
            if elapsed >= plan.duration:
                errors = {name: float(actual - goal) for name, actual, goal in zip(JOINT_ORDER, state, HOME)}
                result = {"completed": True, "command_amplitude_rad": 0.30,
                          "home_feedback_verified": home_ready,
                          "final_home_errors_rad": errors}
                out = Path(__file__).parent / "out"
                out.mkdir(exist_ok=True)
                (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
                print("Final HOME errors (rad): " + json.dumps(errors), flush=True)
                node.send_output("finish", pa.array([True]))
                break
        elif event["id"] == "tick" and now - started > 20.0:
            raise TimeoutError("no Pi feedback arrived within 20 seconds")


if __name__ == "__main__":
    main()
