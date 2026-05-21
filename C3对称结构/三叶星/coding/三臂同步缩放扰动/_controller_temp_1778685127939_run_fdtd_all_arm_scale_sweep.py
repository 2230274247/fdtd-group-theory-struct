# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c3_sweep_common import run

# ========================= 用户主要修改区 =========================
RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3
REFERENCE_LENGTH_NM = 440.0    # 母版单臂长度；同步缩放以该值作为 1 倍参考
START_NM = 10
END_NM = 520
STEP_NM = 50
LENGTH_START_NM = START_NM
LENGTH_STOP_NM = END_NM
LENGTH_STEP_NM = STEP_NM
AUTO_LENGTH_STEP = False
TARGET_SCAN_POINTS = 8
LENGTH_STEP_MIN_NM = 50
LENGTH_STEP_MAX_NM = 50
SIMULATION_TIME_S = 50e-12
AUTO_SHUTOFF_MIN = 1e-7

CONFIG = dict(
    STRUCTURE_ROOT=r"H:\FDTD outcome\struct\群论_struct\C3对称结构\三叶星",
    STRUCTURE_CN_NAME="三叶星",
    SAFE_NAME="three_lobed_star",
    LUMERICAL_ROOT=r"D:\Program Files\Lumerical\v202",
    ASCII_WORK_ROOT=r"H:\FDTD_CodeX\fdtd_ascii_work",
    PERTURBATION_NAME="三臂同步缩放扰动",
    GROUP_PATH="C3 -> C3",
    OBJECT_NAME="Si_lobe",
    OPERATION="scale_xy_span",
    OPERATION_DESCRIPTION="三个 Si_lobe 同步按比例缩放 x span 和 y span，保持三重旋转对称。",
    TARGET_INDICES=(1, 2, 3),
    VALUE_NAME="arm_scale_reference_length",
    SCAN_LABEL="all_arm_scale",
    SCAN_START_NM=LENGTH_START_NM,
    SCAN_STOP_NM=LENGTH_STOP_NM,
    SCAN_STEP_NM=LENGTH_STEP_NM,
    AUTO_SCAN_STEP=AUTO_LENGTH_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=LENGTH_STEP_MIN_NM,
    SCAN_STEP_MAX_NM=LENGTH_STEP_MAX_NM,
    BASE_REFERENCE_NM=REFERENCE_LENGTH_NM,
    TEST_POINT_COUNT=TEST_POINT_COUNT,
    RUN_MODE_DEFAULT=RUN_MODE_DEFAULT,
    SIMULATION_TIME_S=SIMULATION_TIME_S,
    AUTO_SHUTOFF_MIN=AUTO_SHUTOFF_MIN,
    T_MONITOR_NAME="T",
    GEOMETRY_OBJECTS=("Si_lobe",),
    USER_GUIDE=["- 该脚本把长度扫描值换算为缩放倍数，同时缩放宽和长，主要研究保持 C3 的整体尺度效应。"],
)

if __name__ == "__main__":
    run(CONFIG)

