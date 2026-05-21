# 扰动 2：对边成对变化

脚本：`run_fdtd_opposite_pair_pillar_radius_sweep.py`

## 实现内容

同步改变一组对边柱子的半径，默认改变左右两个柱子 `(1, 3)`，上下两个柱子保持母版半径。

## 默认降群路径

`C4 -> C2`

左右对边同步变化后，结构仍保留 180° 旋转，但不再保留 90° 旋转。

## 默认可修改参数

- `PAIR_PILLAR_INDICES = (1, 3)`：左右对边；可改为 `(2, 4)`；
- `RADIUS_START_NM = 60.0`
- `RADIUS_STOP_NM = 130.0`
- `AUTO_RADIUS_STEP = True`
- `TARGET_SCAN_POINTS = 8`

半径终点会被柱间距和边界留白自动限制。
