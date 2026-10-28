# Open Duck Mini v2（Forge 机器人交付包）

[查看机器人构型说明](description.md)

## 交付内容

| 内容 | 路径 |
|------|------|
| **MJCF + meshes** | `assets/mjcf/open_duck_fixed.xml`、`assets/meshes/open_duck_mini_v2/` |
| **URDF** | `assets/urdf/robot.urdf` |
| **仿真配置示例** | `examples/03_workflows/simulation/mujoco_open_duck/` |
| **真机连接配置** | `config/config.yaml` |
| **真机节点源码** | `src/robots_open_duck/` |
| **真机动作示例** | `examples/03_workflows/real_basic_motion/` |
| **强化学习行走 Skill** | 外部可选集成，不随本公共仓库分发 |

本仓模型来源为 `apirrone/Open_Duck_Mini`，资产固定到提交 `b23317a485b3cec7d8417f352478778b3475173c`。真机通过树莓派已有的 Runtime SDK 控制电机，Forge / Dora 运行在电脑上。

## 关节单位与顺序

- Forge 层的 14 个关节均使用弧度，固定顺序为左腿 5、颈部 / 头部 4、右腿 5。
- 名称、motor ID、HOME 和工作限位统一定义在 `src/robots_open_duck/config.py`。
- SDK 原始角度与 Forge 逻辑角度之间按本机校准 offset 换算；SSH 后端读取 Pi 的校准文件。
- driver 接受按名称指定的稀疏位置命令，未指定关节保持目标。速度、力矩反馈暂留空，不支持非零速度、力矩或 kp/kd 命令。

## 真机生命周期

- 构造 driver 不访问硬件，`connect()` 建立连接并读取状态，不自动归位或使能。
- 动作须在现场配置中显式设置 `enable_action: true`。HOME 归位由设备工具或 workflow 发起。
- 基础动作 workflow 从实测姿态平滑回到 HOME，反馈确认后逐关节扫描。正常结束释放本次启用的扭矩，机器人不继续保持 HOME。
- `stop()` 锁存停止，断开并重新连接后才可恢复动作。

## 目录结构

| 路径 | 说明 |
|------|------|
| `assets/mjcf/` | MuJoCo 模型及上游快照 |
| `assets/meshes/` | 模型引用的网格 |
| `assets/urdf/` | URDF 及上游快照 |
| `examples/01_sdk_tests/` | 直接读取底层 SDK 状态，不启动 Dora |
| `examples/02_dora_tests/` | Dora 真机只读节点与仿真入口索引 |
| `examples/03_workflows/` | 包含 TaskRobot 的仿真与真机基础动作 |
| `src/` | Forge 规范机器人节点源码 |
| `scripts/` | 资产导入、配置生成、模型校验与打包 |
| `config/` | 默认连接配置 |
| `tests/` | 开发测试与测试替身，不作为运行后端 |

## 资产状态

后续仿真以本仓根目录 `assets/` 为准，无需从外部模型目录加载：

- `assets/mjcf/open_duck_fixed.xml`：固定基座 14 关节 MuJoCo 入口。
- `assets/meshes/open_duck_mini_v2/`：45 个被模型引用的 STL。
- `assets/urdf/robot.urdf`：整理网格路径的上游 URDF。
- 上游原始文件用于追溯，许可与哈希见 `assets/README.md` 和 `assets/asset_manifest.json`。

当前未交付 GLB / USD；固定基座仿真用于关节与数据流检查，不演示平衡或行走。

## 仿真接入流程

从本仓根目录运行：

```bash
./examples/03_workflows/simulation/mujoco_open_duck/run_demo.sh
```

脚本准备依赖与配置，启动 MuJoCo、TaskRobot 和 Forge image viewer。逐关节执行 HOME 附近 ±0.30 rad 扫描后保持 HOME；按 `Ctrl+C` 退出。日常运行无需手动执行配置生成命令。

## 真机接入流程

仓库随附 `config/config.yaml`。下载后按实际机器人修改其中的 SSH 目标、远程 Python、Runtime 目录和校准文件路径；现有值对应当前调试环境。SSH 认证使用系统 SSH 配置。

运行只读检查和基础动作：

```bash
./examples/03_workflows/real_basic_motion/run_demo.sh --check
./examples/03_workflows/real_basic_motion/run_demo.sh
```

动作运行需架稳机器人并在现场配置中允许动作。脚本自动启动 Pi 接收端，无需在 Pi 安装 Forge；可用 `--config PATH` 指定其他现场配置。详见 [真机基础动作](examples/03_workflows/real_basic_motion/README.md)。

## 强化学习行走 Skill

`move-open-duck` 使用树莓派已安装的 Runtime 脚本和 ONNX 模型，在本机通过 Forge `motion.walk_direction` 接收前进、后退、左右转向、左右横移六种定性动作指令。该 Skill 作为外部可选集成单独维护，不在本公共机器人仓库保存其开发源码；安装副本位于 `~/.PhyAgentOS/skills/move-open-duck/`。启动前按现场情况修改安装副本的 `profiles/open_duck_real/open_duck_rl.yaml` 和 `skill.yaml` 中的 `OPEN_DUCK_PROJECT_DIR`。本机机器人包需先创建 `.venv`，并配置到 Pi 的免交互 SSH 密钥认证；当前调试设备已配置。

本机在仓库根目录执行：

```bash
conda activate paos
paos skill start move-open-duck -p open_duck_real
```

Skill 启动时，树莓派脚本先从实测姿态使能舵机，再调用原生上电流程逐关节移动到 HOME；此后保持 HOME，收到第一条非零行走命令才启动步态策略。机器人应有支撑或位于空旷地面。之后可向 Agent 下达“前进”“后退”“向左转”“向右转”“向左横移”“向右横移”；每条命令持续 10 秒，结果仅报告方向、命令速度和时长，不表示实际位移或转角。即使指令包含距离、角度或其他时长，只要方向明确，Agent 也会直接执行对应的 10 秒动作，并在结果中说明并未按指定数值控制。取消动作会发零速度命令。结束时执行 `paos skill stop move-open-duck`；与基础关节动作 workflow 不得同时运行。

## `src/` 与 Forge 节点

正式实现位于 `src/robots_open_duck/`，使用与 Piper、Zerith 相同的 `BaseRobotDriver`、`JointCommand` / `JointState` 合同。Python 使用方直接构造 `OpenDuckDriver(config)`；接口、配置和 topic 说明见 [节点说明](src/robots_open_duck/README.md)。

```bash
uv sync
uv run robots-open-duck --help
uv run robots-open-duck watch-state --config config/config.yaml
```

`run` 或无子命令运行 Dora 节点；`move-home` / `move-joint` 提供平滑动作工具。
`rl` 子命令运行原生强化学习行走驱动，并分别读取受保护的运行参数和用户连接配置。
单文件打包使用 `./scripts/build_pyinstaller.sh`。

## 交付与验收

MuJoCo workflow 和 SSH 真机基础动作已有运行记录，真机完成 HOME 与 14 关节扫描，最终最大 HOME 误差为 0.007389 rad。本轮调整配置和构造接口后，尚未重新执行测试或真机回归。

仿真检查见 [仿真关节检查记录](examples/03_workflows/simulation/JOINT_SWEEP_CHECKLIST.md)，真机检查见 [真机关节检查记录](examples/03_workflows/real_basic_motion/JOINT_SWEEP_CHECKLIST.md)。强制断网、完整关节方向 / 工作范围、发布产物仍需验收；相机 / IMU、同构 / VR 与行走策略尚未接入。
