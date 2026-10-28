#!/usr/bin/env python3
"""Compile a local MJCF and check the expected fixed-base actuator contract."""
import argparse
from pathlib import Path
from robots_open_duck.config import JOINT_ORDER, OPEN_DUCK_ACTUATOR_SPECS

parser = argparse.ArgumentParser()
parser.add_argument("model", nargs="?", default="assets/mjcf/open_duck_fixed.xml")
args = parser.parse_args()
try:
    import mujoco
except ImportError as exc:
    raise SystemExit("Install the sim extra to validate MJCF") from exc
path = Path(args.model).resolve()
model = mujoco.MjModel.from_xml_path(str(path))
joint_names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(model.njnt)]
actuator_names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) for i in range(model.nu)]
if model.nq != 14 or model.nv != 14 or model.nu != 14:
    raise SystemExit(f"expected nq=nv=nu=14, got {model.nq}/{model.nv}/{model.nu}")
if set(joint_names) != set(JOINT_ORDER) or set(actuator_names) != set(JOINT_ORDER):
    raise SystemExit(f"joint/actuator names do not match canonical order: {joint_names}, {actuator_names}")
data=mujoco.MjData(model)
checks={}
for spec in OPEN_DUCK_ACTUATOR_SPECS:
    jid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,spec.name)
    aid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_ACTUATOR,spec.name)
    lo,hi=map(float,model.jnt_range[jid])
    if abs(lo-spec.lower)>2e-5 or abs(hi-spec.upper)>2e-5:
        raise SystemExit(f"{spec.name} joint range mismatch: {(lo,hi)} vs {(spec.lower,spec.upper)}")
    if model.actuator_ctrllimited[aid] and (abs(model.actuator_ctrlrange[aid,0]-lo)>2e-5 or abs(model.actuator_ctrlrange[aid,1]-hi)>2e-5):
        raise SystemExit(f"{spec.name} actuator range does not match joint range")
    addr=int(model.jnt_qposadr[jid])
    for label,value in (("lower",lo),("upper",hi),("zero",0.0),("home",spec.home)):
        if not lo<=value<=hi: raise SystemExit(f"{spec.name} {label} outside model range")
        data.qpos[addr]=value; data.ctrl[aid]=value; mujoco.mj_forward(model,data)
        if not all(map(__import__('math').isfinite,data.qpos)) or not all(map(__import__('math').isfinite,data.ctrl)):
            raise SystemExit(f"non-finite state at {spec.name} {label}")
    checks[spec.name]={"range":[lo,hi],"home":spec.home}
print({"path": str(path), "nq": model.nq, "nv": model.nv, "nu": model.nu, "joints": joint_names,"checks":checks})
