# 四孔方块 / 扰动 1：改单孔半径

## 脚本位置

`run_fdtd_single_hole_radius_sweep.py`

## 脚本实现内容

本脚本用于控制四孔方块母版 `.fsp`，只改变其中一个空气孔 `air_hole` 的半径，其余三个孔的位置和半径保持母版值不变。每一个半径点都会独立复制母版 `.fsp`，在副本上修改参数并运行 FDTD 仿真。

每个仿真点完成后会保存：

- 本点修改后的 `.fsp`
- 透射谱 abs^2 图片 `.png`
- 透射谱源数据 Excel `.xlsx`
- `manifest.csv`
- `scan_points.csv`
- `结构状态说明.md`

## 降群路径

`C4 -> C1`

改单孔半径会破坏四重旋转对称，也通常会破坏镜面对称，因此是比较强的局域扰动。

## 从母版 .fsp 读取到的结构参数

- Si 方块对象：`Si_square_host`
- 空气孔对象：`air_hole`
- SiO2 衬底对象：`SiO2_substrate`
- Si 方块尺寸：600 nm x 600 nm
- Si 方块厚度：420 nm
- SiO2 衬底尺寸：900 nm x 900 nm
- SiO2 衬底厚度：1000 nm
- 母版空气孔半径：55 nm
- 母版半孔距：160 nm
- 四个孔索引：
  - 1：左下
  - 2：右下
  - 3：左上
  - 4：右上

## 用户主要可修改参数

在脚本顶部“用户主要修改区”中可修改：

- `SINGLE_HOLE_INDEX`：选择要改变的孔，默认 `4`
- `RADIUS_START_M`：半径扫描起点，默认 `35e-9`
- `RADIUS_STOP_M`：半径扫描终点，默认 `85e-9`
- `RADIUS_STEP_M`：手动步长，默认 `5e-9`
- `AUTO_STEP`：是否自动根据范围和目标点数计算步长
- `TARGET_POINTS`：自动步长模式下的目标扫描点数
- `EDGE_CLEARANCE_M`：孔边缘与方块边缘的安全余量
- `SIMULATION_TIME_S`：仿真时间
- `AUTO_SHUTOFF_MIN`：最小 auto shutoff 阈值
- `RUN_MODE`：运行模式，支持 `ask/test/full/preview`

## 结果保存位置

结果统一保存到：

`H:\FDTD outcome\struct\群论_struct\C4对称结构\四孔方块\results\改单孔半径扰动\run_模式_时间戳\`

脚本不会修改 `fsp` 文件夹中的源 `.fsp`。运行开始和结束会检查源 `.fsp` 的 SHA256 指纹，若源文件发生变化会立刻报错。
