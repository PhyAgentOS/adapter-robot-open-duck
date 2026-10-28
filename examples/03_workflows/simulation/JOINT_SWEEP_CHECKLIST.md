# 仿真关节 / 自由度检查记录

本文件记录 OpenDuck MuJoCo 模型的历史关节扫描和图像链路检查。检查范围为 HOME 附近动作，未覆盖所有关节的最小 / 最大机械位置。

## 检查前提

- 仿真入口为根目录 `assets/mjcf/open_duck_fixed.xml`，14 个固定基座位置执行器。
- MuJoCo 与 TaskRobot 使用相同的名称、顺序、弧度单位和 HOME。
- 相机 `front` 由 TaskRobot 转发为 `image/front`，640×480 RGB。

## 历史运行记录

| 项目 | 结果 |
|------|------|
| 直接 MuJoCo | 46 秒，2,245 帧状态、674 帧图像 |
| TaskRobot workflow | 46 秒，2,243 帧状态、673 帧图像 |
| 最终 HOME | 最大反馈误差不超过 0.019 rad |
| 图像 | 640×480 RGB，图像标准差约 40.0 |
| Viewer | 曾连续运行 59 秒；用户确认窗口保持响应 |

以下为当时 TaskRobot workflow 报告中的反馈最大值减最小值及最终 HOME 绝对误差，不是当前版本重新运行的结果：

| 关节 | 反馈范围跨度（rad） | 最终 HOME 误差（rad） |
|------|---------------------|----------------------|
| left_hip_yaw | 0.290132 | 0.000000 |
| left_hip_roll | 0.284999 | 0.018834 |
| left_hip_pitch | 0.283848 | 0.001989 |
| left_knee | 0.287444 | 0.007718 |
| left_ankle | 0.291020 | 0.000757 |
| neck_pitch | 0.306721 | 0.006094 |
| head_pitch | 0.296032 | 0.005878 |
| head_yaw | 0.290139 | 0.000001 |
| head_roll | 0.290881 | 0.000066 |
| right_hip_yaw | 0.290149 | 0.000000 |
| right_hip_roll | 0.284872 | 0.018537 |
| right_hip_pitch | 0.285369 | 0.002035 |
| right_knee | 0.287461 | 0.007743 |
| right_ankle | 0.291012 | 0.000811 |

## 本次目录整理

2026-10-13 将仿真统一至 `simulation/mujoco_open_duck/`，修正模型、启动脚本和依赖路径，移除 02 层重复的仿真配置。当前动作源的名义目标幅度为 ±0.30 rad，受模型限位约束；本轮未重跑动态仿真，不能用上表替代当前版本验收。

原始 JSON 和图像保留为仓外接入工作记录。后续运行生成 `mujoco_open_duck/out/joint_sweep.json`；新结果确认后更新本文件。

## 后续真机对照

逐关节复核方向、零位与安全工作范围，不能以固定基座仿真代替平衡或行走验收。真机基础扫描记录见 [真机关节检查记录](../real_basic_motion/JOINT_SWEEP_CHECKLIST.md)。
