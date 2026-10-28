# 配置与标定

- **真机 / Dora 节点**：统一使用 `config.yaml`，使用前按实际环境修改 SSH 目标、远程 Python、Runtime 目录、校准文件和串口。
- **配置交付**：`config.yaml` 随仓库提交，现有连接值对应当前调试环境。可选的 `*.local.yaml` 与本地校准文件继续排除提交。
- **动作权限**：`config.yaml` 保留当前基础动作设置 `enable_action: true`。只读 CLI 和 workflow 的 `--check` 会禁用动作。

SSH 地址字段允许使用系统 `~/.ssh/config` 中的 Host 别名。认证由系统 SSH 负责，本包不保存密码或私钥。Pi 校准文件只在 Pi 端读取，SSH 配置不同时填写 offsets。

配置通过 `--config` 或 `OPEN_DUCK_NODE_CONFIG` 指定。Dora 内联配置 / 配置路径优先，显式文件其次，环境变量最后；不提供配置时报错。关节名称、顺序、HOME 和模型限位统一定义在 `src/robots_open_duck/config.py`。

超时单位为秒，默认配置使用 4 秒 RPC 超时、3 秒动作超时。持续读取状态不刷新动作 watchdog；启用动作后的退出会释放本会话扭矩。

源码还保留 `backend: real` 的本机串口适配，但未独立验收，不另交付配置模板。需要该路径时，应安装 hardware extra，并提供本台机器全部 14 个关节的实测 offsets。
