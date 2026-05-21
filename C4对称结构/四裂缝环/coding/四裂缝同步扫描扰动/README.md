# 四裂缝环 / 扰动 5：四裂缝同步扫描

脚本：`run_fdtd_all_slit_width_sweep.py`

## 实现内容

四条 `air_slit` 的宽度 `x span` 同步变化，裂缝位置、角度和长度保持母版设置。

## 降群路径

保持 `C4`

这是对照型扫描，用来区分整体尺寸调谐和真正降群扰动带来的谱线变化。

## 母结构真实参数

- 外环半径：300 nm
- 内孔半径：190 nm
- 环宽：110 nm
- 裂缝中心半径：270 nm
- 母版裂缝宽度：60 nm
- 母版裂缝长度：180 nm
- Si 厚度：420 nm
- 衬底尺寸：900 nm x 900 nm x 1000 nm

## 主要可修改参数

- `WIDTH_START_M` / `WIDTH_STOP_M` / `WIDTH_STEP_M`
- `AUTO_STEP` / `TARGET_POINTS`
- `SIMULATION_TIME_S`
- `RUN_MODE`

结果保存到 `results\四裂缝同步扫描扰动\run_模式_时间戳\`。
