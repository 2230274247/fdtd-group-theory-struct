# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c2_sweep_common import run

# ========================= 用户主要修改区 =========================
START_DEG = 0.0
END_DEG = 30.0
STEP_DEG = 5.0
ANGLE_START_DEG = START_DEG
ANGLE_STOP_DEG = END_DEG
ANGLE_STEP_DEG = STEP_DEG
AUTO_STEP = True
TARGET_SCAN_POINTS = 7
STEP_MIN_DEG = 2.5
STEP_MAX_DEG = 5.0

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
    PERTURBATION_NAME='转角差扰动',
    GROUP_PATH='C2 -> C1',
    OPERATION='set_rotation_delta',
    OPERATION_DESCRIPTION='只改变右侧 Si_ellipse_R_rect_approx 的 rotation 1。',
    TARGET_INDICES=(1,),
    VALUE_NAME='right_ellipse_angle_delta',
    SCAN_LABEL='ellipse_angle_difference',
    USER_GUIDE=['母版左右 rotation 1 = -25 / +25 deg；扫描值为右侧额外角度。'],
    SCAN_UNIT='deg',
    SCAN_START_DEG=ANGLE_START_DEG,
    SCAN_STOP_DEG=ANGLE_STOP_DEG,
    SCAN_STEP_DEG=ANGLE_STEP_DEG,
    AUTO_SCAN_STEP=AUTO_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_DEG=STEP_MIN_DEG,
    SCAN_STEP_MAX_DEG=STEP_MAX_DEG,
)

if __name__ == "__main__":
    run(CONFIG)
