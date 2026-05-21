# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c2_sweep_common import run

# ========================= 用户主要修改区 =========================
START_NM = 0.0
END_NM = 35.0
STEP_NM = 5.0
DX_START_NM = START_NM
DX_STOP_NM = END_NM
DX_STEP_NM = STEP_NM
AUTO_STEP = True
TARGET_SCAN_POINTS = 8
STEP_MIN_NM = 5.0
STEP_MAX_NM = 5.0

SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

CONFIG = dict(
    STRUCTURE_ROOT='H:\\FDTD outcome\\struct\\群论_struct\\C2对称结构\\双椭圆',
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
    STRUCTURE_CN_NAME='双椭圆',
    SAFE_NAME='dual_ellipses',
    GEOMETRY_OBJECTS=('Si_ellipse_L_rect_approx', 'Si_ellipse_R_rect_approx'),
    OBJECT_NAME='Si_ellipse_R_rect_approx',
    PERTURBATION_NAME='间距差扰动',
    GROUP_PATH='C2 -> C1',
    OPERATION='offset_single',
    OPERATION_DESCRIPTION='只移动右侧近似椭圆的 x 坐标。',
    TARGET_INDICES=(1,),
    VALUE_NAME='right_ellipse_dx',
    SCAN_LABEL='ellipse_spacing_difference',
    USER_GUIDE=['母版中心 x = -0.180 / +0.180 um；dx 为右侧额外 +x 位移。'],
    OFFSET_AXIS='x',
    SCAN_START_NM=DX_START_NM,
    SCAN_STOP_NM=DX_STOP_NM,
    SCAN_STEP_NM=DX_STEP_NM,
    AUTO_SCAN_STEP=AUTO_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=STEP_MIN_NM,
    SCAN_STEP_MAX_NM=STEP_MAX_NM,
)

if __name__ == "__main__":
    run(CONFIG)
