# 四孔方块扰动自动化脚本说明

本目录包含四孔方块结构的 5 个扰动脚本：

1. 改单孔半径扰动：C4 -> C1
2. 对角成对变化扰动：C4 -> C2
3. 单孔偏移扰动：C4 -> C1
4. 四孔同步孔径扰动：保持 C4
5. 孔距同步扫描扰动：保持 C4

公共流程在 `four_hole_square_common.py`，每个扰动子文件夹中的脚本只保留用户主要修改区和扰动配置。

结果统一保存到：

`H:\FDTD outcome\struct\群论_struct\C4对称结构\四孔方块\results\扰动名\run_模式_时间戳\`

每个真实仿真点会保存：

- 修改后的 `.fsp`
- 透射谱 abs^2 图片 `.png`
- 透射谱原始数据 Excel `.xlsx`
- `manifest.csv`
- `scan_points.csv`
- `结构状态说明.md`

由于 Lumerical 对中文路径加载 `.fsp` 有时会失败，公共模块会自动在
`H:\FDTD_CodeX\fdtd_ascii_work\four_hole_square\` 下创建英文镜像工作副本用于仿真，最终结果仍保存回本结构的 `results` 目录。
