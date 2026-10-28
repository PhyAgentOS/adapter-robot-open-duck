# OpenDuck 真机基础动作

电脑运行 Forge / Dora、TaskRobot 和 OpenDuck driver，通过 SSH 启动 Pi 接收端；接收端调用 Pi 已安装的 Runtime HWI / Rustypot 访问电机串口。

## 配置

仓库随附根目录 `config/config.yaml`，使用前按实际环境修改 SSH 目标、远程 Python、Runtime 目录、校准文件和串口。现有连接值对应当前调试环境。

`config.yaml` 保留当前基础动作设置 `enable_action: true`。SSH 后端读取 Pi 校准文件，并验证 14 个关节、motor ID 与 HOME。认证使用系统 SSH，脚本可在当前终端交互认证。

## 运行

从构型包根目录执行：

```bash
./examples/03_workflows/real_basic_motion/run_demo.sh --check
./examples/03_workflows/real_basic_motion/run_demo.sh
```

第一条只读检查接收 20 帧经 TaskRobot 返回的反馈后退出；第二条运行完整动作。脚本同步电脑依赖，建立 SSH 会话，构建并运行 dataflow。Pi 无需安装 Forge 或手动启动接收端。

使用其他现场配置时：

```bash
./examples/03_workflows/real_basic_motion/run_demo.sh --config /path/to/config.yaml
```

也可设置 `OPEN_DUCK_NODE_CONFIG`。不指定时脚本读取根目录 `config/config.yaml`。

## 动作顺序

机器人需架稳，双脚和各关节有活动空间。动作源读取当前姿态，优先恢复模型工作范围外的关节，逐关节平滑回到 HOME，峰值目标速度不超过 0.30 rad/s。无需手动摆准初始姿态。

全部 HOME 反馈误差连续 0.5 秒不超过 0.08 rad 后，依次执行每个关节的 `HOME - 0.30 rad → HOME + 0.30 rad → HOME`。左右膝正向幅度受限位约束，分别约 +0.203、+0.192 rad。最后保持 HOME 2 秒，记录反馈误差并退出。

只有收到新反馈才推进轨迹，每次最多推进 0.05 秒。实际时长随通信速度变化；轨迹结束后最多等待 HOME 到位 10 秒，失败停止。报告写入 `out/result.json`。

## 节点与停止

dataflow 调用正式入口 `robots-open-duck run --finite`，接收 `action`、输出 `state`，通过 `finish` 正常结束。节点实现位于包内 `node.py`，本目录只保存轨迹与编排。

Pi 接收端将 SDK 日志与 JSON RPC 分开。动作增益为腿部 Kp 30、颈部 / 头部 Kp 8，Kd 0；目标单步变化限于 0.08 rad。结束、Ctrl+C、SSH 关闭或动作 watchdog 超时会尝试关闭本次启用的扭矩，正常结束不继续保持 HOME。

默认配置的动作超时为 3 秒、RPC 超时为 4 秒；状态读取不刷新动作 watchdog。强制断网、原生串口阻塞时的失能延迟尚待硬件验收。

## 验收记录

此前完整真机流程运行 232 秒并正常退出，最终最大 HOME 反馈误差为 0.007389 rad。当前目录和配置调整后尚未回归，详见 [关节检查记录](JOINT_SWEEP_CHECKLIST.md)。

本 workflow 不运行 ONNX 步态。仿真入口为 `../simulation/mujoco_open_duck/run_demo.sh`。
