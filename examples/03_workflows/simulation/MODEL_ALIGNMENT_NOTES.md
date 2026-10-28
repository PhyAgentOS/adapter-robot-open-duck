# 模型对齐记录

## 结论

- 仿真入口：`assets/mjcf/open_duck_fixed.xml`。
- 执行器：14 个旋转关节、14 个 position actuator；规范顺序为左腿 5、颈部 / 头部 4、右腿 5。
- 前缀：空字符串；TaskRobot 的关节名与模型名称一致。
- HOME 与限位：统一来自 `src/robots_open_duck/config.py`。
- 相机：`front` 转发为 `image/front`，640×480 RGB、15 Hz。
- 基座：固定；模型包含地面，但不验证自由站立、平衡或行走。
- 资产来源与哈希：根目录 `assets/ASSET_SOURCES.md`、`assets/asset_manifest.json`。

## 模型转换

上游固定基座 MJCF 含两个天线关节及执行器。导入脚本移除这两项，保留其外观为固定部件，添加地面、光照与前方相机。源碰撞网格在 HOME 时存在躯干 / 颈部相邻重叠，转换仅排除 `trunk_assembly` 与 `neck_pitch_assembly` 的碰撞对，保持外观和运动学变换。

整理后的 URDF 保留上游关节定义，仅修改网格路径，不能将其执行器清单直接视为上述 14 执行器 MJCF。未修改的上游快照用于追溯，不作为本包仿真入口。

## 检查记录

此前模型编译结果为 nq=14、nv=14、nu=14，关节名称、执行器名称、工作限位与 HOME 已核对。仿真跟踪记录见 [JOINT_SWEEP_CHECKLIST.md](JOINT_SWEEP_CHECKLIST.md)。

2026-10-13 整理目录、模型文档及配置路径，未重新运行模型编译或动态仿真。真机方向、零位和完整安全工作范围仍待逐关节复核。
