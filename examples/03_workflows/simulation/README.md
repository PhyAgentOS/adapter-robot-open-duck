# OpenDuck 仿真接入

| 内容 | 路径 |
|------|------|
| MuJoCo workflow | `mujoco_open_duck/` |
| 模型对齐记录 | [MODEL_ALIGNMENT_NOTES.md](MODEL_ALIGNMENT_NOTES.md) |
| 关节检查记录 | [JOINT_SWEEP_CHECKLIST.md](JOINT_SWEEP_CHECKLIST.md) |
| Forge 对接说明 | [SIMULATION_INTEGRATION.md](SIMULATION_INTEGRATION.md) |

仿真入口使用本仓 `assets/mjcf/open_duck_fixed.xml`，模型与网格只保存在根目录 `assets/`。从构型包根目录启动：

```bash
./examples/03_workflows/simulation/mujoco_open_duck/run_demo.sh
```
