# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from brillouin_zone_folding_common import run

# ========================= 用户主要修改区 =========================
# BZF 二聚化扰动 eta_nm。
# eta=0：simple-copy supercell / mathematical folding baseline。
# eta!=0：左右 primitive cell 不再等价，900 nm primitive period 被破坏，1800 nm 成为真实周期。
# 网页总控会读取 START_NM / END_NM / STEP_NM，因此保留这些变量名；内部统一记录为 eta_nm。
START_NM = 0.0
END_NM = 60.0
STEP_NM = 5.0

RUN_MODE_DEFAULT = "ask"
TEST_POINT_COUNT = 3
SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8
SCAN_PARAMETER_NAME = "eta_nm"
BZF_STRATEGY = "copy_then_eta_break"
PRIMITIVE_PERIOD_X_NM = 900.0
SUPERCELL_PERIOD_X_NM = 1800.0
L_NM = 450.0
BASE_DELTA_NM = 180.0
DISK_RADIUS_NM = 145.0
DISK_HEIGHT_NM = 420.0
BZF_OBJECT_NAMES = ('Si_disk_1', 'Si_disk_2', 'Si_disk_3', 'Si_disk_4')

# BZF 设置：x 方向周期翻倍，folding order=2；C3/C4/C6 这里只作为标记保留。
FOLDING_ORDER = 2
LUMERICAL_ROOT = r"D:\Program Files\Lumerical\v202"
FDTD_OBJECT_NAME = "FDTD"
MOTIF_OBJECT_NAMES = ('Si_disk',)
SUBSTRATE_OBJECT_CANDIDATES = ('SiO2_substrate', 'substrate', 'Si_substrate', 'Au_substrate')
SUPER_CELL_SPAN_OBJECTS = ('SiO2_substrate', 'Au_substrate', 'substrate', 'source', 'T')
# ================================================================

CONFIG = dict(
    STRUCTURE_ROOT=str(Path(__file__).resolve().parents[2]),
    SYMMETRY_NAME="C2对称结构",
    STRUCTURE_CN_NAME="双圆盘",
    PERTURBATION_NAME="布里渊区折叠",
    GROUP_PATH="C2对称结构 -> 2-cell BZF supercell -> eta_nm dimerization perturbation",
    START_NM=START_NM,
    END_NM=END_NM,
    STEP_NM=STEP_NM,
    RUN_MODE_DEFAULT=RUN_MODE_DEFAULT,
    TEST_POINT_COUNT=TEST_POINT_COUNT,
    SIMULATION_TIME_FS=SIMULATION_TIME_FS,
    SIMULATION_TIME_S=SIMULATION_TIME_S,
    AUTO_SHUTOFF_MIN=AUTO_SHUTOFF_MIN,
    MESH_ACCURACY=MESH_ACCURACY,
    DT_STABILITY_FACTOR=DT_STABILITY_FACTOR,
    FOLDING_ORDER=FOLDING_ORDER,
    SCAN_PARAMETER_NAME=SCAN_PARAMETER_NAME,
    BZF_STRATEGY=BZF_STRATEGY,
    PRIMITIVE_PERIOD_X_NM=PRIMITIVE_PERIOD_X_NM,
    SUPERCELL_PERIOD_X_NM=SUPERCELL_PERIOD_X_NM,
    L_NM=L_NM,
    BASE_DELTA_NM=BASE_DELTA_NM,
    DISK_RADIUS_NM=DISK_RADIUS_NM,
    DISK_HEIGHT_NM=DISK_HEIGHT_NM,
    BZF_OBJECT_NAMES=BZF_OBJECT_NAMES,
    LUMERICAL_ROOT=LUMERICAL_ROOT,
    FDTD_OBJECT_NAME=FDTD_OBJECT_NAME,
    MOTIF_OBJECT_NAMES=MOTIF_OBJECT_NAMES,
    SUBSTRATE_OBJECT_CANDIDATES=SUBSTRATE_OBJECT_CANDIDATES,
    SUPER_CELL_SPAN_OBJECTS=SUPER_CELL_SPAN_OBJECTS,
)

if __name__ == "__main__":
    run(CONFIG)
