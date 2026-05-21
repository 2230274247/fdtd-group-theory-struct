# 双圆盘 C2 扰动脚本说明

## 已确认的母结构参数

- 对象名：`Si_disk`，数量 2。
- 母版半径 `0.145 um`，中心 x = -0.180 / +0.180 um。
- Si 高度 `0.420 um`，衬底 `0.900 um x 0.900 um x 1.000 um`。

## 已生成脚本

- `半径差扰动/run_fdtd_disk_radius_difference_sweep.py`：右盘半径差，C2 -> C1
- `非对称位移扰动/run_fdtd_disk_asymmetric_offset_sweep.py`：右盘位移，C2 -> C1
- `单盘开孔扰动/run_fdtd_single_disk_hole_sweep.py`：右盘开孔，C2 -> C1
- `双盘同步开孔扰动/run_fdtd_all_disk_hole_sweep.py`：双盘同步开孔，保持 C2

## 共同规则

- 源 `.fsp` 只读，不会被修改。
- 每次运行先复制源文件到 results 工作母版，再为每个扫描点复制单独 `.fsp`。
- 结果保存到 `results/扰动名/run_模式_时间戳/`。
- 运行模式：1 测试、2 完整仿真、3 预览。
