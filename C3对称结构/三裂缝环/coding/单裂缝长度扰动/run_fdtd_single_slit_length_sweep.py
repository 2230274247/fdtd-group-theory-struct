# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c3_sweep_common import run

# ========================= 用户主要修改区 =========================
RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3
TARGET_SLIT_INDEX = 1
START_NM = 100.0  # 母版长度 170 nm；建议范围 100-230 nm
END_NM = 230.0
STEP_NM = 20.0
LENGTH_START_NM = START_NM
LENGTH_STOP_NM = END_NM
LENGTH_STEP_NM = STEP_NM
AUTO_LENGTH_STEP = True
TARGET_SCAN_POINTS = 8
LENGTH_STEP_MIN_NM = 10.0
LENGTH_STEP_MAX_NM = 25.0
SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

CONFIG = dict(
    STRUCTURE_ROOT=r"H:\FDTD outcome\struct\群论_struct\C3对称结构\三裂缝环",
    STRUCTURE_CN_NAME="三裂缝环",
    SAFE_NAME="three_slit_ring",
    LUMERICAL_ROOT=r"D:\Program Files\Lumerical\v202",
    ASCII_WORK_ROOT=r"H:\FDTD_CodeX\fdtd_ascii_work",
    PERTURBATION_NAME="单裂缝长度扰动",
    GROUP_PATH="C3 -> C1",
    OBJECT_NAME="air_slit",
    OPERATION="set_y_span",
    OPERATION_DESCRIPTION="只改变一个 air_slit 的 y span，等效扫描单道裂缝长度。",
    TARGET_INDICES=(TARGET_SLIT_INDEX,),
    VALUE_NAME="slit_length",
    SCAN_LABEL="single_slit_length",
    SCAN_START_NM=LENGTH_START_NM,
    SCAN_STOP_NM=LENGTH_STOP_NM,
    SCAN_STEP_NM=LENGTH_STEP_NM,
    AUTO_SCAN_STEP=AUTO_LENGTH_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=LENGTH_STEP_MIN_NM,
    SCAN_STEP_MAX_NM=LENGTH_STEP_MAX_NM,
    TEST_POINT_COUNT=TEST_POINT_COUNT,
    RUN_MODE_DEFAULT=RUN_MODE_DEFAULT,
    SIMULATION_TIME_FS=SIMULATION_TIME_FS,
    SIMULATION_TIME_S=SIMULATION_TIME_S,
    AUTO_SHUTOFF_MIN=AUTO_SHUTOFF_MIN,
    MESH_ACCURACY=MESH_ACCURACY,
    DT_STABILITY_FACTOR=DT_STABILITY_FACTOR,
    T_MONITOR_NAME="T",
    GEOMETRY_OBJECTS=("Si_outer_ring", "air_inner_ring", "air_slit"),
    USER_GUIDE=["- LENGTH_START/STOP 控制裂缝长度；过长时建议检查是否越过外环边界。"],
)

if __name__ == "__main__":
    run(CONFIG)

