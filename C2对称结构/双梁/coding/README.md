# 双梁 C2 扰动脚本说明

## 已确认的母结构参数

- 对象名：`Si_beam`，数量 2。
- 母版 x span `0.300 um`，y span `0.120 um`，中心 x = -0.210 / +0.210 um。
- Si 高度 `0.420 um`，衬底 `0.900 um x 0.900 um x 1.000 um`。

## 已生成脚本

- `梁宽差扰动/run_fdtd_beam_width_difference_sweep.py`：右梁宽度差，C2 -> C1
- `梁长差扰动/run_fdtd_beam_length_difference_sweep.py`：右梁长度差，C2 -> C1
- `梁偏移扰动/run_fdtd_beam_offset_sweep.py`：右梁位移，C2 -> C1
- `同步梁宽扫描扰动/run_fdtd_all_beam_width_sweep.py`：双梁同步改宽，保持 C2

## 共同规则

- 源 `.fsp` 只读，不会被修改。
- 每次运行先复制源文件到 results 工作母版，再为每个扫描点复制单独 `.fsp`。
- 结果保存到 `results/扰动名/run_模式_时间戳/`。
- 运行模式：1 测试、2 完整仿真、3 预览。
