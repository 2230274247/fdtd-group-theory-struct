# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c2_sweep_common import run

# ========================= 用户主要修改区 =========================
START_NM = 80.0
END_NM = 160.0
STEP_NM = 10.0
WIDTH_START_NM = START_NM
WIDTH_STOP_NM = END_NM
WIDTH_STEP_NM = STEP_NM
AUTO_STEP = True
TARGET_SCAN_POINTS = 9
STEP_MIN_NM = 5.0
STEP_MAX_NM = 10.0

SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

CONFIG = dict(
    STRUCTURE_ROOT='H:\\FDTD outcome\\struct\\群论_struct\\C2对称结构\\双梁',
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
    STRUCTURE_CN_NAME='双梁',
    SAFE_NAME='dual_beams',
    OBJECT_NAME='Si_beam',
    GEOMETRY_OBJECTS=('Si_beam',),
    PERTURBATION_NAME='同步梁宽扫描扰动',
    GROUP_PATH='保持 C2',
    OPERATION='set_y_span',
    OPERATION_DESCRIPTION='左右两个 Si_beam 同步设置 y span。',
    TARGET_INDICES=(1, 2),
    VALUE_NAME='beam_width',
    SCAN_LABEL='all_beam_width',
    USER_GUIDE=['同步梁宽扫描保持 C2。'],
    SCAN_START_NM=WIDTH_START_NM,
    SCAN_STOP_NM=WIDTH_STOP_NM,
    SCAN_STEP_NM=WIDTH_STEP_NM,
    AUTO_SCAN_STEP=AUTO_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=STEP_MIN_NM,
    SCAN_STEP_MAX_NM=STEP_MAX_NM,
)

if __name__ == "__main__":
    run(CONFIG)
