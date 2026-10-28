# OpenDuck 真机最小 Dora 示例

本示例验证正式 `robots-open-duck run` 节点的状态读取，输出规范顺序的 14 个关节位置。dataflow 强制关闭动作，不改变电机目标或扭矩。

## 配置

按实际环境修改根目录随附的 `config/config.yaml`，并在启动前通过 `OPEN_DUCK_NODE_CONFIG` 指定其绝对路径。SSH 使用公钥认证或已有的 `OPEN_DUCK_SSH_CONTROL_PATH` 会话。

## 运行

从构型包根目录执行：

```bash
uv sync
export OPEN_DUCK_NODE_CONFIG="$PWD/config/config.yaml"
cd examples/02_dora_tests/hardware_minimal
../../../../../forge_runtime/.venv/bin/dora build dataflow.yaml
../../../../../forge_runtime/.venv/bin/dora run dataflow.yaml
```

按 `Ctrl+C` 退出，检查器打印有效状态帧数。需要自动建立 SSH 会话并检查完整 TaskRobot 链路时，从构型包根目录运行：

```bash
./examples/03_workflows/real_basic_motion/run_demo.sh --check
```
