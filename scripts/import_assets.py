#!/usr/bin/env python3
"""Import runtime meshes and pinned source models, then generate fixed MJCF."""
import argparse, hashlib, json, shutil, xml.etree.ElementTree as ET
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path, help="upstream open_duck_mini_v2 directory")
parser.add_argument("--commit", required=True)
args = parser.parse_args()
src = args.source.resolve(); dest = Path(__file__).resolve().parents[1] / "assets"
if not (src / "robot.urdf").is_file() or not (src / "robot.xml").is_file():
    raise SystemExit("source must include robot.urdf and robot.xml")
refs = set()
import re
for model in (src / "robot.xml", src / "robot.urdf"):
    text = model.read_text(encoding="utf-8")
    refs.update(re.findall(r'(?:file|filename)=["\']([^"\']+)["\']', text))
missing = [name for name in refs if not (src / name.rsplit("/",1)[-1]).exists()]
if missing: raise SystemExit("missing referenced assets: " + ", ".join(sorted(missing)))
(dest / "mjcf").mkdir(parents=True, exist_ok=True); (dest / "urdf").mkdir(parents=True, exist_ok=True)
mesh_root = dest / "meshes" / "open_duck_mini_v2"
mesh_root.mkdir(parents=True, exist_ok=True)
# CAD .part files and duplicate model/config files do not belong in meshes/.
mesh_names = {name.rsplit("/", 1)[-1] for name in refs
              if Path(name).suffix.lower() in {".stl", ".obj", ".ply"}}
for existing in mesh_root.iterdir():
    if existing.is_file() and existing.name not in mesh_names:
        existing.unlink()
for name in sorted(mesh_names):
    shutil.copy2(src / name, mesh_root / name)
shutil.copy2(src / "robot.xml", dest / "mjcf" / "upstream_robot_fixed_16dof.xml")
shutil.copy2(src / "robot.urdf", dest / "urdf" / "upstream_robot.urdf")
tree = ET.parse(src / "robot.xml")
root = tree.getroot()
compiler = root.find("compiler")
if compiler is not None:
    compiler.set("meshdir", "../meshes/open_duck_mini_v2")
for body in root.iter("body"):
    for joint in list(body.findall("joint")):
        if joint.get("name") in {"left_antenna", "right_antenna"}:
            body.remove(joint)  # Keep antenna visuals fixed to their parent body.
actuator = root.find("actuator")
if actuator is not None:
    for item in list(actuator):
        if item.get("joint") in {"left_antenna", "right_antenna"}:
            actuator.remove(item)
worldbody = root.find("worldbody")
if worldbody is not None:
    worldbody.insert(0, ET.Element("light", {"pos":"0 -1 2", "dir":"0 0 -1", "directional":"true"}))
    worldbody.insert(1, ET.Element("geom", {"name":"floor", "type":"plane", "pos":"0 0 0", "size":"2 2 0.1", "rgba":"0.32 0.34 0.37 1"}))
    worldbody.append(ET.Element("camera", {"name":"front", "mode":"targetbody", "target":"trunk", "pos":"1 -1 0.8", "fovy":"45"}))
# The source collision meshes overlap in the nominal Home pose and trap neck pitch.
# Exclude only this adjacent body pair; visible geoms and kinematic transforms stay intact.
contact=ET.Element("contact")
ET.SubElement(contact,"exclude",{"body1":"trunk_assembly","body2":"neck_pitch_assembly"})
actuator_index=list(root).index(actuator) if actuator is not None else len(root)
root.insert(actuator_index,contact)
tree.write(dest / "mjcf" / "open_duck_fixed.xml", encoding="utf-8", xml_declaration=True)
shutil.copy2(src / "scene.xml", dest / "mjcf" / "upstream_scene.xml")
license_path=src.parents[2]/"LICENSE"
if not license_path.is_file(): raise SystemExit("upstream repository LICENSE file is required")
shutil.copy2(license_path,dest/"UPSTREAM_APACHE-2.0.txt")
urdf = ET.parse(src / "robot.urdf")
for mesh in urdf.iter("mesh"):
    filename = mesh.get("filename")
    if filename:
        mesh.set("filename", "../meshes/open_duck_mini_v2/" + filename.rsplit("/",1)[-1])
urdf.write(dest / "urdf" / "robot.urdf", encoding="utf-8", xml_declaration=True)
items = [{"path": str(p.relative_to(dest)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(dest.rglob("*")) if p.is_file() and p.name != "asset_manifest.json"]
(dest / "asset_manifest.json").write_text(json.dumps({"commit":args.commit,"files":items},indent=2)+"\n",encoding="utf-8")
print(f"Imported {len(items)} files from {src}")
