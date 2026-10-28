# Open Duck Mini v2 节点

基于 dora-rs 的 OpenDuck 机器人节点：订阅 TaskRobot 下发的 `JointCommand`，通过 SSH 连接 Pi 上的 Runtime SDK，将读到的状态以 `JointState` 输出，供 TaskRobot 聚合为 `proprio_state`。

## 位置

`robots/open_duck/src/robots_open_duck/`

`driver.py` 实现 Forge `BaseRobotDriver`；`sdk.py` 处理设备位置、校准与停止；`ssh_io.py` / `pi_bridge.py` 分别处理电脑客户端和 Pi 接收端。

## 配置

仓库提供 `config/config.yaml`，使用前按实际环境修改连接地址和远程路径。配置来源优先级为：

1. `OPEN_DUCK_DATAFLOW_CONFIG` 内联 JSON 或 `OPEN_DUCK_DATAFLOW_CONFIG_PATH` 文件。
2. `--config` 显式文件。
3. 环境变量 `OPEN_DUCK_NODE_CONFIG`。

每次选择一个完整来源，不合并字段；未提供配置时报错。随仓库提供的连接值对应当前调试环境，SSH 后端使用 Pi 的校准文件。本机串口适配尚未独立验收，需要该路径时须提供全部 14 个实测 offset。

## Dataflow 使用

```yaml
path: ../../../.venv/bin/robots-open-duck
args: run
```

配置可由节点参数 `--config` 或环境变量提供。典型连接关系：

- TaskRobot 的 `robot_0/action` → OpenDuck 输入 `action`。
- OpenDuck 输出 `state` → TaskRobot 输入 `robot_0/state`。
- 输入 `tick` 触发反馈；也接受 `action/<source>` 和位置镜像输入 `master_state`。
- 有限 workflow 使用 `run --finite`，增加 `finish` 输入，处理完成后断开连接。

普通节点复用 Forge 标准 runner。没有独立 `stop` topic；Dora STOP 触发退出清理，Python 使用方可调用 `driver.stop()`。基础关节模式不提供 locomotion 接口。

## RL 行走模式

`rl_driver.py` 提供独立的 `OpenDuckRLDriver`，实现 Forge `LocomotionRobotDriver.set_locomotion_command(LocomotionCommand)`。`vx` 为向前、`vy` 为向左，单位 m/s；`wz` 为逆时针，单位 rad/s。范围由 `open_duck_rl.yaml` 限制。`get_state()` 返回 Pi 上 RL 观测缓存中的 14 关节角度和速度；`set_command(JointCommand)` 在该模式中拒绝执行，防止两种控制器同时写舵机。

`rl_main.py` 是独立的 Dora 节点入口；`pi_rl_bridge.py` 经 SSH 在 Pi 上加载已安装的原生步态脚本，将原脚本的手柄命令源替换为带超时归零的远程命令源。它保留原脚本的传感器、ONNX 推理和电机控制循环。技能包 `move-open-duck` 提供 `motion.walk_direction` 动作入口，将六个方向映射为固定 10 秒的速度命令；结果不报告位移或转角。启动该模式会从实测姿态使能舵机并按原生流程归位 HOME，在第一条行走命令前保持 HOME；退出时沿用原脚本的舵机保持行为。

## CLI 子命令

| 子命令 | 说明 |
|--------|------|
| `run --config ...` 或无子命令 | 运行 Dora 节点 |
| `run --finite` | 运行带 finish 输入的有限节点 |
| `watch-state --config ...` | 强制只读，读取一帧后断开 |
| `move-home --config ...` | 从实测姿态平滑归位 HOME |
| `move-joint NAME POSITION --config ...` | 平滑移动单关节到绝对目标弧度 |

动作工具须在配置中允许动作，退出时释放本次启用的扭矩。帮助 / 版本查询不连接设备。

## Python 接口

直接构造 driver，显式管理连接：

```python
from robots_open_duck.config import load_config
from robots_open_duck.driver import OpenDuckDriver

driver = OpenDuckDriver(load_config("config/config.yaml"))
try:
    driver.connect()
    state = driver.get_state()
finally:
    driver.disconnect()
```

| 接口 | 说明 |
|------|------|
| `connect()` / `disconnect()` | 连接 / 释放本会话资源 |
| `get_state() -> JointState` | 读取 14 关节逻辑角度 |
| `set_command(JointCommand)` | 按名称更新稀疏位置目标，其他关节保持目标 |
| `joint_order` | 固定关节名称顺序 |
| `stop()` | 停止并锁存；断开重连后恢复动作权限 |

连接不会自动 HOME 或使能。包内 `device_tools.move_home(driver)` / `move_joint(driver, name, position)` 使用已连接且允许动作的 driver，平滑下发并等待反馈，成功后由调用方管理连接。

## 关节顺序与单位

固定顺序为左腿 5、颈部 / 头部 4、右腿 5。元数据定义在 `config.py`：`JOINT_ORDER`、`MOTOR_IDS`、`HOME` 和 `OPEN_DUCK_ACTUATOR_SPECS`。规格字段为 `name/motor_id/lower/upper/home`。

位置使用逻辑弧度，原始电机角度 = 逻辑角度 + 校准 offset。速度 / 力矩反馈留空；position 命令中未使用的 velocity、effort、kp、kd 可为空或全零，非零值不支持。

普通越界目标告警并裁剪。SSH 启动恢复允许保持范围外目标或逐步向范围内移动；接收端限制每条目标变化不超过 0.08 rad。工具默认峰值目标速度 0.30 rad/s，到位容差 0.08 rad、稳定时间 0.5 秒。

## 打包

```bash
./scripts/build_pyinstaller.sh
```

产物为 `dist/robots_open_duck`。冻结程序携带经 SSH 发送的 Pi 接收端源码，连接配置通过外部 YAML 读取，仓库提供 `config/config.yaml`。Pi 的 Runtime SDK 需在 Pi 上预先安装。
