# -*- coding: utf-8 -*-
"""
Si 方环扰动 5：外框长宽差 FDTD 自动化扫描脚本
==============================================

本脚本实现 visual guide 中的：
    方环 / 扰动 5：外框长宽差
    改变参数：外框长宽比 aspect_ratio = outer_x_span / outer_y_span
    建议范围：1.0 到 1.5
    建议步长：0.05
    delta 定义：delta = aspect_ratio - 1.0
    降群路径：C4 -> C2

几何定义：
    - 母结构外框对象：Si_outer_square
    - 内孔对象：air_inner_square
    - 本扰动保持外框面积不变，改变外框的长宽比。
    - 面积 = outer_x_span * outer_y_span = constant = base_span^2
    - outer_x_span = base_span * sqrt(aspect_ratio)
    - outer_y_span = base_span / sqrt(aspect_ratio)
    - aspect_ratio = 1.0 时为正方形外框，作为基线结构（C4 对称）。
    - 内孔保持正方形不变（x span = y span = 300 nm），中心不动。

运行流程：
    1. 从 SOURCE_FSP_DIR 中寻找唯一 .fsp 文件；
    2. 复制到本批次结果目录下的工作子目录，作为 master_template.fsp；
    3. 每个长宽比都从 master_template.fsp 再复制一个 work_*.fsp；
    4. 只在该 work_*.fsp 上改变 Si_outer_square 的 x span 和 y span；
    5. 仿真结束后立刻保存 .fsp、透射谱 |T|^2 图片、Excel 源数据和日志。
"""

import argparse
import csv
import importlib.util
import math
import os
import shutil
import sys
import time
import warnings
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, NamedTuple
from xml.sax.saxutils import escape

# Lumerical 自带 Python 在导入 numpy 时有时会报告"重复加载 OpenBLAS DLL"。
warnings.filterwarnings("ignore", category=UserWarning, module=r"numpy\._distributor_init")
import numpy as np


# =============================================================================
# 用户主要修改区
# =============================================================================

LUMERICAL_ROOT = Path(r"D:\Program Files\Lumerical\v202")
SOURCE_FSP_DIR = Path(r"H:\FDTD outcome\struct\群论_struct\C4对称结构\方环\fsp")

OUTER_FRAME_OBJECT_NAME = "Si_outer_square"
INNER_HOLE_OBJECT_NAME = "air_inner_square"
TRANSMISSION_MONITOR_NAME = "T"

# 当前 .fsp 中实际读取到的值约为：
#   外框 x span = 580 nm，y span = 580 nm
#   内孔 x span = 300 nm，y span = 300 nm
# 这里作为校验值；脚本实际以 .fsp 读取值为准。
EXPECTED_OUTER_X_SPAN_M = 580e-9
EXPECTED_OUTER_Y_SPAN_M = 580e-9
EXPECTED_INNER_X_SPAN_M = 300e-9
EXPECTED_INNER_Y_SPAN_M = 300e-9

# ===== 外框长宽差扫描参数 =====
# aspect_ratio = outer_x_span / outer_y_span
# 面积保持不变：outer_x_span * outer_y_span = base_span^2
# outer_x_span = base_span * sqrt(aspect_ratio)
# outer_y_span = base_span / sqrt(aspect_ratio)
START = 1.0
END = 1.5
STEP = 0.05
ASPECT_RATIO_START = START
ASPECT_RATIO_STOP = END
ASPECT_RATIO_STEP = STEP
INCLUDE_EXACT_STOP_POINT = True

# ===== 参数联动设置 =====
AUTO_CLIP_ASPECT_RATIO = True
MIN_EDGE_WIDTH_M = 20e-9
OUTER_FRAME_EDGE_CLEARANCE_M = 5e-9
AUTO_STEP = True
TARGET_POINTS = 15
AUTO_STEP_MIN = 0.01
AUTO_STEP_MAX = 0.10

# 运行模式：
#   "ask"     : 运行后输入 1/2/3 选择
#   "test"    : 真实仿真测试，只跑 TEST_POINT_COUNT 个点
#   "full"    : 完整真实仿真
#   "preview" : 只预览，不仿真
RUN_MODE = "ask"
TEST_POINT_COUNT = 3
SIMULATION_TIME_FS = 10000.0
SIMULATION_TIME_S = SIMULATION_TIME_FS * 1e-15
AUTO_SHUTOFF_MIN = 1e-12
MESH_ACCURACY = 2
DT_STABILITY_FACTOR = 0.8

RUN_FOLDER_PREFIX = "run_"
PERTURBATION_OUTPUT_DIR_NAME = "外框长宽差扰动"
WORK_FSP_DIR_NAME = "05_work_fsp"
SUPPRESS_NONCRITICAL_WARNINGS = True


def chinese_timestamp():
    """生成中文时间戳。"""
    now = datetime.now()
    return "{}年{}月{}日_{:02d}时{:02d}分{:02d}秒".format(
        now.year, now.month, now.day, now.hour, now.minute, now.second
    )


# =============================================================================
# 程序主体
# =============================================================================


class SweepPoint(NamedTuple):
    global_index: int
    aspect_ratio: float
    outer_x_span_m: float
    outer_y_span_m: float


