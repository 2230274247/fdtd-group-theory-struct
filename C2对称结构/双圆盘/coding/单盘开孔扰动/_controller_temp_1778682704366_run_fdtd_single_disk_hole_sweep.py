# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c2_sweep_common import run

# ========================= 用户主要修改区 =========================
START_NM = 0
END_NM = 50
STEP_NM = 1
R_START_NM = START_NM
R_STOP_NM = END_NM
R_STEP_NM = STEP_NM
AUTO_STEP = False
TARGET_SCAN_POINTS = 7
STEP_MIN_NM = 1
STEP_MAX_NM = 1
SIMULATION_TIME_S = 5e-11
AUTO_SHUTOFF_MIN = 1e-07

CONFIG = dict(
    STRUCTURE_ROOT='H:\\FDTD outcome\\struct\\群论_struct\\C2对称结构\\双圆盘',
    LUMERICAL_ROOT='D:\\Program Files\\Lumerical\\v202',
    ASCII_WORK_ROOT='H:\\FDTD_CodeX\\fdtd_ascii_work',
    RUN_MODE_DEFAULT='ask',
    TEST_POINT_COUNT=3,
    SIMULATION_TIME_S=SIMULATION_TIME_S,
    AUTO_SHUTOFF_MIN=AUTO_SHUTOFF_MIN,
    T_MONITOR_NAME='T',
    STRUCTURE_CN_NAME='双圆盘',
    SAFE_NAME='dual_disks',
    OBJECT_NAME='Si_disk',
    GEOMETRY_OBJECTS=('Si_disk',),
    PERTURBATION_NAME='单盘开孔扰动',
    GROUP_PATH='C2 -> C1',
    OPERATION='insert_hole',
    OPERATION_DESCRIPTION='只在右侧 Si_disk 中心插入 etch 圆孔。',
    TARGET_INDICES=(2,),
    VALUE_NAME='hole_radius',
    SCAN_LABEL='single_disk_hole',
    USER_GUIDE=['孔半径从 0 开始；0 nm 时不插入孔，作为基线。'],
    SCAN_START_NM=R_START_NM,
    SCAN_STOP_NM=R_STOP_NM,
    SCAN_STEP_NM=R_STEP_NM,
    AUTO_SCAN_STEP=AUTO_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=STEP_MIN_NM,
    SCAN_STEP_MAX_NM=STEP_MAX_NM,
)

if __name__ == "__main__":
    run(CONFIG)
