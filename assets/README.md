# 模型资产

资产只保存在根目录这一份实体目录。模型来源为 `apirrone/Open_Duck_Mini`，固定提交 `b23317a485b3cec7d8417f352478778b3475173c`，附上游 Apache-2.0 许可。

| 路径 | 用途 |
|---|---|
| `mjcf/open_duck_fixed.xml` | 本包可运行的固定基座 14 关节 MuJoCo 入口 |
| `urdf/robot.urdf` | 整理了网格相对路径的 URDF |
| `meshes/open_duck_mini_v2/` | 上述模型引用的 45 个 STL 网格 |
| `mjcf/upstream_robot_fixed_16dof.xml`、`mjcf/upstream_scene.xml` | 未修改的上游 MJCF 快照，用于追溯 |
| `urdf/upstream_robot.urdf` | 未修改的上游 URDF 快照，用于追溯 |
| `UPSTREAM_APACHE-2.0.txt` | 上游许可证 |

`scripts/import_assets.py` 移除天线关节及执行器、保留其外观，添加地面、光照与前方相机，并排除一个导致 neck_pitch 在 HOME 卡住的相邻躯干/颈部碰撞对。模型保持固定基座，不用于演示自由站立或行走。

上游快照保留原始相对路径和 include，不能直接作为本包的仿真入口；启动时使用 `open_duck_fixed.xml`。2026-10-13 清理了 51 个未参与本包运行的 CAD、重复模型和配置文件，未修改网格几何。

来源与逐文件 SHA256 见 [资产来源](ASSET_SOURCES.md) 和 [asset_manifest.json](asset_manifest.json)，第三方许可说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。`robots_open_duck.asset_directory()` 在源码检出中解析根目录资产；Python wheel 仅包含驱动包，不包含模型文件。