class OutputPaths(NamedTuple):
    fsp_file: Path
    excel_file: Path
    png_file: Path


def nm(value_m):
    return value_m * 1e9


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def effective_aspect_ratio_limits(base_span_m, inner_span_m):
    """根据基线外框尺寸、内孔尺寸和安全边距，计算长宽比的安全范围。"""
    # 当 aspect_ratio > 1 时：
    #   outer_x = base * sqrt(ar)  => 增大
    #   outer_y = base / sqrt(ar)  => 减小
    # 需要 outer_y/2 - inner_span/2 >= MIN_EDGE_WIDTH_M
    #   => base / sqrt(ar) >= inner_span + 2 * MIN_EDGE_WIDTH_M
    #   => sqrt(ar) <= base / (inner_span + 2 * MIN_EDGE_WIDTH_M)
    #   => ar <= [base / (inner_span + 2 * MIN_EDGE_WIDTH_M)]^2

    min_outer_y = inner_span_m + 2.0 * MIN_EDGE_WIDTH_M
    if min_outer_y <= 0:
        raise ValueError("内孔尺寸或最小边宽设置不合理。")

    max_ar = (base_span_m / min_outer_y) ** 2
    max_ar = min(max_ar, 2.0)  # 硬上限

    return 1.0, max_ar


def effective_aspect_ratio_stop(base_span_m, inner_span_m):
    """获取实际的长宽比终点值。"""
    min_ar, max_ar = effective_aspect_ratio_limits(base_span_m, inner_span_m)

    actual_start = max(ASPECT_RATIO_START, min_ar)
    actual_stop = min(ASPECT_RATIO_STOP, max_ar)

    if AUTO_CLIP_ASPECT_RATIO:
        if actual_start > actual_stop:
            raise ValueError(
                "长宽比范围无效：start={:.4f} > stop={:.4f}。".format(actual_start, actual_stop)
            )
        return actual_start, actual_stop

    if ASPECT_RATIO_START < min_ar or ASPECT_RATIO_STOP > max_ar:
        raise ValueError(
            "ASPECT_RATIO 范围 [{:.4f}, {:.4f}] 超出安全范围 [{:.4f}, {:.4f}]。".format(
                ASPECT_RATIO_START, ASPECT_RATIO_STOP, min_ar, max_ar
            )
        )
    return ASPECT_RATIO_START, ASPECT_RATIO_STOP


def effective_aspect_ratio_step(actual_start, actual_stop):
    """获取实际的长宽比步长。"""
    if not AUTO_STEP:
        if ASPECT_RATIO_STEP <= 0:
            raise ValueError("ASPECT_RATIO_STEP 必须大于 0。")
        return ASPECT_RATIO_STEP

    total_range = actual_stop - actual_start
    by_points = total_range / float(max(1, TARGET_POINTS - 1))
    return clamp(by_points, AUTO_STEP_MIN, AUTO_STEP_MAX)


def maybe_ask_fdtd_runtime_overrides():
    global SIMULATION_TIME_FS, SIMULATION_TIME_S, AUTO_SHUTOFF_MIN, MESH_ACCURACY, DT_STABILITY_FACTOR
    print("")
    print("当前 FDTD 参数：simulation time = {} fs；auto shutoff min = {}；mesh accuracy = {}；dt stability factor = {}".format(
        SIMULATION_TIME_FS, AUTO_SHUTOFF_MIN, MESH_ACCURACY, DT_STABILITY_FACTOR
    ))
    if input("是否修改本次 FDTD 参数？y/N：").strip().lower() != "y":
        return
    prompts = (
        ("SIMULATION_TIME_FS", "simulation time (fs)"),
        ("AUTO_SHUTOFF_MIN", "auto shutoff min"),
        ("MESH_ACCURACY", "mesh accuracy"),
        ("DT_STABILITY_FACTOR", "dt stability factor"),
    )
    for key, label in prompts:
        current = globals().get(key)
        raw = input("{}，空白表示不改，当前 {}：".format(label, current)).strip()
        if not raw:
            continue
        value = float(raw)
        if value <= 0:
            print("{} 必须大于 0，已忽略。".format(label))
            continue
        globals()[key] = int(value) if key == "MESH_ACCURACY" else value
    SIMULATION_TIME_S = float(SIMULATION_TIME_FS) * 1e-15


def import_lumapi():
    api_dir = LUMERICAL_ROOT / "api" / "python"
    bin_dir = LUMERICAL_ROOT / "bin"

    for path in (api_dir, bin_dir):
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(path))
        os.environ["PATH"] = str(path) + os.pathsep + os.environ.get("PATH", "")

    lumapi_file = api_dir / "lumapi.py"
    if not lumapi_file.exists():
        raise FileNotFoundError("找不到 lumapi.py：{}".format(lumapi_file))

    spec = importlib.util.spec_from_file_location("lumapi", str(lumapi_file))
    if spec is None or spec.loader is None:
        raise RuntimeError("无法从该路径导入 lumapi：{}".format(lumapi_file))

    lumapi = importlib.util.module_from_spec(spec)
    sys.modules["lumapi"] = lumapi
    spec.loader.exec_module(lumapi)
    return lumapi


