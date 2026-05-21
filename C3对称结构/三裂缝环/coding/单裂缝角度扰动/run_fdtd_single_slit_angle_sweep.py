# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c3_sweep_common import run

# ========================= 用户主要修改区 =========================
RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3
TARGET_SLIT_INDEX = 1
START_DEG = -15.0  # 在母版角度基础上增加的角度；建议 -15 到 +15 deg
END_DEG = 15.0
STEP_DEG = 5.0
ANGLE_DELTA_START_DEG = START_DEG
ANGLE_DELTA_STOP_DEG = END_DEG
ANGLE_DELTA_STEP_DEG = STEP_DEG
AUTO_ANGLE_STEP = True
TARGET_SCAN_POINTS = 7
ANGLE_STEP_MIN_DEG = 2.0
ANGLE_STEP_MAX_DEG = 6.0
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
    PERTURBATION_NAME="单裂缝角度扰动",
    GROUP_PATH="C3 -> C1",
    OBJECT_NAME="air_slit",
    OPERATION="set_rotation_delta",
    OPERATION_DESCRIPTION="只改变一个 air_slit 的 rotation 1；扫描值是相对母版角度的增量。",
    TARGET_INDICES=(TARGET_SLIT_INDEX,),
    VALUE_NAME="slit_angle_delta",
    SCAN_LABEL="single_slit_angle",
    SCAN_UNIT="deg",
    SCAN_START_DEG=ANGLE_DELTA_START_DEG,
    SCAN_STOP_DEG=ANGLE_DELTA_STOP_DEG,
    SCAN_STEP_DEG=ANGLE_DELTA_STEP_DEG,
    AUTO_SCAN_STEP=AUTO_ANGLE_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_DEG=ANGLE_STEP_MIN_DEG,
    SCAN_STEP_MAX_DEG=ANGLE_STEP_MAX_DEG,
    TEST_POINT_COUNT=TEST_POINT_COUNT,
    RUN_MODE_DEFAULT=RUN_MODE_DEFAULT,
    SIMULATION_TIME_FS=SIMULATION_TIME_FS,
    SIMULATION_TIME_S=SIMULATION_TIME_S,
    AUTO_SHUTOFF_MIN=AUTO_SHUTOFF_MIN,
    MESH_ACCURACY=MESH_ACCURACY,
    DT_STABILITY_FACTOR=DT_STABILITY_FACTOR,
    T_MONITOR_NAME="T",
    GEOMETRY_OBJECTS=("Si_outer_ring", "air_inner_ring", "air_slit"),
    USER_GUIDE=[
        "- ANGLE_DELTA 是相对原始裂缝角度的增量，不是绝对角度。",
        "- 角度过大可能让裂缝与内孔/外边界的几何关系不再接近原设计，建议先预览。",
    ],
)

if __name__ == "__main__":
    run(CONFIG)

