# -*- coding: utf-8 -*-
"""
四柱簇 - 扰动 2：对边柱子成对半径变化
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from four_pillar_cluster_common import run


# ========================= 用户主要修改区 =========================
RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3

# 对边成对改变：
# (1, 3)=左右一对，保留 180° 旋转，通常 C4 降到 C2；
# (2, 4)=上下形成另一条 C2 轴。
PAIR_PILLAR_INDICES = (1, 3)

# 母版半径约 95 nm。建议范围 60-130 nm。
START_NM = 60.0
END_NM = 130.0
STEP_NM = 10.0
RADIUS_START_NM = START_NM
RADIUS_STOP_NM = END_NM
RADIUS_STEP_NM = STEP_NM

AUTO_RADIUS_STEP = True
TARGET_SCAN_POINTS = 8
RADIUS_STEP_MIN_NM = 5.0
RADIUS_STEP_MAX_NM = 15.0

MIN_GAP_NM = 20.0
EDGE_CLEARANCE_NM = 25.0

SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8
# ================================================================


CONFIG = {
    "STRUCTURE_ROOT": r"H:\FDTD outcome\struct\群论_struct\C4对称结构\四柱簇",
    "LUMERICAL_ROOT": r"D:\Program Files\Lumerical\v202",
    "ASCII_WORK_ROOT": r"H:\FDTD_CodeX\fdtd_ascii_work",
    "PERTURBATION_NAME": "对边成对变化扰动",
    "PERTURBATION_TYPE": "opposite_pair_radius",
    "GROUP_PATH": "C4 -> C2",
    "PILLAR_OBJECT_NAME": "Si_pillar",
    "SUBSTRATE_OBJECT_NAME": "SiO2_substrate",
    "FDTD_OBJECT_NAME": "FDTD",
    "T_MONITOR_NAME": "T",
    "RUN_MODE_DEFAULT": RUN_MODE_DEFAULT,
    "TEST_POINT_COUNT": TEST_POINT_COUNT,
    "PAIR_PILLAR_INDICES": PAIR_PILLAR_INDICES,
    "RADIUS_START_NM": RADIUS_START_NM,
    "RADIUS_STOP_NM": RADIUS_STOP_NM,
    "RADIUS_STEP_NM": RADIUS_STEP_NM,
    "AUTO_RADIUS_STEP": AUTO_RADIUS_STEP,
    "TARGET_SCAN_POINTS": TARGET_SCAN_POINTS,
    "RADIUS_STEP_MIN_NM": RADIUS_STEP_MIN_NM,
    "RADIUS_STEP_MAX_NM": RADIUS_STEP_MAX_NM,
    "MIN_GAP_NM": MIN_GAP_NM,
    "EDGE_CLEARANCE_NM": EDGE_CLEARANCE_NM,
    "SIMULATION_TIME_FS": SIMULATION_TIME_FS,
    "SIMULATION_TIME_S": SIMULATION_TIME_S,
    "AUTO_SHUTOFF_MIN": AUTO_SHUTOFF_MIN,
    "MESH_ACCURACY": MESH_ACCURACY,
    "DT_STABILITY_FACTOR": DT_STABILITY_FACTOR,
}


if __name__ == "__main__":
    run(CONFIG)
