# 四裂缝环 / 扰动 4：裂缝长度差

脚本：`run_fdtd_single_slit_length_sweep.py`

## 实现内容

只改变一条裂缝的长度 `y span`，其他裂缝保持母版长度。默认改变索引 1。

## 降群路径

`C4 -> C1`

单裂缝长度变化会改变局部切穿程度和局域辐射耦合。

## 母结构真实参数

- 外环半径：300 nm
- 内孔半径：190 nm
- 裂缝中心半径：270 nm
- 裂缝宽度：60 nm
- 母版裂缝长度：180 nm
- Si 厚度：420 nm
- 衬底厚度：1000 nm

## 主要可修改参数

- `SINGLE_SLIT_INDEX`
- `LENGTH_START_M` / `LENGTH_STOP_M` / `LENGTH_STEP_M`
- `AUTO_STEP` / `TARGET_POINTS`
- `SIMULATION_TIME_S`
- `RUN_MODE`

结果保存到 `results\裂缝长度差扰动\run_模式_时间戳\`。
