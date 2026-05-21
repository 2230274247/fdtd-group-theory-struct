# 三裂缝环 C3 扰动脚本说明

## 母结构实际参数

- 源文件位置：`H:\FDTD outcome\struct\群论_struct\C3对称结构\三裂缝环\fsp`
- 脚本会自动选择文件名时间戳较新的 `.fsp` 作为源文件，并只读复制，不会修改源文件。
- 衬底：SiO2，尺寸约 `0.900 um x 0.900 um`，厚度 `1.000 um`。
- Si 外环半径：`0.310 um`。
- 内孔半径：`0.200 um`。
- 环厚度方向 Si 高度：约 `0.420 um`。
- 三条 air_slit：宽度 `0.050 um`，长度 `0.170 um`，角度约 `90 deg / 210 deg / 330 deg`。
- 透射监视器：`T`；输出图统一为 `|T|^2`。

## 已生成脚本

- `单裂缝宽度扰动/run_fdtd_single_slit_width_sweep.py`：只改变一道裂缝宽度，降群路径 `C3 -> C1`。
- `单裂缝角度扰动/run_fdtd_single_slit_angle_sweep.py`：只改变一道裂缝相对角度，降群路径 `C3 -> C1`。
- `单裂缝长度扰动/run_fdtd_single_slit_length_sweep.py`：只改变一道裂缝长度，降群路径 `C3 -> C1`。
- `三裂缝同步宽度扰动/run_fdtd_all_slit_width_sweep.py`：三道裂缝同步改宽，降群路径 `C3 -> C3`。

## 运行与结果目录

运行任一脚本后，结果会进入：

`H:\FDTD outcome\struct\群论_struct\C3对称结构\三裂缝环\results\扰动名\run_模式_时间戳`

其中包括：

- `00_scan_plan`：扫描点表。
- `01_fsp`：每个扫描点保存后的 FSP 副本。
- `02_transmission_excel`：透射谱原始数据 Excel。
- `03_transmission_abs2_png`：透射谱 `|T|^2` 图片。
- `04_logs`：manifest 运行索引。
- `05_work_fsp`：该轮运行的工作母版。

