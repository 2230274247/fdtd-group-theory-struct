# 四孔方块 / 扰动 4：四孔同步孔径

## 脚本位置

`run_fdtd_all_hole_radius_sweep.py`

## 脚本实现内容

本脚本用于同步改变四个空气孔的半径，孔中心位置保持母版值。由于四个孔完全同步变化，因此结构整体仍保持 C4 对称。

该扰动非常适合作为对照组：它会改变整体孔径和有效折射率分布，但不会引入降群破缺。

## 降群路径

保持 `C4`

四孔同步孔径不会破坏四重旋转对称，可用于和改单孔半径、对角成对变化、单孔偏移等降群扰动做对照。

## 从母版 .fsp 读取到的结构参数

- Si 方块对象：`Si_square_host`
- 空气孔对象：`air_hole`
- Si 方块尺寸：600 nm x 600 nm
- Si 方块厚度：420 nm
- SiO2 衬底尺寸：900 nm x 900 nm
- SiO2 衬底厚度：1000 nm
- 母版孔半径：55 nm
- 母版半孔距：160 nm

## 用户主要可修改参数

- `RADIUS_START_M`：四孔同步半径扫描起点，默认 `30e-9`
- `RADIUS_STOP_M`：四孔同步半径扫描终点，默认 `90e-9`
- `RADIUS_STEP_M`：手动步长，默认 `5e-9`
- `MIN_HOLE_RADIUS_M` / `MAX_HOLE_RADIUS_M`：允许半径范围
- `AUTO_STEP`：是否自动计算步长
- `TARGET_POINTS`：自动步长目标点数
- `EDGE_CLEARANCE_M`：边界安全余量
- `SIMULATION_TIME_S`：仿真时间
- `RUN_MODE`：运行模式

## 结果保存位置

结果统一保存到：

`H:\FDTD outcome\struct\群论_struct\C4对称结构\四孔方块\results\四孔同步孔径扰动\run_模式_时间戳\`

脚本会保存每个半径点的 `.fsp`、透射谱 abs^2 图片和 Excel 数据。
