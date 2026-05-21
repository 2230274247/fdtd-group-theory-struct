# -*- coding: utf-8 -*-
"""
四孔方块扰动 2：对角成对变化 FDTD 自动化扫描脚本

降群路径：C4 -> C2
动作：同步改变一条对角线上的两个孔半径，另一条对角线保持母版半径。
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
TARGET_POINTS = 11
STEP_MIN_M = 2.5e-9
STEP_MAX_M = 10e-9
INCLUDE_EXACT_STOP_POINT = True

# 对角孔索引：默认 1 和 4，即左下 + 右上；也可改成 (2, 3)。
DIAGONAL_PAIR_INDICES = (1, 4)

# 母版孔半径约 55 nm。
MIN_HOLE_RADIUS_M = 25e-9
MAX_HOLE_RADIUS_M = 95e-9
START_M = 35e-9
END_M = 85e-9
STEP_M = 5e-9
RADIUS_START_M = START_M
RADIUS_STOP_M = END_M
RADIUS_STEP_M = STEP_M


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
    "perturbation_name": "对角成对变化扰动",
    "kind": "diagonal_pair_radius",
    "changed_parameter": "同步改变一条对角线上的两个孔半径，另一条对角线保持母版半径",
    "group_path": "C4 -> C2",
    "expected_effect": "对角成对孔径变化保留二重旋转特征，适合观察 C4 到 C2 的谱峰分裂。",
    "point_label": "diagonal_pair_radius",
    "diagonal_pair_indices": DIAGONAL_PAIR_INDICES,
    "min_hole_radius_m": MIN_HOLE_RADIUS_M,
    "max_hole_radius_m": MAX_HOLE_RADIUS_M,
    "radius_start_m": RADIUS_START_M,
    "radius_stop_m": RADIUS_STOP_M,
    "radius_step_m": RADIUS_STEP_M,
}


if __name__ == "__main__":
    run(CONFIG)
