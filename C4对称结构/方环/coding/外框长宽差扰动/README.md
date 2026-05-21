# 方环扰动 5：外框长宽差自动化仿真

本文件夹用于实现 `方环 / 扰动 5：外框长宽差` 的 FDTD 自动化扫描。脚本会复制方环母版 `.fsp`，保持外框面积不变，改变外框对象 `Si_outer_square` 的 x span 和 y span（使长宽比不等于 1），每次改变都运行一次仿真，并立刻保存本次 `.fsp`、透射谱 `|T|^2` 图片、透射谱 Excel 源数据和日志。

## 文件

- `run_fdtd_outer_aspect_ratio_sweep.py`：主脚本。
- `WORKING_MEMORY.md`：本系列脚本需要继承的工作规则。
- 输出目录：运行后自动生成在 `方环/results/外框长宽差扰动/时间戳目录`。

## 扰动定义

- **扰动名称**：外框长宽差
- **改变参数**：外框 `Si_outer_square` 的 x span 和 y span（面积保持不变）
- **delta 定义**：`delta = aspect_ratio - 1.0`，其中 `aspect_ratio = outer_x_span / outer_y_span`
- **降群路径**：C4 -> C2
- **几何说明**：aspect_ratio = 1.0 时为正方形外框（C4 对称）；aspect_ratio > 1 时 x 方向更长（C2 对称）
- **面积守恒**：`outer_x_span * outer_y_span = base_span^2`

## 已从当前方环 FSP 中读取到的关键结构

- 母版 FSP 目录：`H:\FDTD outcome\struct\群论_struct\C4对称结构\方环\fsp`
- 外框对象：`Si_outer_square`
- 内孔对象：`air_inner_square`
- 透射监视器：`T`
- 外框尺寸：约 `580 nm x 580 nm`
- 内孔尺寸：约 `300 nm x 300 nm`
- 结构厚度：约 `420 nm`

## 运行模式

脚本顶部有一个用户修改区：

```python
RUN_MODE = "ask"
TEST_POINT_COUNT = 3

ASPECT_RATIO_START = 1.0
ASPECT_RATIO_STOP = 1.5
ASPECT_RATIO_STEP = 0.05
```

命令行参数：

```powershell
# 测试模式
python "run_fdtd_outer_aspect_ratio_sweep.py" --test-run

# 预览模式
python "run_fdtd_outer_aspect_ratio_sweep.py" --preview

# 完整仿真
python "run_fdtd_outer_aspect_ratio_sweep.py" --full-run
```

## 输出目录结构

```text
方环/
  results/
    外框长宽差扰动/
      run_时间戳/
        结构状态说明.md
        00_scan_plan/
          scan_points.csv
          scan_summary.txt
        01_fsp_files/
          *.fsp
        02_transmission_excel/
          *.xlsx
        03_transmission_png_abs2/
          *.png
        04_logs/
          manifest.csv
          automation_run.log
```

## 注意

首次建议先用 `--preview` 检查扫描点，再用 `--test-run` 跑 3 个真实点。如果 3 个点都能正常输出，再运行完整扫描。
