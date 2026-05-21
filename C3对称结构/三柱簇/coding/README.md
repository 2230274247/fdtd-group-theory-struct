# 三柱簇 C3 扰动脚本说明

## 母结构实际参数

- 源文件位置：`H:\FDTD outcome\struct\群论_struct\C3对称结构\三柱簇\fsp`
- 脚本只读源 `.fsp`，先复制到 results 工作母版，再为每个扫描点复制单独副本后修改。
- 衬底：SiO2，尺寸约 `0.900 um x 0.900 um`，厚度 `1.000 um`。
- 三个 Si_pillar：母版半径 `0.095 um`，中心半径约 `0.210 um`，厚度约 `0.420 um`。
- 透射监视器：`T`；输出图统一为 `|T|^2`。

## 已生成脚本

- `改单个柱子扰动/run_fdtd_single_pillar_radius_sweep.py`：只改变一个柱半径，降群路径 `C3 -> C1`。
- `单点偏移扰动/run_fdtd_single_pillar_offset_sweep.py`：只把一个柱沿径向外移，降群路径 `C3 -> C1`。
- `三柱同步半径扫描扰动/run_fdtd_all_pillar_radius_sweep.py`：三柱同步改变半径，降群路径 `C3 -> C3`。
- `其中两柱同改扰动/run_fdtd_two_pillar_radius_sweep.py`：两个柱同步改半径，第三个保持母版；默认 `C3 -> Cs/C1`。

## 运行模式

脚本运行后会询问：

- `1`：测试模式，只真实仿真前 3 个点。
- `2`：完整真实仿真。
- `3`：预览模式，只生成扫描计划和结构说明，不运行 FDTD。

也可以用命令行参数直接指定，例如：

`python run_fdtd_single_pillar_radius_sweep.py --preview`