def find_source_fsp():
    fsp_files = sorted(p for p in SOURCE_FSP_DIR.glob("*.fsp") if p.suffix.lower() == ".fsp")
    if len(fsp_files) != 1:
        raise RuntimeError("期望在 {} 中找到 1 个 .fsp，实际找到 {} 个。".format(SOURCE_FSP_DIR, len(fsp_files)))
    return fsp_files[0]


def prepare_ascii_master_template(source_fsp, ascii_work_dir):
    ascii_work_dir.mkdir(parents=True, exist_ok=True)
    target = ascii_work_dir / "master_template.fsp"
    shutil.copy2(str(source_fsp), str(target))
    return target


def make_point_working_copy(master_template_fsp, point, ascii_work_dir):
    point_work_fsp = ascii_work_dir / "work_{}.fsp".format(point_stem(point))
    shutil.copy2(str(master_template_fsp), str(point_work_fsp))
    return point_work_fsp


def get_float_property(fdtd, object_name, property_name):
    return float(fdtd.getnamed(object_name, property_name))


def read_square_ring_geometry(fdtd):
    """从 .fsp 中读取方环几何参数。"""
    outer_x_span_m = get_float_property(fdtd, OUTER_FRAME_OBJECT_NAME, "x span")
    outer_y_span_m = get_float_property(fdtd, OUTER_FRAME_OBJECT_NAME, "y span")
    outer_z_min_m = get_float_property(fdtd, OUTER_FRAME_OBJECT_NAME, "z min")
    outer_z_max_m = get_float_property(fdtd, OUTER_FRAME_OBJECT_NAME, "z max")
    inner_x_span_m = get_float_property(fdtd, INNER_HOLE_OBJECT_NAME, "x span")
    inner_y_span_m = get_float_property(fdtd, INNER_HOLE_OBJECT_NAME, "y span")
    inner_z_min_m = get_float_property(fdtd, INNER_HOLE_OBJECT_NAME, "z min")
    inner_z_max_m = get_float_property(fdtd, INNER_HOLE_OBJECT_NAME, "z max")
    return (outer_x_span_m, outer_y_span_m, outer_z_min_m, outer_z_max_m,
            inner_x_span_m, inner_y_span_m, inner_z_min_m, inner_z_max_m)


def build_aspect_ratios(base_span_m, inner_span_m):
    """生成长宽比扫描值列表。"""
    actual_start, actual_stop = effective_aspect_ratio_stop(base_span_m, inner_span_m)
    step = effective_aspect_ratio_step(actual_start, actual_stop)

    if step <= 0:
        raise ValueError("实际步长必须大于 0。")

    values = []  # type: List[float]
    current = actual_start
    while current <= actual_stop + 1e-12:
        values.append(float(current))
        current += step

    if INCLUDE_EXACT_STOP_POINT and values and abs(values[-1] - actual_stop) > 1e-12:
        values.append(float(actual_stop))

    return values


def build_sweep_points(outer_x_span_m, outer_y_span_m, inner_x_span_m, inner_y_span_m):
    """构建扫描点列表。"""
    base_span_m = (outer_x_span_m + outer_y_span_m) / 2.0  # 基线外框边长
    inner_span_m = (inner_x_span_m + inner_y_span_m) / 2.0  # 基线内孔边长

    aspect_ratios = build_aspect_ratios(base_span_m, inner_span_m)
    points = []  # type: List[SweepPoint]
    for global_index, ar in enumerate(aspect_ratios):
        outer_x = base_span_m * math.sqrt(ar)
        outer_y = base_span_m / math.sqrt(ar)
        points.append(SweepPoint(global_index, float(ar), float(outer_x), float(outer_y)))
    return points


def point_stem(point):
    return "{:04d}_ar{:05.3f}_Ox{:07.2f}nm_Oy{:07.2f}nm".format(
        point.global_index,
        point.aspect_ratio,
        nm(point.outer_x_span_m),
        nm(point.outer_y_span_m),
    ).replace(".", "d")


def prepare_output_root(script_dir, resume, explicit_run_dir, run_mode="run"):
    ring_root = script_dir.parent.parent
    root = ring_root / "results" / PERTURBATION_OUTPUT_DIR_NAME
    root.mkdir(parents=True, exist_ok=True)

    if explicit_run_dir:
        run_dir = Path(explicit_run_dir)
        if not run_dir.is_absolute():
            run_dir = root / explicit_run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    if resume:
        candidates = sorted(p for p in root.glob(RUN_FOLDER_PREFIX + "*") if p.is_dir())
        if not candidates:
            raise RuntimeError("指定了 --resume，但 results/{} 中没有可继续的 run_* 批次。".format(PERTURBATION_OUTPUT_DIR_NAME))
        return candidates[-1]

    run_dir = root / (RUN_FOLDER_PREFIX + run_mode + "_" + chinese_timestamp())
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def prepare_output_folders(run_dir):
    folders = {
        "plan": run_dir / "00_scan_plan",
        "fsp": run_dir / "01_fsp_files",
        "excel": run_dir / "02_transmission_excel",
        "png": run_dir / "03_transmission_png_abs2",
        "logs": run_dir / "04_logs",
        "work": run_dir / WORK_FSP_DIR_NAME,
    }
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def paths_for_point(folders, point):
    stem = point_stem(point)
    return OutputPaths(
        folders["fsp"] / (stem + ".fsp"),
        folders["excel"] / (stem + "_transmission_abs2.xlsx"),
        folders["png"] / (stem + "_transmission_abs2.png"),
    )


