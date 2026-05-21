# -*- coding: utf-8 -*-
"""
四孔方块扰动 4：四孔同步孔径 FDTD 自动化扫描脚本

降群路径：保持 C4
动作：四个 air_hole 半径同步改变，孔位保持母版值。
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
TARGET_POINTS = 13
STEP_MIN_M = 2.5e-9
STEP_MAX_M = 10e-9
INCLUDE_EXACT_STOP_POINT = True

# 母版孔半径约 55 nm；同步孔径是保持 C4 的对照型扫描。
MIN_HOLE_RADIUS_M = 25e-9
MAX_HOLE_RADIUS_M = 95e-9
START_M = 30e-9
END_M = 90e-9
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
    "perturbation_name": "四孔同步孔径扰动",
    "kind": "all_radius",
    "changed_parameter": "四个 air_hole 半径同步改变，孔位保持母版值",
    "group_path": "保持 C4",
    "expected_effect": "保持对称性的全局孔径调参，适合作为区分尺寸调谐与降群效应的对照组。",
    "point_label": "all_hole_radius",
    "min_hole_radius_m": MIN_HOLE_RADIUS_M,
    "max_hole_radius_m": MAX_HOLE_RADIUS_M,
    "radius_start_m": RADIUS_START_M,
    "radius_stop_m": RADIUS_STOP_M,
    "radius_step_m": RADIUS_STEP_M,
}


if __name__ == "__main__":
    run(CONFIG)
