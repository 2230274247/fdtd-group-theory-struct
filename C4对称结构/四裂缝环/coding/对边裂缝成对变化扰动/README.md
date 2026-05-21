# 四裂缝环 / 扰动 2：对边裂缝成对变化

脚本：`run_fdtd_opposite_pair_slit_width_sweep.py`

## 实现内容

同步改变两条相对裂缝的宽度 `x span`，另外两条裂缝保持母版宽度。默认改变 0° 和 180° 两条裂缝，即索引 `(1, 3)`。

## 降群路径

`C4 -> C2`

对边成对变化保留二重旋转特征，适合观察 C4 到 C2 的模式分裂。

## 母结构真实参数

- 外环半径：300 nm
- 内孔半径：190 nm
- 环宽：110 nm
- 裂缝中心半径：270 nm
- 裂缝宽度：60 nm
- 裂缝长度：180 nm
- Si 厚度：420 nm
- 衬底尺寸：900 nm x 900 nm x 1000 nm

## 主要可修改参数

- `OPPOSITE_PAIR_INDICES`：默认 `(1, 3)`，可改为 `(2, 4)`
- `WIDTH_START_M` / `WIDTH_STOP_M` / `WIDTH_STEP_M`
- `AUTO_STEP` / `TARGET_POINTS`
- `SIMULATION_TIME_S`
- `RUN_MODE`

结果保存到 `results\对边裂缝成对变化扰动\run_模式_时间戳\`。