def set_outer_frame_aspect_ratio(fdtd, point):
    """只改变外框 Si_outer_square 的 x span 和 y span；内孔保持不变。"""
    fdtd.switchtolayout()
    fdtd.select(OUTER_FRAME_OBJECT_NAME)
    fdtd.set("x span", point.outer_x_span_m)
    fdtd.set("y span", point.outer_y_span_m)


def squeeze_array(value):
    return np.asarray(value).squeeze()


def result_get(result, names):
    for name in names:
        if name in result:
            return result[name]
    return None


def read_transmission(fdtd):
    result = fdtd.getresult(TRANSMISSION_MONITOR_NAME, "T")
    wavelength = result_get(result, ["lambda", "wavelength"])
    frequency = result_get(result, ["f", "frequency"])
    transmission = result_get(result, ["T", "t"])

    if wavelength is None:
        try:
            wavelength = fdtd.getdata(TRANSMISSION_MONITOR_NAME, "lambda")
        except Exception:
            wavelength = None
    if frequency is None:
        try:
            frequency = fdtd.getdata(TRANSMISSION_MONITOR_NAME, "f")
        except Exception:
            frequency = None
    if transmission is None:
        try:
            transmission = fdtd.transmission(TRANSMISSION_MONITOR_NAME)
        except Exception:
            transmission = None

    if transmission is None:
        raise RuntimeError("无法从监视器 {} 读取透射谱 T。".format(TRANSMISSION_MONITOR_NAME))

    transmission = squeeze_array(transmission).astype(complex)
    if wavelength is None and frequency is None:
        x_axis = np.arange(transmission.size, dtype=float)
        wavelength = x_axis
        frequency = x_axis
    elif wavelength is None:
        frequency = squeeze_array(frequency).astype(float)
        wavelength = 299792458.0 / frequency
    elif frequency is None:
        wavelength = squeeze_array(wavelength).astype(float)
        frequency = 299792458.0 / wavelength
    else:
        wavelength = squeeze_array(wavelength).astype(float)
        frequency = squeeze_array(frequency).astype(float)

    wavelength = np.asarray(wavelength).reshape(-1)
    frequency = np.asarray(frequency).reshape(-1)
    transmission = np.asarray(transmission).reshape(-1)

    count = min(wavelength.size, frequency.size, transmission.size)
    return wavelength[:count], frequency[:count], transmission[:count]


def save_abs2_plot(png_path, point, wavelength_m, transmission):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    wavelength_nm = wavelength_m * 1e9
    t_abs2 = np.abs(transmission) ** 2

    fig, ax = plt.subplots(figsize=(8.6, 5.2), dpi=180)
    ax.plot(wavelength_nm, t_abs2, linewidth=1.8, color="#1f77b4")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("|T|^2")
    ax.set_title(
        "Outer aspect ratio: ar={:.3f}, Ox={:.2f} nm, Oy={:.2f} nm".format(
            point.aspect_ratio, nm(point.outer_x_span_m), nm(point.outer_y_span_m)
        )
    )
    ax.grid(True, alpha=0.28)
    fig.tight_layout()
    fig.savefig(str(png_path))
    plt.close(fig)


def xlsx_col_name(index):
    name = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def xlsx_cell(row_index, col_index, value):
    ref = "{}{}".format(xlsx_col_name(col_index), row_index + 1)
    if value is None:
        return '<c r="{}"/>'.format(ref)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return '<c r="{}"><v>{:.16g}</v></c>'.format(ref, float(value))
    return '<c r="{}" t="inlineStr"><is><t>{}</t></is></c>'.format(ref, escape(str(value)))


def xlsx_sheet_xml(rows):
    xml_rows = []
    for r, row in enumerate(rows):
        cells = [xlsx_cell(r, c, value) for c, value in enumerate(row)]
        xml_rows.append('<row r="{}">{}</row>'.format(r + 1, "".join(cells)))
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{}</sheetData></worksheet>'.format(
        "".join(xml_rows)
    )


