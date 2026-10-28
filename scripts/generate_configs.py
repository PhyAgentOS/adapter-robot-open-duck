#!/usr/bin/env python3
"""Emit canonical joint metadata for downstream simulator/task_robot configs."""
import json
import argparse
from pathlib import Path
import os
from robots_open_duck.config import OPEN_DUCK_ACTUATOR_SPECS

parser=argparse.ArgumentParser()
parser.add_argument("--workflow-dir",type=Path)
parser.add_argument("--kind", choices=("both", "sim", "task"), default="both")
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
payload = {"actuator_order": [s.name for s in OPEN_DUCK_ACTUATOR_SPECS],
           "initial_positions": {s.name: s.home for s in OPEN_DUCK_ACTUATOR_SPECS},
           "joint_to_actuator": {s.name: s.name for s in OPEN_DUCK_ACTUATOR_SPECS},
           "limits": {s.name: [s.lower, s.upper] for s in OPEN_DUCK_ACTUATOR_SPECS}}
if args.workflow_dir:
    import yaml
    folder=args.workflow_dir.resolve(); folder.mkdir(parents=True,exist_ok=True)
    joint_rows=[{"name":s.name,"mode":"position","unit":"radians"} for s in OPEN_DUCK_ACTUATOR_SPECS]
    robot={"id":"robot_0","prefix":"","actuator_order":payload["actuator_order"],"joint_to_actuator":payload["joint_to_actuator"]}
    model_path=os.path.relpath(root/"assets"/"mjcf"/"open_duck_fixed.xml",folder)
    sim={"model_path":model_path,"control_hz":50,"image_format":"raw","initial_positions":payload["initial_positions"],"image_forward":{"front":{"output":"image/front","fps":15,"width":640,"height":480}},"joints":joint_rows,"robots":[robot]}
    task={"joints":joint_rows,"robots":[robot]}
    if args.kind == "both":
        task["image_forward"] = {"image/front":"image/front"}
    if args.kind in ("both", "sim"):
        (folder/"simulator.yaml").write_text(yaml.safe_dump(sim,sort_keys=False),encoding="utf-8")
    if args.kind in ("both", "task"):
        (folder/"task_robot.yaml").write_text(yaml.safe_dump(task,sort_keys=False),encoding="utf-8")
    print(folder)
else:
    out=root/"out"/"open_duck_joint_spec.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8"); print(out)
