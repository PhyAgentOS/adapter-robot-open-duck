# 01 — SDK / 底层最小测试

本目录直接调用正式 `OpenDuckSDK`，读取真机状态，不启动 Dora。

先按实际环境修改根目录 `config/config.yaml`，然后从构型包根目录执行：

```bash
uv run python examples/01_sdk_tests/read_state.py --config config/config.yaml
```

脚本强制关闭动作，输出校准后的 14 关节弧度并断开。SSH 读取需要系统 SSH 认证；也可使用本机串口配置。未指定文件时读取 `OPEN_DUCK_NODE_CONFIG`。

单关节 / HOME 动作使用正式 CLI 的 `move-joint` / `move-home`，完整基础动作见 `../03_workflows/real_basic_motion/`。开发测试替身位于根目录 `tests/`，不提供离线假机器人运行后端。