def save_xlsx(xlsx_path, sheets):
    workbook_sheets = []
    relationships = []
    content_overrides = []

    for idx, sheet in enumerate(sheets, start=1):
        name = escape(sheet[0])
        workbook_sheets.append(
            '<sheet name="{}" sheetId="{}" r:id="rId{}"/>'.format(name, idx, idx)
        )
        relationships.append(
            '<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{}.xml"/>'.format(
                idx, idx
            )
        )
        content_overrides.append(
            '<Override PartName="/xl/worksheets/sheet{}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.format(
                idx
            )
        )

    workbook_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{}</sheets></workbook>'.format(
        "".join(workbook_sheets)
    )
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{}</Relationships>'.format(
        "".join(relationships)
    )
    root_rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    content_types_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>{}</Types>'.format(
        "".join(content_overrides)
    )

    with zipfile.ZipFile(str(xlsx_path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        for idx, sheet in enumerate(sheets, start=1):
            zf.writestr("xl/worksheets/sheet{}.xml".format(idx), xlsx_sheet_xml(sheet[1]))


def save_transmission_excel(xlsx_path, point, geometry, wavelength_m, frequency_hz, transmission):
    outer_x_span_m, outer_y_span_m, outer_z_min_m, outer_z_max_m, inner_x_span_m, inner_y_span_m, inner_z_min_m, inner_z_max_m = geometry
    t_abs2 = np.abs(transmission) ** 2
    data_rows = [["wavelength_m", "wavelength_nm", "frequency_Hz", "T_real", "T_imag", "T_abs2"]]
    for wl, fr, t, abs2 in zip(wavelength_m, frequency_hz, transmission, t_abs2):
        data_rows.append([float(wl), float(wl * 1e9), float(fr), float(np.real(t)), float(np.imag(t)), float(abs2)])

    base_span = (outer_x_span_m + outer_y_span_m) / 2.0
    edge_x = (point.outer_x_span_m - inner_x_span_m) / 2.0
    edge_y = (point.outer_y_span_m - inner_y_span_m) / 2.0
    metadata_rows = [
        ["item", "value"],
        ["perturbation", "outer_aspect_ratio"],
        ["method", "change_outer_frame_xy_span_area_preserved"],
        ["group_path", "C4 -> C2"],
        ["outer_frame_object", OUTER_FRAME_OBJECT_NAME],
        ["inner_hole_object", INNER_HOLE_OBJECT_NAME],
        ["transmission_monitor", TRANSMISSION_MONITOR_NAME],
        ["base_span_m", base_span],
        ["base_span_nm", nm(base_span)],
        ["aspect_ratio", point.aspect_ratio],
        ["delta", point.aspect_ratio - 1.0],
        ["outer_x_span_m", point.outer_x_span_m],
        ["outer_x_span_nm", nm(point.outer_x_span_m)],
        ["outer_y_span_m", point.outer_y_span_m],
        ["outer_y_span_nm", nm(point.outer_y_span_m)],
        ["inner_x_span_m", inner_x_span_m],
        ["inner_x_span_nm", nm(inner_x_span_m)],
        ["inner_y_span_m", inner_y_span_m],
        ["inner_y_span_nm", nm(inner_y_span_m)],
        ["edge_width_x_nm", nm(edge_x)],
        ["edge_width_y_nm", nm(edge_y)],
        ["area_preserved", "yes"],
        ["area_nm2", nm(point.outer_x_span_m) * nm(point.outer_y_span_m)],
    ]
    save_xlsx(xlsx_path, [("transmission_abs2", data_rows), ("metadata", metadata_rows)])


def write_scan_plan(plan_dir, points, geometry):
    outer_x_span_m, outer_y_span_m, outer_z_min_m, outer_z_max_m, inner_x_span_m, inner_y_span_m, inner_z_min_m, inner_z_max_m = geometry
    base_span = (outer_x_span_m + outer_y_span_m) / 2.0
    csv_path = plan_dir / "scan_points.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["global_index", "aspect_ratio", "delta=ar-1", "outer_x_span_nm", "outer_y_span_nm",
                         "edge_width_x_nm", "edge_width_y_nm"])
        for point in points:
            edge_x = (point.outer_x_span_m - inner_x_span_m) / 2.0
            edge_y = (point.outer_y_span_m - inner_y_span_m) / 2.0
            writer.writerow([
                point.global_index,
                "{:.6f}".format(point.aspect_ratio),
                "{:.6f}".format(point.aspect_ratio - 1.0),
                "{:.6f}".format(nm(point.outer_x_span_m)),
                "{:.6f}".format(nm(point.outer_y_span_m)),
                "{:.6f}".format(nm(edge_x)),
                "{:.6f}".format(nm(edge_y)),
            ])

    summary_path = plan_dir / "scan_summary.txt"
    with summary_path.open("w", encoding="utf-8-sig") as f:
        f.write("\n".join([
            "FDTD 方环外框长宽差自动扫描配置摘要",
            "==================================",
            "扰动名称: 外框长宽差",
            "实现方式: 保持外框面积不变，改变 Si_outer_square 的 x span 和 y span",
            "外框对象: {}".format(OUTER_FRAME_OBJECT_NAME),
            "内孔对象: {}".format(INNER_HOLE_OBJECT_NAME),
            "透射监视器: {}".format(TRANSMISSION_MONITOR_NAME),
            ".fsp 中外框 x span: {:.6f} nm".format(nm(outer_x_span_m)),
            ".fsp 中外框 y span: {:.6f} nm".format(nm(outer_y_span_m)),
            ".fsp 中内孔 x span: {:.6f} nm".format(nm(inner_x_span_m)),
            ".fsp 中内孔 y span: {:.6f} nm".format(nm(inner_y_span_m)),
            "基线外框边长 (base_span): {:.6f} nm".format(nm(base_span)),
            "长宽比起点: {:.6f}".format(ASPECT_RATIO_START),
            "长宽比终点: {:.6f}".format(ASPECT_RATIO_STOP),
            "实际步长: {:.6f}".format(effective_aspect_ratio_step(*effective_aspect_ratio_stop(base_span, (inner_x_span_m + inner_y_span_m) / 2.0))),
            "自动联动: {}".format(AUTO_CLIP_ASPECT_RATIO),
            "计划点数: {}".format(len(points)),
            "结果目录: results/{}".format(PERTURBATION_OUTPUT_DIR_NAME),
        ]))
    return csv_path


