# OpenDuck MuJoCo 基础动作

本 workflow 将动作源、Forge TaskRobot 和独立 mujoco_sim 节点串联，并用 Forge standalone image viewer 显示相机图像。

## 运行

从构型包根目录启动：

```bash
./examples/03_workflows/simulation/mujoco_open_duck/run_demo.sh
```

脚本同步依赖、生成配置、构建 viewer 并运行 Dora dataflow。动作源以 50 Hz 定时上限逐关节执行 HOME 附近 ±0.30 rad 扫描，随后持续保持 HOME；按 Ctrl+C 退出。

## 模型与输出

模型入口为根目录 `assets/mjcf/open_duck_fixed.xml`，固定基座。相机 `image/front` 为 640×480 RGB、15 Hz。本示例检查关节映射及动作 / 状态 / 图像链路，不验证平衡或行走。

检查器退出时将报告写入 `out/joint_sweep.json`，运行日志与报告不作为源文件保留。

## 对接与检查记录

- [仿真交付与 Forge 对接](../SIMULATION_INTEGRATION.md)
- [模型对齐](../MODEL_ALIGNMENT_NOTES.md)
- [关节检查记录](../JOINT_SWEEP_CHECKLIST.md)
- [真机基础动作](../../real_basic_motion/README.md)
