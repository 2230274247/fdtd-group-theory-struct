# 十字扰动 3：单臂长度变化自动化仿真

本文件夹用于实现 `十字 / 扰动 3：单臂长度变化` 的 FDTD 自动化扫描。只改变水平臂的 x span，竖直臂完全不动。

## 扰动定义

- **扰动名称**：单臂长度变化
- **改变参数**：水平臂 `Si_cross_horizontal` 的 x span
- **delta 定义**：`delta = horizontal_x_span - vertical_y_span`
- **降群路径**：C4 -> C1
- **默认扫描范围**：200 nm 到 700 nm，步长 25 nm

## 运行模式

命令行：`--preview`、`--test-run`、`--full-run`、`--resume`
