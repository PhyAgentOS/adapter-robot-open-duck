"""Observe formal node output and validate canonical finite state frames."""
import math
from dora import Node
from forge_msgs import JointState
from robots_open_duck.config import JOINT_ORDER

node=Node(); frames=0
for event in node:
    if event.get("kind") not in (None,"dora"): continue
    if event.get("type")=="INPUT" and event.get("id")=="state":
        state=JointState.from_arrow(event["value"])
        if state.name != list(JOINT_ORDER) or len(state.position)!=14 or not all(math.isfinite(x) for x in state.position):
            raise RuntimeError(f"invalid formal node state: {state}")
        frames+=1
    elif event.get("type")=="STOP":
        print({"valid_state_frames":frames})
        break
