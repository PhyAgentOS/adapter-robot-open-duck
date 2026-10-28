# 辅助脚本

| 脚本 | 用途 |
|---|---|
| `import_assets.py` | 从指定上游目录导入模型及被引用网格，生成固定基座 MJCF、整理 URDF 并记录哈希 |
| `generate_configs.py` | 根据唯一关节规格表生成 MuJoCo / task_robot 配置 |
| `validate_model.py` | 编译 MJCF，核对关节、执行器、限位与 HOME |
| `build_pyinstaller.sh` | 将正式 CLI 打包为单文件程序 |

从构型包根目录运行。日常启动仿真直接使用 workflow 的 `run_demo.sh`，无需手动生成配置。维护模型规格后可重新生成：

```bash
uv run python scripts/generate_configs.py --workflow-dir examples/03_workflows/simulation/mujoco_open_duck
uv run python scripts/generate_configs.py --workflow-dir examples/03_workflows/real_basic_motion --kind task
```

`--kind both` 为默认值，同时输出带相机转发的仿真和 task_robot 配置；`sim` 仅输出模拟器配置；`task` 仅输出不含相机转发的 task_robot 配置。

资产导入须提供含 `robot.xml`、`robot.urdf`、`scene.xml` 和网格的上游目录，以及 `--commit`。脚本保留模型引用的运行时网格，不复制 CAD `.part`、重复模型或配置文件，逐文件哈希输出到 `assets/asset_manifest.json`。来源与转换说明见 [资产说明](../assets/README.md)。

## 打包

```bash
./scripts/build_pyinstaller.sh
# 产物：dist/robots_open_duck
```

脚本通过 uv 安装 PyInstaller extra。SSH 后端不要求电脑安装硬件 extra；需要本机直连串口时先安装 `uv sync --extra pyinstaller --extra hardware`。spec 会携带 Pi 接收端源码，供冻结程序经 SSH 发送。

产物不包含仿真资产、examples 或 Pi 的 Runtime SDK。此前的 Linux x86_64 产物仅验证过 help/version；2026-10-13 更新 spec 后尚未重建，冻结程序的 SSH 连接仍待验收，不能据此声明支持 Pi aarch64 部署。
