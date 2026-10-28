# Forge 机器人节点源码（`src/`）

Open Duck Mini v2 真机 / Dora 节点源码位于：

`src/robots_open_duck/`

主要文件包括 `main.py`、`driver.py`、`config.py`、`sdk.py` 和 `device_tools.py`。电脑端 SSH 客户端为 `ssh_io.py`，Pi 接收端为 `pi_bridge.py`；有限 workflow 的退出适配位于 `node.py`。

真机 workflow 调用安装后的 `robots-open-duck` 入口。通信、消息转换、校准与停止逻辑均保存在正式包中，examples 只负责轨迹和节点编排；打包及资产工具位于根目录 `scripts/`。

配置、CLI、Python 接口与 topic 见 [OpenDuck 节点](robots_open_duck/README.md)。
