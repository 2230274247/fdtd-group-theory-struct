# -*- coding: utf-8 -*-
"""
四柱簇 - 扰动 1：改单个柱子半径

运行方式：
1. 直接运行本文件，按提示输入 1/2/3；
2. 或命令行追加 --test / --full / --preview。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from four_pillar_cluster_common import run


# ========================= 用户主要修改区 =========================
# 运行模式：
# "ask"     每次运行时输出 1/2/3 让你选择；
# "test"    只真实仿真前 TEST_POINT_COUNT 个点；
# "full"    完整真实仿真；
# "preview" 只生成扫描计划和说明文档，不运行 FDTD。
RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3

# 要改变哪一个柱子：
# 1=右侧柱 (x=+200 nm), 2=上侧柱, 3=左侧柱, 4=下侧柱。
TARGET_PILLAR_INDEX = 1

# 半径扫描范围，单位 nm。
# 母版半径约 95 nm。建议范围 60-130 nm。
# 脚本会根据柱子之间最小间距和边界留白自动截断过大的终点，避免柱子相交或贴边。
START_NM = 60.0
END_NM = 130.0
STEP_NM = 10.0
RADIUS_START_NM = START_NM
RADIUS_STOP_NM = END_NM
RADIUS_STEP_NM = STEP_NM

# 是否自动计算步长。
# True：按 TARGET_SCAN_POINTS 自动算步长，并限制在 STEP_MIN/STEP_MAX 之间；
# False：严格使用 RADIUS_STEP_NM。
AUTO_RADIUS_STEP = True
TARGET_SCAN_POINTS = 8
RADIUS_STEP_MIN_NM = 5.0
RADIUS_STEP_MAX_NM = 15.0

# 安全间隔，单位 nm。柱子与柱子、柱子与周期边界至少保留这个距离。
MIN_GAP_NM = 20.0
EDGE_CLEARANCE_NM = 25.0

# FDTD 运行控制。沿用当前母版较稳妥的设置：50 ps，auto shutoff min=1e-7。
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
    "PERTURBATION_NAME": "改单个柱子扰动",
    "PERTURBATION_TYPE": "single_radius",
    "GROUP_PATH": "C4 -> C1",
    "PILLAR_OBJECT_NAME": "Si_pillar",
    "SUBSTRATE_OBJECT_NAME": "SiO2_substrate",
    "FDTD_OBJECT_NAME": "FDTD",
    "T_MONITOR_NAME": "T",
    "RUN_MODE_DEFAULT": RUN_MODE_DEFAULT,
    "TEST_POINT_COUNT": TEST_POINT_COUNT,
    "TARGET_PILLAR_INDEX": TARGET_PILLAR_INDEX,
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
