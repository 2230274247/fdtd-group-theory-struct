# -*- coding: utf-8 -*-
"""
四孔方块扰动 3：单孔偏移 FDTD 自动化扫描脚本

降群路径：C4 -> C1
动作：只移动一个孔的中心位置，孔半径保持母版值。
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from four_hole_square_common import run


# =============================================================================
# 用户主要修改区
# =============================================================================

LUMERICAL_ROOT = Path(r"D:\Program Files\Lumerical\v202")
HOST_OBJECT_NAME = "Si_square_host"
HOLE_OBJECT_NAME = "air_hole"
SUBSTRATE_OBJECT_NAME = "SiO2_substrate"
FDTD_OBJECT_NAME = "FDTD"
TRANSMISSION_MONITOR_NAME = "T"

SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

RUN_MODE = "ask"
TEST_POINT_COUNT = 3

EDGE_CLEARANCE_M = 10e-9
AUTO_STEP = True
TARGET_POINTS = 9
STEP_MIN_M = 5e-9
STEP_MAX_M = 15e-9
INCLUDE_EXACT_STOP_POINT = True

# 选择要偏移的孔：默认 4=右上。
OFFSET_HOLE_INDEX = 4

# 偏移方向。默认沿 +x；可改为 (0, 1)、(1, 1)、(-1, 0) 等。
OFFSET_DIRECTION = (1.0, 0.0)

# 偏移距离。脚本会按方块边界、孔半径和安全余量自动裁剪最大值。
START_M = 0e-9
END_M = 80e-9
STEP_M = 10e-9
OFFSET_START_M = START_M
OFFSET_STOP_M = END_M
OFFSET_STEP_M = STEP_M


CONFIG = {
    "script_file": __file__,
    "lumerical_root": LUMERICAL_ROOT,
    "host_object_name": HOST_OBJECT_NAME,
    "hole_object_name": HOLE_OBJECT_NAME,
    "substrate_object_name": SUBSTRATE_OBJECT_NAME,
    "fdtd_object_name": FDTD_OBJECT_NAME,
    "transmission_monitor_name": TRANSMISSION_MONITOR_NAME,
    "simulation_time_fs": SIMULATION_TIME_FS,
    "simulation_time_s": SIMULATION_TIME_S,
    "auto_shutoff_min": AUTO_SHUTOFF_MIN,
    "mesh_accuracy": MESH_ACCURACY,
    "dt_stability_factor": DT_STABILITY_FACTOR,
    "run_mode": RUN_MODE,
    "test_point_count": TEST_POINT_COUNT,
    "edge_clearance_m": EDGE_CLEARANCE_M,
    "auto_step": AUTO_STEP,
    "target_points": TARGET_POINTS,
    "step_min_m": STEP_MIN_M,
    "step_max_m": STEP_MAX_M,
    "include_exact_stop": INCLUDE_EXACT_STOP_POINT,
    "perturbation_name": "单孔偏移扰动",
    "kind": "single_offset",
    "changed_parameter": "只移动一个 air_hole 的中心位置，孔半径保持母版值",
    "group_path": "C4 -> C1",
    "expected_effect": "单孔偏移破缺最强，常用于打开局部散射通道，观察线宽随偏移增强。",
    "point_label": "single_hole_offset",
    "offset_hole_index": OFFSET_HOLE_INDEX,
    "offset_direction": OFFSET_DIRECTION,
    "offset_start_m": OFFSET_START_M,
    "offset_stop_m": OFFSET_STOP_M,
    "offset_step_m": OFFSET_STEP_M,
}


if __name__ == "__main__":
    run(CONFIG)
