# 十字扰动 1：横竖臂长度差自动化仿真

本文件夹用于实现 `十字 / 扰动 1：横竖臂长度差` 的 FDTD 自动化扫描。脚本会复制十字母版 `.fsp`，只改变水平臂对象 `Si_cross_horizontal` 的 x span（竖直臂不变），每次改变都运行一次仿真。

## 文件

- `run_fdtd_arm_length_diff_sweep.py`：主脚本。
- 输出目录：运行后自动生成在 `十字/results/横竖臂长度差扰动/时间戳目录`。

## 扰动定义

- **扰动名称**：横竖臂长度差
- **改变参数**：水平臂 `Si_cross_horizontal` 的 x span
- **delta 定义**：`delta = (horizontal_x_span - vertical_y_span) / 2`
- **降群路径**：C4 -> C2
- **默认扫描范围**：delta = -100 nm 到 +100 nm，步长 10 nm

## 运行模式

```python
RUN_MODE = "ask"  # "ask" / "test" / "full" / "preview"
```

命令行：`--preview`、`--test-run`、`--full-run`、`--resume`
