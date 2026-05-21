# -*- coding: utf-8 -*-
"""
四孔方块扰动 5：孔距同步扫描 FDTD 自动化扫描脚本

降群路径：保持 C4
动作：四个孔同步向内/向外移动，保持正方形排布。
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
STEP_MIN_M = 5e-9
STEP_MAX_M = 15e-9
INCLUDE_EXACT_STOP_POINT = True

# half pitch 是单个孔中心到结构中心的 |x|=|y| 距离。
# 母版 half pitch 为 160 nm；实际相邻孔心距为 320 nm。
START_M = 100e-9
END_M = 220e-9
STEP_M = 10e-9
PITCH_START_M = START_M
PITCH_STOP_M = END_M
PITCH_STEP_M = STEP_M


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
    "perturbation_name": "孔距同步扫描扰动",
    "kind": "pitch_scan",
    "changed_parameter": "四个孔同步向内/向外移动，保持正方形排布与 C4 对称",
    "group_path": "保持 C4",
    "expected_effect": "改变四孔与边界及彼此之间的耦合强度，适合作为保持对称性的结构调谐基线。",
    "point_label": "hole_pitch",
    "pitch_start_m": PITCH_START_M,
    "pitch_stop_m": PITCH_STOP_M,
    "pitch_step_m": PITCH_STEP_M,
}


if __name__ == "__main__":
    run(CONFIG)
