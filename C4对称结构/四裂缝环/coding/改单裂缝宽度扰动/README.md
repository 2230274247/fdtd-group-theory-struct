# 四裂缝环 / 扰动 1：改单裂缝宽度

脚本：`run_fdtd_single_slit_width_sweep.py`

## 实现内容

只改变一条 `air_slit` 的 `x span`，即裂缝宽度，其他三条裂缝保持母版宽度。

## 降群路径

`C4 -> C1`

改单裂缝宽度会破坏四重旋转对称，是强局域扰动。

## 母结构真实参数

- 外环对象：`Si_outer_ring`，半径 300 nm
- 内孔对象：`air_inner_ring`，半径 190 nm
- 裂缝对象：`air_slit`，共 4 条
- 裂缝中心半径：270 nm
- 裂缝宽度 `x span`：60 nm
- 裂缝长度 `y span`：180 nm
- Si 厚度：420 nm
- SiO2 衬底：900 nm x 900 nm，厚度 1000 nm

## 主要可修改参数

- `SINGLE_SLIT_INDEX`：要改变的裂缝，默认 1
- `WIDTH_START_M` / `WIDTH_STOP_M` / `WIDTH_STEP_M`
- `AUTO_STEP` / `TARGET_POINTS`
- `SIMULATION_TIME_S`
- `RUN_MODE`

结果保存到 `results\改单裂缝宽度扰动\run_模式_时间戳\`。
