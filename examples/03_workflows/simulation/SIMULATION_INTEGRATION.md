# OpenDuck 仿真交付与 Forge 对接

## 运行环境

本示例按 framework 工作区布局使用并列的 `forge/`、`forge_runtime/`、`simulators/mujoco_sim/` 和 `tools/viewers/image_viewer/`。Python 依赖与锁文件位于 `mujoco_open_duck/`，启动脚本通过 uv 准备环境。

## 模型与配置

| 配置 | 作用 |
|------|------|
| `mujoco_open_duck/simulator.yaml` | 指向根目录 MJCF，定义初始位置、14 关节映射与相机输出 |
| `mujoco_open_duck/task_robot.yaml` | 与模型一致的 actuator_order、joint_to_actuator 和图像转发 |
| `mujoco_open_duck/dataflow.yaml` | 动作源、MuJoCo、TaskRobot、关节检查器与 image viewer 编排 |

唯一关节规格表位于 `src/robots_open_duck/config.py`。启动脚本自动生成上述两份节点配置，日常无需单独执行生成器。模型对齐记录见 [MODEL_ALIGNMENT_NOTES.md](MODEL_ALIGNMENT_NOTES.md)。

## 运行

从构型包根目录执行：

```bash
./examples/03_workflows/simulation/mujoco_open_duck/run_demo.sh
```

脚本同步依赖、生成配置、构建 standalone image viewer，然后构建并运行 Dora dataflow。动作源等待反馈后开始逐关节扫描，完成后保持 HOME；按 Ctrl+C 退出。

## Topic 对接

- 动作源 `action` → TaskRobot `action`。
- TaskRobot `action` → MuJoCo `action`。
- MuJoCo `proprio_state`、`image/front` → TaskRobot 同名输入。
- TaskRobot 聚合后的状态与图像 → 检查器和 image viewer。

仿真不经过真机 SDK / driver。物理模型是固定基座，适用于关节映射和状态 / 图像链路检查。真机动作使用并列的 `real_basic_motion/` workflow。

## 检查与输出

检查器统计状态与图像数量、逐关节反馈范围及最终 HOME 误差，退出时写入 `mujoco_open_duck/out/joint_sweep.json`。历史结果及其覆盖范围见 [JOINT_SWEEP_CHECKLIST.md](JOINT_SWEEP_CHECKLIST.md)。

本轮整理修正了目录深度、模型路径、Python 依赖路径和锁文件，尚未重新运行 Dora 或图形界面。
