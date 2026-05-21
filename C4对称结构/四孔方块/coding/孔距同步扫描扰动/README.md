# 四孔方块 / 扰动 5：孔距同步扫描

## 脚本位置

`run_fdtd_hole_pitch_sweep.py`

## 脚本实现内容

本脚本用于同步改变四个空气孔到结构中心的距离，即保持正方形排布，让四个孔同时向内或向外移动。

脚本中的 `half pitch` 表示单个孔中心到结构中心的距离：

- 左下孔：`(-half_pitch, -half_pitch)`
- 右下孔：`(+half_pitch, -half_pitch)`
- 左上孔：`(-half_pitch, +half_pitch)`
- 右上孔：`(+half_pitch, +half_pitch)`

母版 `half pitch` 为 160 nm，因此相邻孔心距为 320 nm。

## 降群路径

保持 `C4`

孔距同步扫描保持四孔正方形排布，不破坏四重旋转对称。它主要用于研究孔间耦合、孔与外边界耦合对透射谱的影响。

## 从母版 .fsp 读取到的结构参数

- Si 方块尺寸：600 nm x 600 nm
- Si 方块厚度：420 nm
- SiO2 衬底尺寸：900 nm x 900 nm
- SiO2 衬底厚度：1000 nm
- 母版孔半径：55 nm
- 母版 half pitch：160 nm
- 母版相邻孔心距：320 nm

## 用户主要可修改参数

- `PITCH_START_M`：half pitch 扫描起点，默认 `100e-9`
- `PITCH_STOP_M`：half pitch 扫描终点，默认 `220e-9`
- `PITCH_STEP_M`：手动步长，默认 `10e-9`
- `AUTO_STEP`：是否自动计算步长
- `TARGET_POINTS`：自动步长目标点数
- `EDGE_CLEARANCE_M`：孔边缘到方块边缘的安全余量
- `SIMULATION_TIME_S`：仿真时间
- `RUN_MODE`：运行模式

脚本会自动根据方块尺寸、孔半径和边界安全距离裁剪最大/最小 half pitch，避免孔重叠或跑出方块。

## 结果保存位置

结果统一保存到：

`H:\FDTD outcome\struct\群论_struct\C4对称结构\四孔方块\results\孔距同步扫描扰动\run_模式_时间戳\`

源 `.fsp` 不会被修改；每个扫描点都会在独立工作副本上运行。
