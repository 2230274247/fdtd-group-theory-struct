# -*- coding: utf-8 -*-
"""
四柱簇 - 扰动 3：单柱偏移
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from four_pillar_cluster_common import run


# ========================= 用户主要修改区 =========================
RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3

# 要移动哪一个柱子：1=右，2=上，3=左，4=下。
TARGET_PILLAR_INDEX = 1

# 偏移方向。默认把右侧柱沿 +x 方向向外移动。
# 若 TARGET_PILLAR_INDEX=2，可把方向改成 (0, 1)；3 可改成 (-1, 0)；4 可改成 (0, -1)。
OFFSET_DIRECTION_X = 1.0
OFFSET_DIRECTION_Y = 0.0

# 偏移量扫描，单位 nm。
# 母版右柱中心 x=200 nm，周期半宽 450 nm，半径 95 nm；
# 默认保留 25 nm 边界留白，因此向外最大约 130 nm，脚本会自动截断。
START_NM = 0.0
END_NM = 120.0
STEP_NM = 15.0
OFFSET_START_NM = START_NM
OFFSET_STOP_NM = END_NM
OFFSET_STEP_NM = STEP_NM

AUTO_OFFSET_STEP = True
TARGET_SCAN_POINTS = 9
OFFSET_STEP_MIN_NM = 5.0
OFFSET_STEP_MAX_NM = 20.0

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
    "PERTURBATION_NAME": "单柱偏移扰动",
    "PERTURBATION_TYPE": "single_offset",
    "GROUP_PATH": "C4 -> C1",
    "PILLAR_OBJECT_NAME": "Si_pillar",
    "SUBSTRATE_OBJECT_NAME": "SiO2_substrate",
    "FDTD_OBJECT_NAME": "FDTD",
    "T_MONITOR_NAME": "T",
    "RUN_MODE_DEFAULT": RUN_MODE_DEFAULT,
    "TEST_POINT_COUNT": TEST_POINT_COUNT,
    "TARGET_PILLAR_INDEX": TARGET_PILLAR_INDEX,
    "OFFSET_DIRECTION_X": OFFSET_DIRECTION_X,
    "OFFSET_DIRECTION_Y": OFFSET_DIRECTION_Y,
    "OFFSET_START_NM": OFFSET_START_NM,
    "OFFSET_STOP_NM": OFFSET_STOP_NM,
    "OFFSET_STEP_NM": OFFSET_STEP_NM,
    "AUTO_OFFSET_STEP": AUTO_OFFSET_STEP,
    "TARGET_SCAN_POINTS": TARGET_SCAN_POINTS,
    "OFFSET_STEP_MIN_NM": OFFSET_STEP_MIN_NM,
    "OFFSET_STEP_MAX_NM": OFFSET_STEP_MAX_NM,
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
