# 双椭圆 C2 扰动脚本说明

## 已确认的母结构参数

- 实际对象名：`Si_ellipse_L_rect_approx` 与 `Si_ellipse_R_rect_approx`，不是 `Si_ellipse`。
- 该母结构在 FSP 中由两个旋转矩形近似椭圆：x span `0.130 um`，y span `0.400 um`。
- 左/右 rotation 1 = `-25 deg` / `+25 deg`，中心 x = -0.180 / +0.180 um。

## 已生成脚本

- `转角差扰动/run_fdtd_ellipse_angle_difference_sweep.py`：右侧转角差，C2 -> C1
- `长轴差扰动/run_fdtd_ellipse_long_axis_difference_sweep.py`：右侧长轴差，C2 -> C1
- `短轴差扰动/run_fdtd_ellipse_short_axis_difference_sweep.py`：右侧短轴差，C2 -> C1
- `间距差扰动/run_fdtd_ellipse_spacing_difference_sweep.py`：右侧位置差，C2 -> C1

## 共同规则

- 源 `.fsp` 只读，不会被修改。
- 每次运行先复制源文件到 results 工作母版，再为每个扫描点复制单独 `.fsp`。
- 结果保存到 `results/扰动名/run_模式_时间戳/`。
- 运行模式：1 测试、2 完整仿真、3 预览。
