# 扰动 1：改单个柱子半径

脚本：`run_fdtd_single_pillar_radius_sweep.py`

## 实现内容

只改变一个 `Si_pillar` 的半径，其余三个柱子的半径、位置、厚度，以及衬底和仿真区域保持母版参数。

## 默认降群路径

`C4 -> C1`

改单个柱子会破坏 90° 旋转对称，也通常破坏镜面对称，因此按一般扰动处理为 C1。

## 默认可修改参数

- `TARGET_PILLAR_INDEX = 1`：默认改变右侧柱；
- `RADIUS_START_NM = 60.0`
- `RADIUS_STOP_NM = 130.0`
- `AUTO_RADIUS_STEP = True`
- `TARGET_SCAN_POINTS = 8`
- `MIN_GAP_NM = 20.0`
- `EDGE_CLEARANCE_NM = 25.0`

脚本会根据柱间距和边界留白自动截断过大的半径终点。
