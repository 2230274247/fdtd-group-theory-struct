# -*- coding: utf-8 -*-
"""四裂缝环扰动 4：裂缝长度差。降群路径：C4 -> C1。"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from four_slit_ring_common import run


# =============================================================================
# 用户主要修改区
# =============================================================================

LUMERICAL_ROOT = Path(r"D:\Program Files\Lumerical\v202")
OUTER_RING_OBJECT_NAME = "Si_outer_ring"
INNER_RING_OBJECT_NAME = "air_inner_ring"
SLIT_OBJECT_NAME = "air_slit"
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

RADIAL_CLEARANCE_M = 10e-9
AUTO_STEP = True
TARGET_POINTS = 11
STEP_MIN_M = 5e-9
STEP_MAX_M = 20e-9
INCLUDE_EXACT_STOP_POINT = True

SINGLE_SLIT_INDEX = 1

# 母版裂缝长度 y span = 180 nm。
MIN_SLIT_LENGTH_M = 80e-9
MAX_SLIT_LENGTH_M = 260e-9
START_M = 100e-9
END_M = 240e-9
STEP_M = 10e-9
LENGTH_START_M = START_M
LENGTH_STOP_M = END_M
LENGTH_STEP_M = STEP_M


CONFIG = {
    "script_file": __file__,
    "lumerical_root": LUMERICAL_ROOT,
    "outer_ring_object_name": OUTER_RING_OBJECT_NAME,
    "inner_ring_object_name": INNER_RING_OBJECT_NAME,
    "slit_object_name": SLIT_OBJECT_NAME,
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
    "radial_clearance_m": RADIAL_CLEARANCE_M,
    "auto_step": AUTO_STEP,
    "target_points": TARGET_POINTS,
    "step_min_m": STEP_MIN_M,
    "step_max_m": STEP_MAX_M,
    "include_exact_stop": INCLUDE_EXACT_STOP_POINT,
    "perturbation_name": "裂缝长度差扰动",
    "kind": "single_length",
    "changed_parameter": "只改变一条 air_slit 的 y span，其他裂缝保持母版长度",
    "group_path": "C4 -> C1",
    "expected_effect": "单裂缝长度变化改变局部切穿程度和辐射耦合，容易引起暗模亮化和峰位移动。",
    "point_label": "single_slit_length",
    "single_slit_index": SINGLE_SLIT_INDEX,
    "min_slit_length_m": MIN_SLIT_LENGTH_M,
    "max_slit_length_m": MAX_SLIT_LENGTH_M,
    "length_start_m": LENGTH_START_M,
    "length_stop_m": LENGTH_STOP_M,
    "length_step_m": LENGTH_STEP_M,
}

if __name__ == "__main__":
    run(CONFIG)
