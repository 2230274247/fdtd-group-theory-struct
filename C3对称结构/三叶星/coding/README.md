# 三叶星 C3 扰动脚本说明

## 母结构实际参数

- 源文件位置：`H:\FDTD outcome\struct\群论_struct\C3对称结构\三叶星\fsp`
- 若同目录存在多个 `.fsp`，脚本优先使用文件名时间戳较新的版本。
- 衬底：SiO2，尺寸约 `0.900 um x 0.900 um`，厚度 `1.000 um`。
- 三个 Si_lobe：单臂宽度 `0.120 um`，单臂长度 `0.440 um`，厚度约 `0.420 um`。
- 三臂旋转角：`0 deg / 120 deg / 240 deg`。
- 透射监视器：`T`；输出图统一为 `|T|^2`。

## 已生成脚本

- `单臂长度差扰动/run_fdtd_single_arm_length_sweep.py`：只改变一个臂的长度，降群路径 `C3 -> C1`。
- `单臂宽度差扰动/run_fdtd_single_arm_width_sweep.py`：只改变一个臂的宽度，降群路径 `C3 -> C1`。
- `单臂转角扰动/run_fdtd_single_arm_angle_sweep.py`：只改变一个臂的相对转角，降群路径 `C3 -> C1`。
- `三臂同步缩放扰动/run_fdtd_all_arm_scale_sweep.py`：三臂同步按比例缩放宽和长，降群路径 `C3 -> C3`。

## 用户修改区

每个脚本开头都有“用户主要修改区”。常用修改项包括：

- 扫描起点、终点、步长。
- `AUTO_*_STEP`：是否按目标扫描点数自动重算步长。
- `TARGET_ARM_INDEX`：选择被扰动的单臂。
- `SIMULATION_TIME_S` 与 `AUTO_SHUTOFF_MIN`：控制单次仿真的时间上限和收敛阈值。

所有结果统一保存到：

`H:\FDTD outcome\struct\群论_struct\C3对称结构\三叶星\results\扰动名\run_模式_时间戳`

