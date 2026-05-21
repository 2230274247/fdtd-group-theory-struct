# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c3_sweep_common import run

# ========================= 用户主要修改区 =========================
RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3
TARGET_ARM_INDEX = 1
START_NM = 80.0  # 母版单臂宽度 120 nm；建议 80-170 nm
END_NM = 170.0
STEP_NM = 15.0
WIDTH_START_NM = START_NM
WIDTH_STOP_NM = END_NM
WIDTH_STEP_NM = STEP_NM
AUTO_WIDTH_STEP = True
TARGET_SCAN_POINTS = 7
WIDTH_STEP_MIN_NM = 5.0
WIDTH_STEP_MAX_NM = 20.0
SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

CONFIG = dict(
    STRUCTURE_ROOT=r"H:\FDTD outcome\struct\群论_struct\C3对称结构\三叶星",
    STRUCTURE_CN_NAME="三叶星",
    SAFE_NAME="three_lobed_star",
    LUMERICAL_ROOT=r"D:\Program Files\Lumerical\v202",
    ASCII_WORK_ROOT=r"H:\FDTD_CodeX\fdtd_ascii_work",
    PERTURBATION_NAME="单臂宽度差扰动",
    GROUP_PATH="C3 -> C1",
    OBJECT_NAME="Si_lobe",
    OPERATION="set_x_span",
    OPERATION_DESCRIPTION="只改变一个 Si_lobe 的 x span，形成单臂变宽/变窄扰动。",
    TARGET_INDICES=(TARGET_ARM_INDEX,),
    VALUE_NAME="arm_width",
    SCAN_LABEL="single_arm_width",
    SCAN_START_NM=WIDTH_START_NM,
    SCAN_STOP_NM=WIDTH_STOP_NM,
    SCAN_STEP_NM=WIDTH_STEP_NM,
    AUTO_SCAN_STEP=AUTO_WIDTH_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=WIDTH_STEP_MIN_NM,
    SCAN_STEP_MAX_NM=WIDTH_STEP_MAX_NM,
    TEST_POINT_COUNT=TEST_POINT_COUNT,
    RUN_MODE_DEFAULT=RUN_MODE_DEFAULT,
    SIMULATION_TIME_FS=SIMULATION_TIME_FS,
    SIMULATION_TIME_S=SIMULATION_TIME_S,
    AUTO_SHUTOFF_MIN=AUTO_SHUTOFF_MIN,
    MESH_ACCURACY=MESH_ACCURACY,
    DT_STABILITY_FACTOR=DT_STABILITY_FACTOR,
    T_MONITOR_NAME="T",
    GEOMETRY_OBJECTS=("Si_lobe",),
    USER_GUIDE=["- WIDTH_START/STOP 控制单臂宽度；太窄时局部网格敏感，太宽时相邻臂间距变小。"],
)

if __name__ == "__main__":
    run(CONFIG)

