# -*- coding: utf-8 -*-
"""
四孔方块扰动 1：改单孔半径 FDTD 自动化扫描脚本

降群路径：C4 -> C1
动作：只改变一个 air_hole 的半径，其他三个孔保持母版半径。
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

# 仿真时间与最小收敛阈值。若谱线很窄或 auto shutoff 不收敛，可增大 SIMULATION_TIME_S。
SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

# ask/test/full/preview。ask 会在运行时让你输入 1/2/3。
RUN_MODE = "ask"
TEST_POINT_COUNT = 3

# 几何安全边界：孔边缘距离 Si 方块边缘至少保留 10 nm。
EDGE_CLEARANCE_M = 10e-9

# 自适应步长。关闭 AUTO_STEP 后使用 RADIUS_STEP_M。
AUTO_STEP = True
TARGET_POINTS = 11
STEP_MIN_M = 2.5e-9
STEP_MAX_M = 10e-9
INCLUDE_EXACT_STOP_POINT = True

# 选择要改变的孔：1=左下，2=右下，3=左上，4=右上。
SINGLE_HOLE_INDEX = 4

# 母版孔半径约 55 nm；建议先在 35-85 nm 粗扫。
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
    "perturbation_name": "改单孔半径扰动",
    "kind": "single_radius",
    "changed_parameter": "只改变一个 air_hole 的半径，其他三个孔保持母版半径",
    "group_path": "C4 -> C1",
    "expected_effect": "单点孔径破缺会打开非对称辐射通道，适合观察暗模变亮和 Fano 线形变化。",
    "point_label": "single_hole_radius",
    "single_hole_index": SINGLE_HOLE_INDEX,
    "min_hole_radius_m": MIN_HOLE_RADIUS_M,
    "max_hole_radius_m": MAX_HOLE_RADIUS_M,
    "radius_start_m": RADIUS_START_M,
    "radius_stop_m": RADIUS_STOP_M,
    "radius_step_m": RADIUS_STEP_M,
}


if __name__ == "__main__":
    run(CONFIG)
