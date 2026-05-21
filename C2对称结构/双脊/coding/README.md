# 双脊 C2 扰动脚本说明

## 已确认的母结构参数

- 对象名：`Si_slab` 数量 1，`Si_ridge` 数量 2。
- slab 尺寸 `0.740 um x 0.740 um x 0.080 um`。
- 脊 x span `0.110 um`，y span `0.560 um`，z span `0.340 um`，中心 x = -0.160 / +0.160 um。

## 已生成脚本

- `脊宽差扰动/run_fdtd_ridge_width_difference_sweep.py`：右脊宽度差，C2 -> C1
- `顶部槽差扰动/run_fdtd_ridge_top_slot_sweep.py`：右脊顶部开槽，C2 -> C1
- `位置差扰动/run_fdtd_ridge_position_difference_sweep.py`：右脊位置差，C2 -> C1
- `脊高差扰动/run_fdtd_ridge_height_difference_sweep.py`：右脊高度差，C2 -> C1

## 共同规则

- 源 `.fsp` 只读，不会被修改。
- 每次运行先复制源文件到 results 工作母版，再为每个扫描点复制单独 `.fsp`。
- 结果保存到 `results/扰动名/run_模式_时间戳/`。
- 运行模式：1 测试、2 完整仿真、3 预览。
