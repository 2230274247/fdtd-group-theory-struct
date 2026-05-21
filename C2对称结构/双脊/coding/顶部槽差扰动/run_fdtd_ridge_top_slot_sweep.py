# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c2_sweep_common import run

# ========================= 用户主要修改区 =========================
START_NM = 0.0
END_NM = 25.0
STEP_NM = 5.0
W_START_NM = START_NM
W_STOP_NM = END_NM
W_STEP_NM = STEP_NM
AUTO_STEP = True
TARGET_SCAN_POINTS = 6
STEP_MIN_NM = 5.0
STEP_MAX_NM = 5.0

SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

CONFIG = dict(
    STRUCTURE_ROOT='H:\\FDTD outcome\\struct\\群论_struct\\C2对称结构\\双脊',
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
    STRUCTURE_CN_NAME='双脊',
    SAFE_NAME='dual_ridges',
    OBJECT_NAME='Si_ridge',
    GEOMETRY_OBJECTS=('Si_slab', 'Si_ridge'),
    PERTURBATION_NAME='顶部槽差扰动',
    GROUP_PATH='C2 -> C1',
    OPERATION='insert_top_slot',
    OPERATION_DESCRIPTION='只在右侧 Si_ridge 顶部插入局部 etch 槽。',
    TARGET_INDICES=(2,),
    VALUE_NAME='top_slot_width',
    SCAN_LABEL='ridge_top_slot',
    USER_GUIDE=['槽宽从 0 开始；0 nm 时不插入槽，作为基线。'],
    SCAN_START_NM=W_START_NM,
    SCAN_STOP_NM=W_STOP_NM,
    SCAN_STEP_NM=W_STEP_NM,
    AUTO_SCAN_STEP=AUTO_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=STEP_MIN_NM,
    SCAN_STEP_MAX_NM=STEP_MAX_NM,
    SLOT_DEPTH_NM=35.0,
)

if __name__ == "__main__":
    run(CONFIG)
