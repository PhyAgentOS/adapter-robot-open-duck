# open_duck 构型说明

## 构型概览

Open Duck Mini v2 双足构型，14 个单自由度旋转关节，通过树莓派上的 Runtime SDK 与电机串口通信。

- **构型类别**：双足机器人
- **执行器顺序**：左腿 5、颈部 / 头部 4、右腿 5
- **位置单位**：弧度
- **基础动作**：架空 HOME 归位与逐关节扫描；未接入行走策略

## 支持引擎

| 引擎 | 支持情况 | 依据 |
|---|---|---|
| 真机 | SSH 路径已有基础动作记录 | `src/robots_open_duck/`、`examples/03_workflows/real_basic_motion/` |
| MuJoCo | 支持固定基座关节仿真 | `assets/mjcf/open_duck_fixed.xml` |
| Isaac Sim / Isaac Lab | 未接入 | 暂无 USD 资产和 workflow |

本机直连串口适配代码已实现，但尚未独立验收。模型工作限位不代表实测机械极限；相机 / IMU、同构 / VR 尚未接入。

## 模型资产

- [`assets/mjcf/open_duck_fixed.xml`](assets/mjcf/open_duck_fixed.xml)
- [`assets/urdf/robot.urdf`](assets/urdf/robot.urdf)
- [`assets/meshes/open_duck_mini_v2/`](assets/meshes/open_duck_mini_v2/)

运行环境见 [README](README.md)；检查范围见 [仿真记录](examples/03_workflows/simulation/JOINT_SWEEP_CHECKLIST.md) 和 [真机记录](examples/03_workflows/real_basic_motion/JOINT_SWEEP_CHECKLIST.md)。
