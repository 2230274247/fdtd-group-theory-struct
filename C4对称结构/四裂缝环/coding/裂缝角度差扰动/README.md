# 四裂缝环 / 扰动 3：裂缝角度差

脚本：`run_fdtd_single_slit_angle_sweep.py`

## 实现内容

改变一条裂缝的角向位置和自身 `rotation 1`。默认改变索引 1，即 0° 右侧裂缝。

## 降群路径

`C4 -> C1`

裂缝角度错位会破坏四条裂缝的等角间隔，属于角向破缺扰动。

## 母结构真实参数

- 外环半径：300 nm
- 内孔半径：190 nm
- 裂缝中心半径：270 nm
- 四条裂缝角度：0°、90°、180°、270°
- 裂缝宽度：60 nm
- 裂缝长度：180 nm
- Si 厚度：420 nm

## 主要可修改参数

- `SINGLE_SLIT_INDEX`：要改变角度的裂缝
- `ANGLE_START_DEG` / `ANGLE_STOP_DEG` / `ANGLE_STEP_DEG`
- `AUTO_STEP` / `TARGET_POINTS`
- `SIMULATION_TIME_S`
- `RUN_MODE`

结果保存到 `results\裂缝角度差扰动\run_模式_时间戳\`。
