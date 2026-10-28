"""50 Hz sequential joint sweep around Home, with all other joints held."""
import time
from dora import Node
from forge_msgs import JointCommand, JointState
from robots_open_duck.config import HOME, JOINT_ORDER, OPEN_DUCK_ACTUATOR_SPECS

node=Node(); start=None; last_state=None; period=1.0; amplitude=.30
for event in node:
    if event.get("kind") not in (None,"dora"): continue
    if event.get("type")=="INPUT":
        key=event.get("id")
        if key=="proprio_state":
            last_state=JointState.from_arrow(event["value"])
        elif key=="tick" and last_state is not None:
            now=time.monotonic()
            if start is None: start=now
            t=now-start
            idx=min(int(t//(3*period)),13); phase=(t%(3*period))/period
            local=min(phase,1.0); blend=local*local*(3-2*local)
            targets=list(HOME)
            if phase<1:
                targets[idx]=HOME[idx]+amplitude*blend
            elif phase<2:
                targets[idx]=HOME[idx]+amplitude-2*amplitude*blend
            else:
                targets[idx]=HOME[idx]-amplitude+amplitude*blend
            spec=OPEN_DUCK_ACTUATOR_SPECS[idx]
            targets[idx]=min(spec.upper,max(spec.lower,targets[idx]))
            node.send_output("action",JointCommand(name=list(JOINT_ORDER),mode="position",position=targets).to_arrow())
            if t>=42.0:
                node.send_output("action",JointCommand(name=list(JOINT_ORDER),mode="position",position=list(HOME)).to_arrow())
