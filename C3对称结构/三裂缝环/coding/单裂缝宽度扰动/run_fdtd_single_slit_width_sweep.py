# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from c3_sweep_common import run

# ========================= 用户主要修改区 =========================
RUN_MODE_DEFAULT = "ask"       # ask/test/full/preview
TEST_POINT_COUNT = 3
TARGET_SLIT_INDEX = 1          # 1=上方裂缝；2=左下裂缝；3=右下裂缝
START_NM = 20.0  # 建议范围：20-80 nm；太小可能网格要求更高
END_NM = 80.0
STEP_NM = 10.0
WIDTH_START_NM = START_NM
WIDTH_STOP_NM = END_NM
WIDTH_STEP_NM = STEP_NM
AUTO_WIDTH_STEP = True
TARGET_SCAN_POINTS = 7
WIDTH_STEP_MIN_NM = 5.0
WIDTH_STEP_MAX_NM = 15.0
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
    PERTURBATION_NAME="单裂缝宽度扰动",
    GROUP_PATH="C3 -> C1",
    OBJECT_NAME="air_slit",
    OPERATION="set_x_span",
    OPERATION_DESCRIPTION="只改变一个 air_slit 的 x span，其他裂缝保持母版尺寸。",
    TARGET_INDICES=(TARGET_SLIT_INDEX,),
    VALUE_NAME="slit_width",
    SCAN_LABEL="single_slit_width",
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
    GEOMETRY_OBJECTS=("Si_outer_ring", "air_inner_ring", "air_slit"),
    USER_GUIDE=[
        "- TARGET_SLIT_INDEX：选择要破坏 C3 对称性的那一道裂缝。",
        "- WIDTH_START/STOP：裂缝宽度扫描范围，单位 nm；输出说明中会换算成 um。",
        "- AUTO_WIDTH_STEP=True 时，脚本按 TARGET_SCAN_POINTS 自动重算步长，并限制在 WIDTH_STEP_MIN/MAX 之间。",
    ],
)

if __name__ == "__main__":
    run(CONFIG)

