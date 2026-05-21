# -*- coding: utf-8 -*-
"""四裂缝环扰动 1：改单裂缝宽度。降群路径：C4 -> C1。"""

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

# 安全余量：裂缝宽度会被限制在环宽以内。
RADIAL_CLEARANCE_M = 10e-9
AUTO_STEP = True
TARGET_POINTS = 11
STEP_MIN_M = 2.5e-9
STEP_MAX_M = 10e-9
INCLUDE_EXACT_STOP_POINT = True

# 选择要改变的裂缝：1=0度右侧，2=90度上侧，3=180度左侧，4=270度下侧。
SINGLE_SLIT_INDEX = 1

# 母版裂缝宽度 x span = 60 nm，建议先扫 30-100 nm。
MIN_SLIT_WIDTH_M = 20e-9
MAX_SLIT_WIDTH_M = 110e-9
START_M = 30e-9
END_M = 100e-9
STEP_M = 5e-9
WIDTH_START_M = START_M
WIDTH_STOP_M = END_M
WIDTH_STEP_M = STEP_M


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
    "perturbation_name": "改单裂缝宽度扰动",
    "kind": "single_width",
    "changed_parameter": "只改变一条 air_slit 的 x span，其他三条裂缝保持母版宽度",
    "group_path": "C4 -> C1",
    "expected_effect": "单裂缝宽度破缺会增强局部散射，适合观察暗模变亮和线宽变化。",
    "point_label": "single_slit_width",
    "single_slit_index": SINGLE_SLIT_INDEX,
    "min_slit_width_m": MIN_SLIT_WIDTH_M,
    "max_slit_width_m": MAX_SLIT_WIDTH_M,
    "width_start_m": WIDTH_START_M,
    "width_stop_m": WIDTH_STOP_M,
    "width_step_m": WIDTH_STEP_M,
}

if __name__ == "__main__":
    run(CONFIG)
