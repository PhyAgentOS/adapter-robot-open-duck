# 02 — Dora 节点测试

本目录记录 OpenDuck Dora 节点级验证入口。当前真机节点实现位于：

`robots/open_duck/src/robots_open_duck/`

| 验证项 | 入口 |
|--------|------|
| 真机只读节点 | `hardware_minimal/dataflow.yaml` |
| MuJoCo 节点 + TaskRobot + 动作源 | `../03_workflows/simulation/mujoco_open_duck/dataflow.yaml` |
| 真机基础动作 | `../03_workflows/real_basic_motion/dataflow.yaml` |
| OpenDuck 节点配置 | `config/config.yaml`，相对于构型包根目录 |

## 真机节点

从构型包根目录运行：

```bash
uv sync
export OPEN_DUCK_NODE_CONFIG="$PWD/config/config.yaml"
cd examples/02_dora_tests/hardware_minimal
../../../../../forge_runtime/.venv/bin/dora build dataflow.yaml
../../../../../forge_runtime/.venv/bin/dora run dataflow.yaml
```

该节点强制只读，不启用电机动作。配置与认证说明见 [hardware_minimal](hardware_minimal/README.md)。

## 仿真节点

从构型包根目录运行统一的仿真入口：

```bash
./examples/03_workflows/simulation/mujoco_open_duck/run_demo.sh
```

MuJoCo 配置、动作源和节点启动脚本统一维护在 03 层。模型对齐与关节检查记录见 [simulation](../03_workflows/simulation/README.md)。
