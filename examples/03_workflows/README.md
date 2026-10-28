# 03 — Forge 端到端 workflow

## 本仓已落地

| Workflow | 路径 | 说明 |
|----------|------|------|
| MuJoCo 基础动作 | `simulation/mujoco_open_duck/` | 固定基座关节扫描、TaskRobot 状态聚合与相机画面 |
| 真机基础动作 | `real_basic_motion/` | SSH 连接 Pi，自动 HOME 与逐关节 ±0.30 rad 扫描 |

两个 workflow 均提供 `run_demo.sh`，启动时准备依赖并调用正式节点。真机使用 `robots-open-duck run --finite`，仿真使用独立 `mujoco_sim`。通信、校准、停止与消息适配位于 `src/robots_open_duck/`。

仿真交付与对接说明见 [SIMULATION_INTEGRATION.md](simulation/SIMULATION_INTEGRATION.md)，关节检查记录见 [仿真](simulation/JOINT_SWEEP_CHECKLIST.md) 和 [真机](real_basic_motion/JOINT_SWEEP_CHECKLIST.md)。运行日志与生成报告写入各 workflow 的 `out/`。
