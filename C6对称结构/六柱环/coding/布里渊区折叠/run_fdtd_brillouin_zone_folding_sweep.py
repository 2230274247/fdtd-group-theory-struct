# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from brillouin_zone_folding_common import run

# ========================= 用户主要修改区 =========================
# 论文里的 gap perturbation: 同一 2-cell 超胞内两个 resonator 的距离从 L 变为 L - deltaL。
# 单位 nm。网页总控会读取这三个顶层变量，因此不要移动到 CONFIG 后面。
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
BZF_STRATEGY = "center_distance"
PRIMITIVE_PERIOD_X_NM = 900.0
SUPERCELL_PERIOD_X_NM = 1800.0

# BZF 设置：x 方向周期翻倍，folding order=2；C3/C4/C6 这里只作为标记保留。
FOLDING_ORDER = 6
LUMERICAL_ROOT = r"D:\Program Files\Lumerical\v202"
FDTD_OBJECT_NAME = "FDTD"
MOTIF_OBJECT_NAMES = ('Si_pillar',)
SUBSTRATE_OBJECT_CANDIDATES = ('SiO2_substrate', 'substrate', 'Si_substrate', 'Au_substrate')
SUPER_CELL_SPAN_OBJECTS = ('SiO2_substrate', 'Au_substrate', 'substrate', 'source', 'T')
# ================================================================

CONFIG = dict(
    STRUCTURE_ROOT=str(Path(__file__).resolve().parents[2]),
    SYMMETRY_NAME="C6对称结构",
    STRUCTURE_CN_NAME="六柱环",
    PERTURBATION_NAME="布里渊区折叠",
    GROUP_PATH="C6对称结构 -> 2-cell BZF supercell -> gap perturbation deltaL",
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
    LUMERICAL_ROOT=LUMERICAL_ROOT,
    FDTD_OBJECT_NAME=FDTD_OBJECT_NAME,
    MOTIF_OBJECT_NAMES=MOTIF_OBJECT_NAMES,
    SUBSTRATE_OBJECT_CANDIDATES=SUBSTRATE_OBJECT_CANDIDATES,
    SUPER_CELL_SPAN_OBJECTS=SUPER_CELL_SPAN_OBJECTS,
)

if __name__ == "__main__":
    run(CONFIG)