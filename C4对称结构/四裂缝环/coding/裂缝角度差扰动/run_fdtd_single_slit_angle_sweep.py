# -*- coding: utf-8 -*-
"""四裂缝环扰动 3：裂缝角度差。降群路径：C4 -> C1。"""

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
TARGET_POINTS = 9
STEP_MIN_M = 2.5e-9
STEP_MAX_M = 10e-9
ANGLE_STEP_MIN_DEG = 2.5
ANGLE_STEP_MAX_DEG = 10.0
INCLUDE_EXACT_STOP_POINT = True

# 选择要改变角度的裂缝。脚本会同时改变该裂缝中心角位置和自身 rotation。
SINGLE_SLIT_INDEX = 1
START_DEG = 0.0
END_DEG = 40.0
STEP_DEG = 5.0
ANGLE_START_DEG = START_DEG
ANGLE_STOP_DEG = END_DEG
ANGLE_STEP_DEG = STEP_DEG


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
    "angle_step_min_deg": ANGLE_STEP_MIN_DEG,
    "angle_step_max_deg": ANGLE_STEP_MAX_DEG,
    "include_exact_stop": INCLUDE_EXACT_STOP_POINT,
    "perturbation_name": "裂缝角度差扰动",
    "kind": "single_angle",
    "changed_parameter": "改变一条 air_slit 的角向位置和 rotation 角度",
    "group_path": "C4 -> C1",
    "expected_effect": "裂缝角度错位会破坏等角间隔，适合观察角向散射扰动引起的谱线变化。",
    "point_label": "single_slit_angle_delta",
    "single_slit_index": SINGLE_SLIT_INDEX,
    "angle_start_deg": ANGLE_START_DEG,
    "angle_stop_deg": ANGLE_STOP_DEG,
    "angle_step_deg": ANGLE_STEP_DEG,
}

if __name__ == "__main__":
    run(CONFIG)
