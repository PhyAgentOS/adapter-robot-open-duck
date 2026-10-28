# 资产来源

模型与网格来自 `apirrone/Open_Duck_Mini`，提交 `b23317a485b3cec7d8417f352478778b3475173c`。上游 Apache-2.0 许可归档在 `assets/UPSTREAM_APACHE-2.0.txt`，逐文件 SHA256 记录于 `asset_manifest.json`。

## 落盘与转换

- 根目录 `assets/meshes/open_duck_mini_v2/` 保存模型引用的 45 个 STL。
- 原始 MJCF 快照保存在 `assets/mjcf/upstream_*.xml`，原始 URDF 为 `assets/urdf/upstream_robot.urdf`；快照用于追溯，不作为可运行入口。
- `assets/mjcf/open_duck_fixed.xml` 由导入脚本生成，固定基座，移除两个天线关节及执行器但保留外观，添加地面/光照/相机，排除相邻躯干与颈部的一个碰撞对。
- `assets/urdf/robot.urdf` 仅整理网格路径，保留上游模型关节定义；它与去除天线后的 14 执行器 MJCF 并非相同执行器清单。

2026-10-13 从 mesh 目录移除了 51 个 CAD 或重复模型/配置文件，更新导入脚本与 manifest，避免重新导入时恢复冗余文件。初始验收所记的 96 个上游文件是清理前数量。当前资产全部在根目录一份实体目录中，源码包内不再保存副本。
