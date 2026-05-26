# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c2_sweep_common import run

# ========================= 用户主要修改区 =========================
START_NM = 0.0
END_NM = 30.0
STEP_NM = 5.0
DELTA_START_NM = START_NM
DELTA_STOP_NM = END_NM
DELTA_STEP_NM = STEP_NM
AUTO_STEP = True
TARGET_SCAN_POINTS = 7
STEP_MIN_NM = 5.0
STEP_MAX_NM = 5.0

SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

CONFIG = dict(
    STRUCTURE_ROOT='H:\\FDTD outcome\\struct\\群论_struct\\C2对称结构\\双圆盘',
    LUMERICAL_ROOT='D:\\Program Files\\Lumerical\\v202',
    ASCII_WORK_ROOT='H:\\FDTD_CodeX\\fdtd_ascii_work',
    RUN_MODE_DEFAULT='ask',
    TEST_POINT_COUNT=3,
    SIMULATION_TIME_FS=SIMULATION_TIME_FS,
    SIMULATION_TIME_S=SIMULATION_TIME_S,
    AUTO_SHUTOFF_MIN=AUTO_SHUTOFF_MIN,
    MESH_ACCURACY=MESH_ACCURACY,
    DT_STABILITY_FACTOR=DT_STABILITY_FACTOR,
    T_MONITOR_NAME='T',
    STRUCTURE_CN_NAME='双圆盘',
    SAFE_NAME='dual_disks',
    OBJECT_NAME='Si_disk',
    GEOMETRY_OBJECTS=('Si_disk',),
    PERTURBATION_NAME='半径差扰动',
    GROUP_PATH='C2 -> C1',
    OPERATION='set_radius_delta',
    OPERATION_DESCRIPTION='只减小右侧 Si_disk 半径，左盘保持母版半径。',
    TARGET_INDICES=(2,),
    VALUE_NAME='disk_radius_difference',
    SCAN_LABEL='disk_radius_difference',
    USER_GUIDE=['母版圆盘半径 0.145 um；delta 越大，右盘越小。'],
    SCAN_START_NM=DELTA_START_NM,
    SCAN_STOP_NM=DELTA_STOP_NM,
    SCAN_STEP_NM=DELTA_STEP_NM,
    AUTO_SCAN_STEP=AUTO_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=STEP_MIN_NM,
    SCAN_STEP_MAX_NM=STEP_MAX_NM,
    MIN_RADIUS_NM=80.0,
)


# Runtime overrides injected by fdtd_master_controller.py
CONFIG.update({'auto_retry_max': 'adaptive', 'AUTO_RETRY_MAX': 'adaptive', 'autoretrymax': 'adaptive', 'quality_t_limit': 1.01, 'QUALITY_T_LIMIT': 1.01, 'qualitytlimit': 1.01})

if __name__ == "__main__":
    run(CONFIG)