def write_structure_overview(run_dir, source_fsp, points, geometry):
    outer_x_span_m, outer_y_span_m, outer_z_min_m, outer_z_max_m, inner_x_span_m, inner_y_span_m, inner_z_min_m, inner_z_max_m = geometry
    base_span = (outer_x_span_m + outer_y_span_m) / 2.0
    inner_span = (inner_x_span_m + inner_y_span_m) / 2.0
    doc_path = run_dir / "结构状态说明.md"
    max_point = points[-1] if points else None
    lines = [
        "# 方环外框长宽差扰动结构状态说明",
        "",
        "## 母结构",
        "- 母版 FSP：`{}`".format(source_fsp),
        "- 结构类型：C4对称结构 / 方环",
        "- 外框对象：`{}`".format(OUTER_FRAME_OBJECT_NAME),
        "- 内孔对象：`{}`".format(INNER_HOLE_OBJECT_NAME),
        "- 透射监视器：`{}`".format(TRANSMISSION_MONITOR_NAME),
        "- 衬底：SiO2，尺寸和厚度保持母版 FSP 中的原始设置，本脚本不修改衬底。",
        "",
        "## 从 .fsp 读取到的固定几何",
        "- 外框 x span：{:.6f} nm".format(nm(outer_x_span_m)),
        "- 外框 y span：{:.6f} nm".format(nm(outer_y_span_m)),
        "- 基线外框边长：{:.6f} nm".format(nm(base_span)),
        "- 内孔 x span：{:.6f} nm".format(nm(inner_x_span_m)),
        "- 内孔 y span：{:.6f} nm".format(nm(inner_y_span_m)),
        "- 外框厚度：{:.6f} nm".format(nm(outer_z_max_m - outer_z_min_m)),
        "- 基线 x 方向边宽：{:.6f} nm".format(nm((outer_x_span_m - inner_x_span_m) / 2.0)),
        "- 基线 y 方向边宽：{:.6f} nm".format(nm((outer_y_span_m - inner_y_span_m) / 2.0)),
        "- 固定不变量：内孔尺寸、内孔位置、外框面积、厚度、材料、FDTD 区域、光源、监视器均不在本脚本中改变。",
        "",
        "## 本批次扰动",
        "- 扰动名称：外框长宽差",
        "- 实现方式：保持外框面积不变，改变 `Si_outer_square` 的 x span 和 y span。",
        "- 变量定义：`aspect_ratio = outer_x_span / outer_y_span`，`delta = aspect_ratio - 1.0`。",
        "- 面积守恒：`outer_x_span * outer_y_span = base_span^2 = {:.6f} nm^2`".format(nm(base_span) ** 2),
        "- 扫描范围：{:.4f} 到 {:.4f}".format(
            effective_aspect_ratio_stop(base_span, inner_span)[0],
            effective_aspect_ratio_stop(base_span, inner_span)[1]
        ),
        "- 实际扫描步长：{:.6f}".format(effective_aspect_ratio_step(*effective_aspect_ratio_stop(base_span, inner_span))),
        "- 降群路径：C4 -> C2",
        "- 计划仿真点数：{}".format(len(points)),
    ]
    if max_point is not None:
        lines.extend([
            "- 最大扰动点：ar={:.4f}, outer_x={:.2f} nm, outer_y={:.2f} nm".format(
                max_point.aspect_ratio, nm(max_point.outer_x_span_m), nm(max_point.outer_y_span_m)
            ),
            "- 最大扰动下 x 方向边宽：{:.6f} nm".format(nm((max_point.outer_x_span_m - inner_x_span_m) / 2.0)),
            "- 最大扰动下 y 方向边宽：{:.6f} nm".format(nm((max_point.outer_y_span_m - inner_y_span_m) / 2.0)),
        ])
    lines.extend([
        "",
        "## 输出文件",
        "- `00_scan_plan/scan_points.csv`：本批次扫描点列表。",
        "- `01_fsp_files/`：每一个扫描点保存后的 `.fsp` 文件。",
        "- `02_transmission_excel/`：每一个扫描点的透射谱源数据 Excel。",
        "- `03_transmission_png_abs2/`：每一个扫描点的透射谱 `|T|^2` 图片。",
        "- `04_logs/manifest.csv`：每一个扫描点的运行状态、输出路径和耗时。",
    ])
    with doc_path.open("w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))
    return doc_path


def write_manifest_header(manifest_path):
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["global_index", "aspect_ratio", "outer_x_span_nm", "outer_y_span_nm",
                         "fsp_file", "excel_file", "png_file", "elapsed_s", "status"])


