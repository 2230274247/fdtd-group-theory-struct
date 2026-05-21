# 十字扰动 2：横竖臂宽度差自动化仿真

本文件夹用于实现 `十字 / 扰动 2：横竖臂宽度差` 的 FDTD 自动化扫描。只改变水平臂的 y span（宽度），竖直臂和臂长度不变。

## 扰动定义

- **扰动名称**：横竖臂宽度差
- **改变参数**：水平臂 `Si_cross_horizontal` 的 y span
- **delta 定义**：`delta = (horizontal_y_span - vertical_x_span) / 2`
- **降群路径**：C4 -> C2
- **默认扫描范围**：delta = -40 nm 到 +40 nm，步长 5 nm

## 运行模式

命令行：`--preview`、`--test-run`、`--full-run`、`--resume`
