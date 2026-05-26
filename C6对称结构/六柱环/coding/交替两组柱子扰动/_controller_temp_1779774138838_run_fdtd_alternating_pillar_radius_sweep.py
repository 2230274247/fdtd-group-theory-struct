# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c6_sweep_common import run

RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3
ALTERNATING_GROUP_INDICES = (1, 3, 5)
START_NM = 45.0
END_NM = 105.0
STEP_NM = 10.0
RADIUS_START_NM = START_NM
RADIUS_STOP_NM = END_NM
RADIUS_STEP_NM = STEP_NM
AUTO_RADIUS_STEP = True
TARGET_SCAN_POINTS = 7
RADIUS_STEP_MIN_NM = 5.0
RADIUS_STEP_MAX_NM = 15.0
SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

CONFIG = dict(
    STRUCTURE_ROOT=r"H:\FDTD outcome\struct\群论_struct\C6对称结构\六柱环",
    STRUCTURE_CN_NAME="六柱环",
    SAFE_NAME="six_pillar_ring",
    LUMERICAL_ROOT=r"D:\Program Files\Lumerical\v202",
    ASCII_WORK_ROOT=r"H:\FDTD_CodeX\fdtd_ascii_work",
    PERTURBATION_NAME="交替两组柱子扰动",
    GROUP_PATH="C6 -> C3",
    OBJECT_NAME="Si_pillar",
    OPERATION="set_radius",
    OPERATION_DESCRIPTION="改变 1/3/5 三个间隔柱子的半径，2/4/6 保持母版半径，形成交替两组。",
    TARGET_INDICES=ALTERNATING_GROUP_INDICES,
    VALUE_NAME="pillar_radius",
    SCAN_LABEL="alternating_pillar_radius",
    SCAN_START_NM=RADIUS_START_NM,
    SCAN_STOP_NM=RADIUS_STOP_NM,
    SCAN_STEP_NM=RADIUS_STEP_NM,
    AUTO_SCAN_STEP=AUTO_RADIUS_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=RADIUS_STEP_MIN_NM,
    SCAN_STEP_MAX_NM=RADIUS_STEP_MAX_NM,
    TEST_POINT_COUNT=TEST_POINT_COUNT,
    RUN_MODE_DEFAULT=RUN_MODE_DEFAULT,
    SIMULATION_TIME_FS=SIMULATION_TIME_FS,
    SIMULATION_TIME_S=SIMULATION_TIME_S,
    AUTO_SHUTOFF_MIN=AUTO_SHUTOFF_MIN,
    MESH_ACCURACY=MESH_ACCURACY,
    DT_STABILITY_FACTOR=DT_STABILITY_FACTOR,
    T_MONITOR_NAME="T",
)


# Runtime overrides injected by fdtd_master_controller.py
CONFIG.update({'auto_retry_enabled': True, 'AUTO_RETRY_ENABLED': True, 'autoretryenabled': True, 'auto_retry_max': 'adaptive', 'AUTO_RETRY_MAX': 'adaptive', 'autoretrymax': 'adaptive', 'quality_t_limit': 1.03, 'QUALITY_T_LIMIT': 1.03, 'qualitytlimit': 1.03, 'quality_ripple_limit': 0.12, 'QUALITY_RIPPLE_LIMIT': 0.12, 'qualityripplelimit': 0.12})

if __name__ == "__main__":
    run(CONFIG)
