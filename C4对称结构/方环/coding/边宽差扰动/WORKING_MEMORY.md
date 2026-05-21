# 本系列 FDTD 自动化脚本的继承规则

这份文档记录当前项目已经约定好的自动化脚本规则。后续继续写方环或其他扰动脚本时，应默认继承这些要求。

## 目录与命名

1. 每一种扰动都放在对应结构 `coding` 目录下的独立文件夹中。
2. 脚本、README、运行输出都放在该扰动文件夹内。
3. 输出统一放在 `results/扰动名称/` 下，并按批次时间戳新建目录。
4. 输出批次目录内固定使用：
   - `00_scan_plan`
   - `01_fsp_files`
   - `02_transmission_excel`
   - `03_transmission_png_abs2`
   - `04_logs`

## FSP 文件处理

1. 原始 `.fsp` 可以位于中文路径。
2. 脚本必须先把原始 `.fsp` 复制到本批次结果目录下的 `05_work_fsp` 工作目录，作为 `master_template.fsp`。
3. 每一个扫描点都必须从 `master_template.fsp` 再复制出独立的 `work_*.fsp`。
4. 参数修改只能发生在当前扫描点的 `work_*.fsp` 上。
5. 每次仿真结束后，必须立刻保存该扫描点对应的 `.fsp`。

## 扫描与参数

1. 脚本顶部必须有清晰的"用户主要修改区"。
2. 固定结构参数和扫描参数都要写在用户容易看到的位置。
3. 固定结构参数默认不改变，只改变当前扰动所要求的变量。
4. 扫描步长、范围、方向要写清楚，并在运行前生成 `scan_points.csv`。
5. 对几何安全边界要做检查，例如孔不能移出结构边界。

## 运行模式

1. 必须支持 `RUN_MODE = "ask"`、`"test"`、`"full"`、`"preview"`。
2. `ask` 模式运行时输入数字选择：
   - `1`：测试模式，真实仿真 3 次。
   - `2`：完整仿真。
   - `3`：预览模式，不仿真。
3. 必须支持命令行参数：
   - `--preview`
   - `--test-run`
   - `--full-run`
   - `--resume`
   - `--run-dir`
   - `--show-gui`
   - `--max-points`

## 数据输出

1. 透射谱图片必须使用 `abs(T)^2`，图中标注为 `|T|^2`。
2. Excel 源数据至少包含：
   - wavelength
   - frequency
   - T_real
   - T_imag
   - T_abs2
3. 每个扫描点都要写入 `manifest.csv`，记录状态、偏移量、输出文件路径和耗时。
4. 运行过程要写入 `automation_run.log`。

## 兼容性

1. 脚本必须兼容 Lumerical v202 自带 Python 3.6.8。
2. 不使用 `from __future__ import annotations`。
3. 不使用 `dataclasses`。
4. 不使用 `list[str]`、`dict[str, ...]`、`str | None` 等新版类型写法。
5. 尽量只依赖 Lumerical 自带的 `lumapi`、`numpy`、`matplotlib`，Excel 文件用标准库生成。

## 当前方环结构数据

1. 外框对象：`Si_outer_square`
2. 内孔对象：`air_inner_square`
3. 透射监视器：`T`
4. 外框尺寸：约 `580 nm x 580 nm`
5. 内孔尺寸：约 `300 nm x 300 nm`
6. 结构厚度：约 `420 nm`
7. 周期：`900 nm`
8. 材料：外框 Si (Silicon) - Palik，内孔 etch
