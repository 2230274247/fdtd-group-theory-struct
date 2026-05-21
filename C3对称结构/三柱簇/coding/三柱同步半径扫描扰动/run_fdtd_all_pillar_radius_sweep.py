# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c3_sweep_common import run

# ========================= 用户主要修改区 =========================
RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3
START_NM = 60.0
END_NM = 130.0
STEP_NM = 10.0
RADIUS_START_NM = START_NM
RADIUS_STOP_NM = END_NM
RADIUS_STEP_NM = STEP_NM
AUTO_RADIUS_STEP = True
TARGET_SCAN_POINTS = 8
RADIUS_STEP_MIN_NM = 5.0
RADIUS_STEP_MAX_NM = 15.0
SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

CONFIG = dict(
    STRUCTURE_ROOT=r"H:\FDTD outcome\struct\群论_struct\C3对称结构\三柱簇",
    STRUCTURE_CN_NAME="三柱簇",
    SAFE_NAME="three_pillar_cluster",
    LUMERICAL_ROOT=r"D:\Program Files\Lumerical\v202",
    ASCII_WORK_ROOT=r"H:\FDTD_CodeX\fdtd_ascii_work",
    PERTURBATION_NAME="三柱同步半径扫描扰动",
    GROUP_PATH="C3 -> C3",
    OBJECT_NAME="Si_pillar",
    OPERATION="set_radius",
    OPERATION_DESCRIPTION="三个 Si_pillar 同步改变半径，保持 C3 对称。",
    TARGET_INDICES=(1, 2, 3),
    VALUE_NAME="all_pillar_radius",
    SCAN_LABEL="all_pillar_radius",
    SCAN_START_NM=RADIUS_START_NM,
    SCAN_STOP_NM=RADIUS_STOP_NM,
    SCAN_STEP_NM=RADIUS_STEP_NM,
    AUTO_SCAN_STEP=AUTO_RADIUS_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=RADIUS_STEP_MIN_NM,
    SCAN_STEP_MAX_NM=RADIUS_STEP_MAX_NM,
    TEST_POINT_COUNT=TEST_POINT_COUNT,
    RUN_MODE_DEFAULT=RUN_MODE_DEFAULT,
    SIMULATION_TIME_FS=SIMULATION_TIME_FS,
    SIMULATION_TIME_S=SIMULATION_TIME_S,
    AUTO_SHUTOFF_MIN=AUTO_SHUTOFF_MIN,
    MESH_ACCURACY=MESH_ACCURACY,
    DT_STABILITY_FACTOR=DT_STABILITY_FACTOR,
    T_MONITOR_NAME="T",
    GEOMETRY_OBJECTS=("Si_pillar",),
    USER_GUIDE=["- 同步半径扫描用于研究保持 C3 对称时的整体尺寸效应。"],
)

if __name__ == "__main__":
    run(CONFIG)

