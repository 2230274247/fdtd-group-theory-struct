# 扰动 3：单柱偏移

脚本：`run_fdtd_single_pillar_offset_sweep.py`

## 实现内容

移动一个柱子的中心位置，不改变柱半径和厚度。默认移动右侧柱，并沿 `+x` 方向向外偏移。

## 默认降群路径

`C4 -> C1`

单柱偏移会破坏 90° 旋转和整体等价性，按一般低对称扰动处理为 C1。

## 默认可修改参数

- `TARGET_PILLAR_INDEX = 1`
- `OFFSET_DIRECTION_X = 1.0`
- `OFFSET_DIRECTION_Y = 0.0`
- `OFFSET_START_NM = 0.0`
- `OFFSET_STOP_NM = 120.0`
- `AUTO_OFFSET_STEP = True`
- `TARGET_SCAN_POINTS = 9`
- `EDGE_CLEARANCE_NM = 25.0`

偏移终点会根据衬底/周期边界、柱半径和边界留白自动截断。
