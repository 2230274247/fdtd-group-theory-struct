# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c3_sweep_common import run

# ========================= 用户主要修改区 =========================
RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3
TARGET_PILLAR_INDEX = 1
START_NM = 0.0  # 沿该柱中心到原点连线的径向外移距离
END_NM = 90.0  # 建议 0-90 nm；过大可能接近周期边界
STEP_NM = 15.0
OFFSET_START_NM = START_NM
OFFSET_STOP_NM = END_NM
OFFSET_STEP_NM = STEP_NM
AUTO_OFFSET_STEP = True
TARGET_SCAN_POINTS = 7
OFFSET_STEP_MIN_NM = 5.0
OFFSET_STEP_MAX_NM = 20.0
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
    PERTURBATION_NAME="单点偏移扰动",
    GROUP_PATH="C3 -> C1",
    OBJECT_NAME="Si_pillar",
    OPERATION="offset_single",
    OPERATION_DESCRIPTION="只移动一个 Si_pillar，移动方向为该柱从中心向外的径向方向。",
    TARGET_INDICES=(TARGET_PILLAR_INDEX,),
    VALUE_NAME="pillar_offset",
    SCAN_LABEL="single_pillar_offset",
    SCAN_START_NM=OFFSET_START_NM,
    SCAN_STOP_NM=OFFSET_STOP_NM,
    SCAN_STEP_NM=OFFSET_STEP_NM,
    AUTO_SCAN_STEP=AUTO_OFFSET_STEP,
    TARGET_SCAN_POINTS=TARGET_SCAN_POINTS,
    SCAN_STEP_MIN_NM=OFFSET_STEP_MIN_NM,
    SCAN_STEP_MAX_NM=OFFSET_STEP_MAX_NM,
    TEST_POINT_COUNT=TEST_POINT_COUNT,
    RUN_MODE_DEFAULT=RUN_MODE_DEFAULT,
    SIMULATION_TIME_FS=SIMULATION_TIME_FS,
    SIMULATION_TIME_S=SIMULATION_TIME_S,
    AUTO_SHUTOFF_MIN=AUTO_SHUTOFF_MIN,
    MESH_ACCURACY=MESH_ACCURACY,
    DT_STABILITY_FACTOR=DT_STABILITY_FACTOR,
    T_MONITOR_NAME="T",
    GEOMETRY_OBJECTS=("Si_pillar",),
    USER_GUIDE=["- OFFSET 是额外外移量，不是最终坐标；母版中心半径约 0.21 um。"],
)

if __name__ == "__main__":
    run(CONFIG)

