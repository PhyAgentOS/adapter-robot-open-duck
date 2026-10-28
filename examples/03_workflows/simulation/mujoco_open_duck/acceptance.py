"""Check measured MuJoCo joint motion and rendered camera frames."""
import json, math
from pathlib import Path
from dora import Node
from forge_msgs import Image, JointState
from robots_open_duck.config import HOME, JOINT_ORDER
import numpy as np

node=Node(); low=[float("inf")]*14; high=[float("-inf")]*14; states=images=0; image_shape=None; image_std=None; final_position=None
for event in node:
    if event.get("kind") not in (None,"dora"): continue
    if event.get("type")=="INPUT":
        if event.get("id")=="proprio_state":
            state=JointState.from_arrow(event["value"])
            if state.name!=list(JOINT_ORDER) or not all(math.isfinite(v) for v in state.position): raise RuntimeError("invalid joint feedback")
            states+=1; final_position=state.position
            for i,v in enumerate(state.position):
                low[i]=min(low[i],v); high[i]=max(high[i],v)
        elif event.get("id")=="image/front":
            image=Image.from_arrow(event["value"]); images+=1; image_shape=[image.height,image.width,image.encoding]
            if image.height!=480 or image.width!=640 or not image.data: raise RuntimeError("invalid rendered image")
            if image_std is None:
                frame=np.frombuffer(image.data,dtype=np.uint8).reshape(image.height,image.width,3)
                image_std=float(frame.std())
    elif event.get("type")=="STOP":
        excursions=[high[i]-low[i] for i in range(14)]
        final_home_error=[abs(final_position[i]-HOME[i]) for i in range(14)] if final_position else []
        result={"backend":"mujoco","hardware_verified":False,"joint_order":list(JOINT_ORDER),"states":states,"images":images,"image_shape":image_shape,"image_std":image_std,"excursion_rad":excursions,"final_home_error_rad":final_home_error,"passed":states>0 and images>0 and image_std is not None and image_std>1.0 and all(x>.12 for x in excursions) and all(x<.05 for x in final_home_error)}
        out=Path("out"); out.mkdir(exist_ok=True); (out/"joint_sweep.json").write_text(json.dumps(result,indent=2)+"\n")
        print(result)
        if not result["passed"]: raise RuntimeError("workflow acceptance failed")
        break
