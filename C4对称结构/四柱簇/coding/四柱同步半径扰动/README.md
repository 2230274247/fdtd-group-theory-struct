# 扰动 4：四柱同步半径

脚本：`run_fdtd_all_pillar_radius_sweep.py`

## 实现内容

四个 `Si_pillar` 同步改变半径，柱中心位置和厚度不变。

## 默认降群路径

`C4 -> C4`

同步半径扫描不破坏 C4 对称性，适合作为四柱簇的整体尺寸调谐基线。

## 默认可修改参数

- `RADIUS_START_NM = 60.0`
- `RADIUS_STOP_NM = 130.0`
- `AUTO_RADIUS_STEP = True`
- `TARGET_SCAN_POINTS = 8`
- `MIN_GAP_NM = 20.0`
- `EDGE_CLEARANCE_NM = 25.0`

脚本会自动根据柱间最小距离限制最大半径，避免柱子互相重叠。