def append_manifest(manifest_path, point, paths, elapsed_s, status):
    with manifest_path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            point.global_index,
            "{:.6f}".format(point.aspect_ratio),
            "{:.6f}".format(nm(point.outer_x_span_m)),
            "{:.6f}".format(nm(point.outer_y_span_m)),
            str(paths.fsp_file),
            str(paths.excel_file),
            str(paths.png_file),
            "{:.3f}".format(elapsed_s),
            status,
        ])


class TeeLogger(object):
    def __init__(self, log_path):
        self.terminal = sys.stdout
        self.log = log_path.open("a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()


def apply_fdtd_runtime_settings(fdtd):
    try:
        fdtd.set("simulation time", SIMULATION_TIME_S)
        fdtd.set("auto shutoff min", AUTO_SHUTOFF_MIN)
        fdtd.set("mesh accuracy", int(MESH_ACCURACY))
        fdtd.set("dt stability factor", DT_STABILITY_FACTOR)
    except Exception as exc:
        print("Warning: failed to set FDTD runtime settings: {}".format(exc))


def parse_args():
    parser = argparse.ArgumentParser(description="Si 方环扰动 5：外框长宽差 FDTD 自动化扫描")
    parser.add_argument("--preview", action="store_true", help="只生成扫描计划和结构说明，不运行仿真。")
    parser.add_argument("--test-run", action="store_true", help="测试模式：真实仿真前 TEST_POINT_COUNT 个点。")
    parser.add_argument("--full-run", action="store_true", help="完整真实仿真全部扫描点。")
    parser.add_argument("--resume", action="store_true", help="继续最近一个 run_* 批次。")
    parser.add_argument("--run-dir", default=None, help="指定输出批次目录。")
    parser.add_argument("--show-gui", action="store_true", help="显示 FDTD 图形界面。默认隐藏界面。")
    parser.add_argument("--max-points", type=int, default=None, help="最多处理多少个扫描点。")
    return parser.parse_args()


def apply_run_mode(args):
    args.prompted_mode = False
    if args.preview:
        return "preview"
    if args.test_run:
        return "test"
    if args.full_run:
        return "full"

    mode = RUN_MODE.lower().strip()
    if mode == "ask":
        args.prompted_mode = True
        print("请选择方环外框长宽差脚本运行模式：")
        print("  1 = 测试模式：真实仿真前 {} 个点".format(TEST_POINT_COUNT))
        print("  2 = 完整真实仿真")
        print("  3 = 预览模式：只生成扫描计划，不仿真")
        choice = input("请输入 1/2/3 后按回车：").strip()
        if choice == "1":
            return "test"
        if choice == "2":
            return "full"
        if choice == "3":
            return "preview"
        raise RuntimeError("输入无效：{}。请重新运行并输入 1、2 或 3。".format(choice))

    if mode not in ("test", "full", "preview"):
        raise RuntimeError('RUN_MODE 只能是 "ask"、"test"、"full" 或 "preview"。')
    return mode


def point_outputs_exist(paths):
    return paths.fsp_file.exists() and paths.excel_file.exists() and paths.png_file.exists()


def format_duration(seconds):
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return "{:.1f} s".format(seconds)
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    if minutes < 60:
        return "{} min {} s".format(minutes, sec)
    hours = minutes // 60
    minutes = minutes % 60
    return "{} h {} min {} s".format(hours, minutes, sec)


def describe_point(point):
    parts = []
    for attr, label in (
        ("aspect_ratio", "ar"),
        ("outer_x_span_m", "Ox"),
        ("outer_y_span_m", "Oy"),
    ):
        if hasattr(point, attr):
            if label == "ar":
                parts.append("{}={:.4f}".format(label, getattr(point, attr)))
            else:
                parts.append("{}={:.3f} nm".format(label, nm(getattr(point, attr))))
    return ", ".join(parts) if parts else str(point)


def print_runtime_progress(done_count, total_count, elapsed_s, run_started_at):
    remaining_count = max(0, total_count - done_count)
    avg_s = (time.time() - run_started_at) / float(max(1, done_count))
    remain_s = avg_s * remaining_count
    print(
        "    单次仿真时间: {}；已完成: {}/{}；还剩: {} 组；预计还需要: {}".format(
            format_duration(elapsed_s),
            done_count,
            total_count,
            remaining_count,
            format_duration(remain_s),
        )
    )


def main():
    args = parse_args()
    mode = apply_run_mode(args)
    if mode in ("test", "full") and getattr(args, "prompted_mode", False):
        maybe_ask_fdtd_runtime_overrides()
    args.run_mode_label = mode

    if SUPPRESS_NONCRITICAL_WARNINGS:
        warnings.filterwarnings("ignore", message=".*deprecated.*")

    script_dir = Path(__file__).resolve().parent
    run_dir = prepare_output_root(script_dir, resume=args.resume, explicit_run_dir=args.run_dir, run_mode=getattr(args, "run_mode_label", "run"))
    folders = prepare_output_folders(run_dir)
    log_path = folders["logs"] / "automation_run.log"
    manifest_path = folders["logs"] / "manifest.csv"

    logger = TeeLogger(log_path)
    old_stdout = sys.stdout
    sys.stdout = logger

    try:
        source_fsp = find_source_fsp()
        master_template_fsp = prepare_ascii_master_template(source_fsp, folders["work"])

        print("源 FSP: {}".format(source_fsp))
        print("工作母版 FSP: {}".format(master_template_fsp))
        print("输出批次目录: {}".format(run_dir))

        lumapi = import_lumapi()
        with lumapi.FDTD(hide=not args.show_gui) as fdtd:
            fdtd.load(str(master_template_fsp))
            geometry = read_square_ring_geometry(fdtd)

        outer_x_span_m, outer_y_span_m, outer_z_min_m, outer_z_max_m, inner_x_span_m, inner_y_span_m, inner_z_min_m, inner_z_max_m = geometry

        points = build_sweep_points(outer_x_span_m, outer_y_span_m, inner_x_span_m, inner_y_span_m)
        if args.max_points is not None:
            points = points[: max(0, args.max_points)]
        if mode == "test":
            points = points[:TEST_POINT_COUNT]

        plan_csv = write_scan_plan(folders["plan"], points, geometry)
        overview_doc = write_structure_overview(run_dir, source_fsp, points, geometry)

        base_span = (outer_x_span_m + outer_y_span_m) / 2.0
        print("外框 x span: {:.3f} nm".format(nm(outer_x_span_m)))
        print("外框 y span: {:.3f} nm".format(nm(outer_y_span_m)))
        print("基线外框边长: {:.3f} nm".format(nm(base_span)))
        print("内孔 span: {:.3f} nm".format(nm(inner_x_span_m)))
        print("长宽比范围: {:.4f} 到 {:.4f}，实际步长 {:.4f}".format(
            effective_aspect_ratio_stop(base_span, (inner_x_span_m + inner_y_span_m) / 2.0)[0],
            effective_aspect_ratio_stop(base_span, (inner_x_span_m + inner_y_span_m) / 2.0)[1],
            effective_aspect_ratio_step(*effective_aspect_ratio_stop(base_span, (inner_x_span_m + inner_y_span_m) / 2.0)),
        ))
        print("计划仿真点数: {}".format(len(points)))
        print("扫描计划已保存: {}".format(plan_csv))

        if mode == "preview":
            print("当前为预览模式，不会运行 FDTD 仿真。扫描点如下：")
            for point in points:
                edge_x = (point.outer_x_span_m - inner_x_span_m) / 2.0
                edge_y = (point.outer_y_span_m - inner_y_span_m) / 2.0
                print("  #{:04d}: ar={:.4f}, Ox={:.2f} nm, Oy={:.2f} nm, edge_x={:.2f} nm, edge_y={:.2f} nm".format(
                    point.global_index,
                    point.aspect_ratio,
                    nm(point.outer_x_span_m),
                    nm(point.outer_y_span_m),
                    nm(edge_x),
                    nm(edge_y),
                ))
            return

        if not args.resume or not manifest_path.exists():
            write_manifest_header(manifest_path)

        run_started_at = time.time()

        for index, point in enumerate(points, start=1):
            paths = paths_for_point(folders, point)
            if args.resume and point_outputs_exist(paths):
                print("[{}/{}] 已存在，跳过：{}".format(index, len(points), point_stem(point)))
                continue

            print("[{}/{}] 开始仿真：{}".format(index, len(points), point_stem(point)))
            print("    当前参数: {}；剩余组数(含当前): {}/{}".format(describe_point(point), len(points) - index + 1, len(points)))
            start = time.time()
            work_fsp = make_point_working_copy(master_template_fsp, point, folders["work"])
            try:
                with lumapi.FDTD(hide=not args.show_gui) as fdtd:
                    fdtd.load(str(work_fsp))
                    fdtd.switchtolayout()
                    apply_fdtd_runtime_settings(fdtd)
                    set_outer_frame_aspect_ratio(fdtd, point)
                    fdtd.save(str(work_fsp))
                    fdtd.run()
                    wavelength_m, frequency_hz, transmission = read_transmission(fdtd)
                    fdtd.save(str(work_fsp))

                shutil.copy2(str(work_fsp), str(paths.fsp_file))
                save_transmission_excel(paths.excel_file, point, geometry, wavelength_m, frequency_hz, transmission)
                save_abs2_plot(paths.png_file, point, wavelength_m, transmission)
                elapsed_s = time.time() - start
                append_manifest(manifest_path, point, paths, elapsed_s, "ok")
                print("    完成并保存，用时 {:.1f} s".format(elapsed_s))
                print_runtime_progress(index, len(points), elapsed_s, run_started_at)
            except Exception as exc:
                elapsed_s = time.time() - start
                append_manifest(manifest_path, point, paths, elapsed_s, "failed: {}".format(exc))
                print("    失败，用时 {:.1f} s：{}".format(elapsed_s, exc))
                raise

        print("全部完成。结果目录: {}".format(run_dir))
    finally:
        sys.stdout = old_stdout
        logger.close()


if __name__ == "__main__":
    main()
