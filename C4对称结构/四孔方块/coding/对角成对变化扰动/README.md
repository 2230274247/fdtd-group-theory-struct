# 四孔方块 / 扰动 2：对角成对变化

## 脚本位置

`run_fdtd_diagonal_pair_radius_sweep.py`

## 脚本实现内容

本脚本用于同步改变四孔方块中一条对角线上的两个空气孔半径，另一条对角线上的两个孔保持母版半径。每个扫描点都会从母版副本继续复制出独立工作 `.fsp`，只在该工作副本上修改并运行仿真。

默认改变的孔为：

- `air_hole` 索引 1：左下
- `air_hole` 索引 4：右上

可在脚本中把 `DIAGONAL_PAIR_INDICES = (1, 4)` 改为 `(2, 3)`，切换到另一条对角线。

## 降群路径

`C4 -> C2`

一条对角线上的两个孔同步变化后，结构不再具有四重旋转对称，但仍可近似保留二重旋转特征，因此是比较清晰的 C4 到 C2 降群方式。

## 从母版 .fsp 读取到的结构参数

- Si 方块对象：`Si_square_host`
- 空气孔对象：`air_hole`
- Si 方块尺寸：600 nm x 600 nm
- Si 方块厚度：420 nm
- SiO2 衬底尺寸：900 nm x 900 nm
- SiO2 衬底厚度：1000 nm
- 母版空气孔半径：55 nm
- 母版半孔距：160 nm
- 四孔位置：`(+/-160 nm, +/-160 nm)`

## 用户主要可修改参数

- `DIAGONAL_PAIR_INDICES`：选择同步变化的对角孔，默认 `(1, 4)`
- `RADIUS_START_M`：对角孔半径扫描起点，默认 `35e-9`
- `RADIUS_STOP_M`：对角孔半径扫描终点，默认 `85e-9`
- `RADIUS_STEP_M`：手动步长，默认 `5e-9`
- `AUTO_STEP`：是否自动步长
- `TARGET_POINTS`：自动步长目标点数
- `EDGE_CLEARANCE_M`：边界安全余量
- `SIMULATION_TIME_S`：仿真时间
- `AUTO_SHUTOFF_MIN`：最小 auto shutoff 阈值
- `RUN_MODE`：运行模式

## 结果保存位置

结果统一保存到：

`H:\FDTD outcome\struct\群论_struct\C4对称结构\四孔方块\results\对角成对变化扰动\run_模式_时间戳\`

源 `.fsp` 只读不写；脚本会自动使用 results 工作母版和英文镜像工作副本进行仿真。
