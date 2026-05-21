# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c2_sweep_common import run

# ========================= 用户主要修改区 =========================
START_NM = 300.0
END_NM = 430.0
STEP_NM = 10.0
SPACING_START_NM = START_NM
SPACING_STOP_NM = END_NM
SPACING_STEP_NM = STEP_NM
AUTO_STEP = True
TARGET_SCAN_POINTS = 14
STEP_MIN_NM = 10.0
STEP_MAX_NM = 10.0

SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

CONFIG = dict(
    STRUCTURE_ROOT='H:\\FDTD outcome\\struct\\群论_struct\\C2对称结构\\双柱',
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
    STRUCTURE_CN_NAME='双柱',
    SAFE_NAME='dual_pillars',
    OBJECT_NAME='Si_pillar',
    GEOMETRY_OBJECTS=('Si_pillar',),
    PERTURBATION_NAME='间距扫描扰动',
    GROUP_PATH='保持 C2',
    OPERATION='set_pair_spacing_x',
    OPERATION_DESCRIPTION='左右两个 Si_pillar 同步移动，使中心距等于扫描值。',
    TARGET_INDICES=(1, 2),
    VALUE_NAME='pillar_spacing',
    SCAN_LABEL='pillar_spacing',
    SCAN_START_NM=SPACING_START_NM,
    SCAN_STOP_NM=SPACING_STOP_NM,
    SCAN_STEP_NM=SPACING_STEP_NM,
    AUTO_SCAN_STEP=AUTO_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=STEP_MIN_NM,
    SCAN_STEP_MAX_NM=STEP_MAX_NM,
    USER_GUIDE=['扫描值是两柱中心距；母版中心距 0.360 um。'],
)

if __name__ == "__main__":
    run(CONFIG)
