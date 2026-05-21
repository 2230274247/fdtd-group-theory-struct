# 双柱 C2 扰动脚本说明

## 已确认的母结构参数

- 对象名：`Si_pillar`，数量 2。
- 母版半径 `0.120 um`，两柱中心 x = -0.180 / +0.180 um。
- Si 高度 `0.420 um`，衬底 `0.900 um x 0.900 um x 1.000 um`。

## 已生成脚本

- `左右半径差扰动/run_fdtd_pillar_radius_difference_sweep.py`：右柱半径差，C2 -> C1
- `左右位置差扰动/run_fdtd_pillar_position_difference_sweep.py`：右柱位置差，C2 -> C1
- `间距扫描扰动/run_fdtd_pillar_spacing_sweep.py`：两柱同步改中心距，保持 C2
- `高度差扰动/run_fdtd_pillar_height_difference_sweep.py`：右柱高度差，C2 -> C1

## 共同规则

- 源 `.fsp` 只读，不会被修改。
- 每次运行先复制源文件到 results 工作母版，再为每个扫描点复制单独 `.fsp`。
- 结果保存到 `results/扰动名/run_模式_时间戳/`。
- 运行模式：1 测试、2 完整仿真、3 预览。
