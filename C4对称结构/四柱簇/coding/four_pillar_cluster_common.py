# -*- coding: utf-8 -*-
"""
鍥涙煴绨?FDTD 鑷姩鍖栨壂鎻忓叕鍏辨ā鍧?================================

杩欎釜妯″潡琚洓涓壈鍔ㄥ叆鍙ｈ剼鏈叡鐢ㄣ€傝璁＄洰鏍囷細
1. 缁濅笉淇敼 fsp 鏂囦欢澶瑰唴鐨勬簮 .fsp锛?2. 姣忔杩愯鍏堟妸婧?.fsp 澶嶅埗鍒?results/鎵板姩鍚?run_妯″紡_鏃堕棿鎴?05_work_fsp/master_template.fsp锛?3. 姣忎釜鎵弿鐐瑰啀浠庢瘝鐗堝鍒跺嚭鐙珛宸ヤ綔鍓湰锛屽彧淇敼璇ュ壇鏈紱
4. 姣忎釜鐪熷疄浠跨湡鐐圭粨鏉熷悗绔嬪埢淇濆瓨鏈偣 .fsp銆侀€忓皠璋?abs^2 鍥剧墖銆丒xcel 婧愭暟鎹紱
5. 杩愯鏃跺疄鏃惰緭鍑哄綋鍓嶅弬鏁般€佸崟鐐硅€楁椂銆佸墿浣欑粍鏁般€侀璁″墿浣欐椂闂村拰鏈偣璋卞嘲淇℃伅銆?
鍏ュ彛鑴氭湰鍙渶瑕佹彁渚?CONFIG 瀛楀吀锛涚湡姝ｇ殑鏂囦欢缁勭粐銆佹壂鎻忚鍒掋€丗DTD 璋冪敤鍜岀粨鏋滀繚瀛橀兘鍦ㄨ繖閲屽畬鎴愩€?"""

import argparse
import csv
import hashlib
import importlib.util
import math
import os
import shutil
import sys
import time
import warnings
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

warnings.filterwarnings("ignore", category=UserWarning, module=r"numpy\._distributor_init")
warnings.filterwarnings("ignore", message=r".*loaded more than 1 DLL.*")
warnings.filterwarnings("ignore", message=r".*deprecated.*")

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fdtd_autotune_common import (
    normalize_autotune_config,
    clone_runtime_config,
    extract_solver_info,
    evaluate_spectrum_quality,
    next_retry_config,
    runtime_profile_text,
    append_retry_history,
)
from c4_runtime_common import chinese_timestamp, format_duration, nm

PILLAR_LABELS = {
    1: "right_0deg",
    2: "top_90deg",
    3: "left_180deg",
    4: "bottom_270deg",
}


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def safe_token(text):
    chars = []
    for ch in str(text):
        if ch.isalnum() or ch in ("_", "-", "."):
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars).strip("_") or "point"


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_source_unchanged(source_fsp, expected_hash):
    now_hash = file_sha256(source_fsp)
    if now_hash != expected_hash:
        raise RuntimeError(
            "瀹夊叏淇濇姢瑙﹀彂锛氭簮 FSP 鏂囦欢鍙戠敓鍙樺寲锛岃剼鏈凡鍋滄銆俓n"
            "婧愭枃浠讹細{}\n鍘熷 SHA256锛歿}\n褰撳墠 SHA256锛歿}".format(source_fsp, expected_hash, now_hash)
        )


def frange(start, stop, step):
    if step <= 0:
        raise ValueError("scan step must be > 0")
    values = []
    value = float(start)
    guard = 0
    while value <= float(stop) + abs(step) * 1e-9 + 1e-18:
        values.append(value)
        value += float(step)
        guard += 1
        if guard > 10000:
            raise RuntimeError("scan points exceed 10000; check range and step")
    if values and abs(values[-1] - float(stop)) > abs(step) * 1e-6:
        values.append(float(stop))
    if not values:
        values.append(float(start))
    return values


def auto_step(start, stop, manual_step, auto_enabled, target_points, step_min, step_max):
    if not auto_enabled:
        if manual_step <= 0:
            raise ValueError("manual step must be > 0")
        return float(manual_step)
    span = abs(float(stop) - float(start))
    if span <= 0:
        return float(manual_step if manual_step > 0 else step_min)
    raw = span / float(max(1, int(target_points) - 1))
    return clamp(raw, float(step_min), float(step_max))


def import_lumapi(lumerical_root):
    api_dir = Path(lumerical_root) / "api" / "python"
    bin_dir = Path(lumerical_root) / "bin"
    for p in (api_dir, bin_dir):
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(p))
        os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
    lumapi_file = api_dir / "lumapi.py"
    spec = importlib.util.spec_from_file_location("lumapi", str(lumapi_file))
    if spec is None or spec.loader is None:
        raise RuntimeError("鏃犳硶瀵煎叆 lumapi锛歿}".format(lumapi_file))
    lumapi = importlib.util.module_from_spec(spec)
    sys.modules["lumapi"] = lumapi
    spec.loader.exec_module(lumapi)
    return lumapi


def find_source_fsp(structure_root):
    files = sorted((Path(structure_root) / "fsp").glob("*.fsp"))
    if len(files) != 1:
        raise RuntimeError("expected exactly one .fsp in fsp folder, got {}".format(len(files)))
    return files[0]


def prepare_run_dir(structure_root, perturbation_name, mode, explicit_run_dir=None):
    root = Path(structure_root) / "results" / perturbation_name
    root.mkdir(parents=True, exist_ok=True)
    if explicit_run_dir:
        run_dir = Path(explicit_run_dir)
        if not run_dir.is_absolute():
            run_dir = root / run_dir
    else:
        run_dir = root / ("run_{}_{}".format(mode, chinese_timestamp()))
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def ensure_folders(run_dir):
    folders = {
        "plan": run_dir / "00_scan_plan",
        "fsp": run_dir / "01_fsp",
        "excel": run_dir / "02_transmission_excel",
        "png": run_dir / "03_transmission_abs2_png",
        "logs": run_dir / "04_logs",
        "work": run_dir / "05_work_fsp",
    }
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def ascii_work_root(config, run_dir):
    root = Path(config["ASCII_WORK_ROOT"]) / "four_pillar_cluster" / safe_token(run_dir.name)
    root.mkdir(parents=True, exist_ok=True)
    return root


def copy_master_templates(source_fsp, folders, config, run_dir):
    result_master = folders["work"] / "master_template.fsp"
    shutil.copy2(str(source_fsp), str(result_master))
    ascii_root = ascii_work_root(config, run_dir)
    ascii_master = ascii_root / "master_template.fsp"
    shutil.copy2(str(source_fsp), str(ascii_master))
    return result_master, ascii_master, ascii_root


def getnamed(fdtd, name, prop, index=None):
    if index is None:
        return fdtd.getnamed(name, prop)
    return fdtd.getnamed(name, prop, int(index))


def setnamed(fdtd, name, prop, value, index=None):
    if index is None:
        fdtd.setnamed(name, prop, value)
    else:
        fdtd.setnamed(name, prop, value, int(index))


def read_geometry(fdtd, config):
    name = config["PILLAR_OBJECT_NAME"]
    count = int(fdtd.getnamednumber(name))
    pillars = []
    for index in range(1, count + 1):
        x = float(getnamed(fdtd, name, "x", index))
        y = float(getnamed(fdtd, name, "y", index))
        r = float(getnamed(fdtd, name, "radius", index))
        zmin = float(getnamed(fdtd, name, "z min", index))
        zmax = float(getnamed(fdtd, name, "z max", index))
        pillars.append({
            "index": index,
            "label": PILLAR_LABELS.get(index, "pillar{}".format(index)),
            "x": x,
            "y": y,
            "radius": r,
            "zmin": zmin,
            "zmax": zmax,
        })
    sub = {
        "x_span": float(getnamed(fdtd, config["SUBSTRATE_OBJECT_NAME"], "x span")),
        "y_span": float(getnamed(fdtd, config["SUBSTRATE_OBJECT_NAME"], "y span")),
        "z_min": float(getnamed(fdtd, config["SUBSTRATE_OBJECT_NAME"], "z min")),
        "z_max": float(getnamed(fdtd, config["SUBSTRATE_OBJECT_NAME"], "z max")),
    }
    fdtd_region = {
        "x_span": float(getnamed(fdtd, config["FDTD_OBJECT_NAME"], "x span")),
        "y_span": float(getnamed(fdtd, config["FDTD_OBJECT_NAME"], "y span")),
        "z_min": float(getnamed(fdtd, config["FDTD_OBJECT_NAME"], "z min")),
        "z_max": float(getnamed(fdtd, config["FDTD_OBJECT_NAME"], "z max")),
        "simulation_time": float(getnamed(fdtd, config["FDTD_OBJECT_NAME"], "simulation time")),
    }
    try:
        fdtd_region["auto_shutoff_min"] = float(getnamed(fdtd, config["FDTD_OBJECT_NAME"], "auto shutoff min"))
    except Exception:
        fdtd_region["auto_shutoff_min"] = None
    min_dist = None
    for i in range(len(pillars)):
        for j in range(i + 1, len(pillars)):
            dx = pillars[i]["x"] - pillars[j]["x"]
            dy = pillars[i]["y"] - pillars[j]["y"]
            dist = (dx * dx + dy * dy) ** 0.5
            min_dist = dist if min_dist is None else min(min_dist, dist)
    return {
        "pillars": pillars,
        "substrate": sub,
        "fdtd": fdtd_region,
        "base_radius": float(np.median([p["radius"] for p in pillars])),
        "min_center_distance": min_dist,
    }


def radius_upper_bound(geometry, config):
    clearance = float(config["MIN_GAP_NM"]) * 1e-9
    half_x = geometry["substrate"]["x_span"] / 2.0
    half_y = geometry["substrate"]["y_span"] / 2.0
    by_edge = min(
        min(half_x - abs(p["x"]), half_y - abs(p["y"])) for p in geometry["pillars"]
    ) - clearance
    if geometry["min_center_distance"]:
        by_neighbor = geometry["min_center_distance"] / 2.0 - clearance
    else:
        by_neighbor = by_edge
    return max(1e-9, min(by_edge, by_neighbor))


def offset_upper_bound(geometry, config, pillar_index, unit_x, unit_y):
    clearance = float(config["EDGE_CLEARANCE_NM"]) * 1e-9
    min_gap = float(config["MIN_GAP_NM"]) * 1e-9
    pillar = geometry["pillars"][pillar_index - 1]
    r = pillar["radius"]
    half_x = geometry["substrate"]["x_span"] / 2.0
    half_y = geometry["substrate"]["y_span"] / 2.0
    limits = []
    if abs(unit_x) > 1e-12:
        if unit_x > 0:
            limits.append((half_x - clearance - r - pillar["x"]) / unit_x)
        else:
            limits.append((-half_x + clearance + r - pillar["x"]) / unit_x)
    if abs(unit_y) > 1e-12:
        if unit_y > 0:
            limits.append((half_y - clearance - r - pillar["y"]) / unit_y)
        else:
            limits.append((-half_y + clearance + r - pillar["y"]) / unit_y)
    positive = [v for v in limits if v >= 0]
    if not positive:
        return 0.0
    boundary_limit = min(positive)

    # 濡傛灉鐢ㄦ埛鎶婂亸绉绘柟鍚戞敼鎴愭湞鍐呮垨鏂滃悜锛岄渶瑕佸悓鏃堕伩鍏嶇洰鏍囨煴涓庡叾浠栨煴鐩镐氦銆?    # 鏉′欢锛殀褰撳墠浣嶇疆 + t * 鏂瑰悜 - 鍏朵粬鏌变腑蹇億 >= r_self + r_other + min_gap銆?    collision_limits = []
    for other in geometry["pillars"]:
        if int(other["index"]) == int(pillar_index):
            continue
        dx = pillar["x"] - other["x"]
        dy = pillar["y"] - other["y"]
        required = r + other["radius"] + min_gap
        b = 2.0 * (dx * unit_x + dy * unit_y)
        c = dx * dx + dy * dy - required * required
        disc = b * b - 4.0 * c
        if disc <= 0:
            continue
        root = disc ** 0.5
        t1 = (-b - root) / 2.0
        t2 = (-b + root) / 2.0
        # first positive root is a usable offset upper bound from t=0
        if t1 > 1e-15:
            collision_limits.append(t1)
        elif t2 > 1e-15 and c < 0:
            collision_limits.append(0.0)
    if collision_limits:
        return max(0.0, min(boundary_limit, min(collision_limits)))
    return boundary_limit


def normalize_direction(dx, dy):
    length = (float(dx) * float(dx) + float(dy) * float(dy)) ** 0.5
    if length <= 0:
        raise ValueError("offset direction cannot be (0,0)")
    return float(dx) / length, float(dy) / length


def build_scan_points(config, geometry, mode, max_points=None):
    kind = config["PERTURBATION_TYPE"]
    points = []
    if kind in ("single_radius", "opposite_pair_radius", "all_radius"):
        auto_upper = radius_upper_bound(geometry, config)
        start = float(config["RADIUS_START_NM"]) * 1e-9
        desired_stop = float(config["RADIUS_STOP_NM"]) * 1e-9
        stop = min(desired_stop, auto_upper)
        if stop < start:
            raise ValueError(
                "radius stop is below start; auto upper bound is {:.3f} nm, adjust RADIUS_START_NM or MIN_GAP_NM".format(nm(auto_upper))
            )
        step = auto_step(
            start, stop, float(config["RADIUS_STEP_NM"]) * 1e-9,
            bool(config["AUTO_RADIUS_STEP"]), int(config["TARGET_SCAN_POINTS"]),
            float(config["RADIUS_STEP_MIN_NM"]) * 1e-9, float(config["RADIUS_STEP_MAX_NM"]) * 1e-9,
        )
        for i, radius in enumerate(frange(start, stop, step)):
            label = "{}_radius_{:.3f}_nm".format(i, nm(radius))
            points.append({
                "index": i,
                "name": "{:04d}_{}".format(i, safe_token(label)),
                "radius": radius,
                "radius_nm": nm(radius),
                "auto_radius_upper_nm": nm(auto_upper),
                "step_nm": nm(step),
            })
    elif kind == "single_offset":
        pillar_index = int(config["TARGET_PILLAR_INDEX"])
        ux, uy = normalize_direction(config["OFFSET_DIRECTION_X"], config["OFFSET_DIRECTION_Y"])
        auto_upper = offset_upper_bound(geometry, config, pillar_index, ux, uy)
        start = float(config["OFFSET_START_NM"]) * 1e-9
        desired_stop = float(config["OFFSET_STOP_NM"]) * 1e-9
        stop = min(desired_stop, auto_upper)
        if stop < start:
            raise ValueError(
                "offset stop is below start; auto upper bound is {:.3f} nm, adjust OFFSET_START_NM or EDGE_CLEARANCE_NM".format(nm(auto_upper))
            )
        step = auto_step(
            start, stop, float(config["OFFSET_STEP_NM"]) * 1e-9,
            bool(config["AUTO_OFFSET_STEP"]), int(config["TARGET_SCAN_POINTS"]),
            float(config["OFFSET_STEP_MIN_NM"]) * 1e-9, float(config["OFFSET_STEP_MAX_NM"]) * 1e-9,
        )
        base = geometry["pillars"][pillar_index - 1]
        for i, offset in enumerate(frange(start, stop, step)):
            new_x = base["x"] + ux * offset
            new_y = base["y"] + uy * offset
            label = "{}_offset_{:.3f}_nm".format(i, nm(offset))
            points.append({
                "index": i,
                "name": "{:04d}_{}".format(i, safe_token(label)),
                "offset": offset,
                "offset_nm": nm(offset),
                "new_x": new_x,
                "new_y": new_y,
                "new_x_nm": nm(new_x),
                "new_y_nm": nm(new_y),
                "unit_x": ux,
                "unit_y": uy,
                "auto_offset_upper_nm": nm(auto_upper),
                "step_nm": nm(step),
            })
    else:
        raise ValueError("鏈煡鎵板姩绫诲瀷锛歿}".format(kind))
    if mode == "test":
        points = points[:int(config["TEST_POINT_COUNT"])]
    if max_points is not None:
        points = points[:int(max_points)]
    return points


def point_parameter_text(config, point):
    kind = config["PERTURBATION_TYPE"]
    if kind in ("single_radius", "opposite_pair_radius", "all_radius"):
        return "radius={:.3f} nm锛涜嚜鍔ㄥ崐寰勪笂闄?{:.3f} nm锛涙闀?{:.3f} nm".format(
            point["radius_nm"], point["auto_radius_upper_nm"], point["step_nm"]
        )
    return "offset={:.3f} nm锛涙柊浣嶇疆 x={:.3f} nm, y={:.3f} nm锛涜嚜鍔ㄥ亸绉讳笂闄?{:.3f} nm锛涙闀?{:.3f} nm".format(
        point["offset_nm"], point["new_x_nm"], point["new_y_nm"], point["auto_offset_upper_nm"], point["step_nm"]
    )


def apply_point(fdtd, config, point):
    fdtd.switchtolayout()
    fdtd_name = config["FDTD_OBJECT_NAME"]
    if config.get("SIMULATION_TIME_S") is not None:
        setnamed(fdtd, fdtd_name, "simulation time", float(config["SIMULATION_TIME_S"]))
    if config.get("AUTO_SHUTOFF_MIN") is not None:
        try:
            setnamed(fdtd, fdtd_name, "auto shutoff min", float(config["AUTO_SHUTOFF_MIN"]))
        except Exception:
            pass
    if config.get("MESH_ACCURACY") is not None:
        try:
            setnamed(fdtd, fdtd_name, "mesh accuracy", int(float(config["MESH_ACCURACY"])))
        except Exception:
            pass
    if config.get("DT_STABILITY_FACTOR") is not None:
        try:
            setnamed(fdtd, fdtd_name, "dt stability factor", float(config["DT_STABILITY_FACTOR"]))
        except Exception:
            pass

    obj = config["PILLAR_OBJECT_NAME"]
    kind = config["PERTURBATION_TYPE"]
    if kind == "single_radius":
        setnamed(fdtd, obj, "radius", point["radius"], int(config["TARGET_PILLAR_INDEX"]))
    elif kind == "opposite_pair_radius":
        for idx in config["PAIR_PILLAR_INDICES"]:
            setnamed(fdtd, obj, "radius", point["radius"], int(idx))
    elif kind == "all_radius":
        for idx in (1, 2, 3, 4):
            setnamed(fdtd, obj, "radius", point["radius"], idx)
    elif kind == "single_offset":
        idx = int(config["TARGET_PILLAR_INDEX"])
        setnamed(fdtd, obj, "x", point["new_x"], idx)
        setnamed(fdtd, obj, "y", point["new_y"], idx)
    else:
        raise ValueError(kind)


def extract_transmission(fdtd, monitor_name):
    wavelength = None
    trans = None
    try:
        result = fdtd.getresult(monitor_name, "T")
        if isinstance(result, dict):
            for key in ("lambda", "wavelength"):
                if key in result:
                    wavelength = np.asarray(result[key]).reshape(-1)
                    break
            if "T" in result:
                trans = np.asarray(result["T"]).reshape(-1)
    except Exception:
        pass
    if wavelength is None:
        wavelength = np.asarray(fdtd.getdata(monitor_name, "lambda")).reshape(-1)
    if trans is None:
        trans = np.asarray(fdtd.transmission(monitor_name)).reshape(-1)
    if wavelength.size != trans.size:
        n = min(wavelength.size, trans.size)
        wavelength = wavelength[:n]
        trans = trans[:n]
    order = np.argsort(wavelength)
    return wavelength[order], trans[order]


def abs2(values):
    arr = np.asarray(values)
    return np.abs(arr) ** 2


def spectrum_summary(wavelength_m, transmission):
    t = abs2(transmission)
    if t.size == 0:
        return {"max": None, "max_nm": None, "min": None, "min_nm": None}
    imax = int(np.argmax(t))
    imin = int(np.argmin(t))
    return {
        "max": float(t[imax]),
        "max_nm": float(nm(wavelength_m[imax])),
        "min": float(t[imin]),
        "min_nm": float(nm(wavelength_m[imin])),
    }


def write_xlsx(path, wavelength_m, transmission):
    """Write a minimal xlsx without openpyxl."""
    rows = [("Wavelength_nm", "Transmission_raw", "Transmission_abs2")]
    for wl, tr, tr_abs2 in zip(nm(wavelength_m), np.asarray(transmission), abs2(transmission)):
        raw = complex(tr)
        if abs(raw.imag) < 1e-30:
            raw_text = "{:.18e}".format(raw.real)
        else:
            raw_text = "{:.18e}{:+.18e}j".format(raw.real, raw.imag)
        rows.append(("{:.18e}".format(float(wl)), raw_text, "{:.18e}".format(float(tr_abs2))))
    sheet_rows = []
    for ridx, row in enumerate(rows, start=1):
        cells = []
        for cidx, value in enumerate(row, start=1):
            col = chr(ord("A") + cidx - 1)
            ref = "{}{}".format(col, ridx)
            if ridx == 1 or cidx == 2:
                cells.append('<c r="{}" t="inlineStr"><is><t>{}</t></is></c>'.format(ref, escape(str(value))))
            else:
                cells.append('<c r="{}"><v>{}</v></c>'.format(ref, value))
        sheet_rows.append('<row r="{}">{}</row>'.format(ridx, "".join(cells)))
    sheet = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>{}</sheetData></worksheet>""".format("".join(sheet_rows))
    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="abs2" sheetId="1" r:id="rId1"/></sheets></workbook>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    wb_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)


def save_abs2_plot(path, config, point, wavelength_m, transmission):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(8.6, 5.2), dpi=160)
    ax.plot(nm(wavelength_m), abs2(transmission), color="#1f77b4", linewidth=1.7)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("|T|^2")
    ax.set_title("{} - {}".format(config["PERTURBATION_NAME"], point["name"]))
    ax.grid(True, alpha=0.28)
    text = point_parameter_text(config, point)
    ax.text(0.03, 0.97, text, transform=ax.transAxes, va="top", ha="left", fontsize=8,
            bbox=dict(facecolor="white", alpha=0.82, edgecolor="#dddddd"))
    fig.tight_layout()
    fig.savefig(str(path))
    plt.close(fig)


def write_scan_plan(path, points):
    if not points:
        return
    fieldnames = sorted(points[0].keys())
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in points:
            writer.writerow(p)


def write_manifest(path, rows):
    keys = [
        "index", "name", "status", "retry_count", "quality_flags", "quality_reasons",
        "solver_status", "solver_status_text", "autoshutoff_final",
        "simulation_time_fs", "auto_shutoff_min", "mesh_accuracy", "dt_stability_factor",
        "fsp", "xlsx", "png", "elapsed_s",
        "max_abs2", "max_wavelength_nm", "min_abs2", "min_wavelength_nm",
    ]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def write_structure_note(path, config, geometry, source_fsp, mode, points):
    pillars = geometry["pillars"]
    lines = []
    lines.append("# 四柱簇结构状态说明")
    lines.append("")
    lines.append("- 运行模式: {}".format(mode))
    lines.append("- 源 FSP: {}".format(source_fsp))
    lines.append("- 扰动名称: {}".format(config["PERTURBATION_NAME"]))
    lines.append("- 降群路径: {}".format(config["GROUP_PATH"]))
    lines.append("- Si 柱数量: {} 个".format(len(pillars)))
    lines.append("- 母版柱半径: {:.3f} nm".format(nm(geometry["base_radius"])))
    lines.append("- 母版柱中心: {}".format(", ".join(
        "{}({:.1f}, {:.1f}) nm".format(p["label"], nm(p["x"]), nm(p["y"])) for p in pillars
    )))
    lines.append("- Si 柱厚度: {:.3f} nm".format(nm(pillars[0]["zmax"] - pillars[0]["zmin"])))
    lines.append("- SiO2 衬底: {:.3f} nm x {:.3f} nm，厚度 {:.3f} nm".format(
        nm(geometry["substrate"]["x_span"]),
        nm(geometry["substrate"]["y_span"]),
        nm(geometry["substrate"]["z_max"] - geometry["substrate"]["z_min"]),
    ))
    lines.append("- FDTD 区域: {:.3f} nm x {:.3f} nm，z {:.3f} nm 到 {:.3f} nm".format(
        nm(geometry["fdtd"]["x_span"]), nm(geometry["fdtd"]["y_span"]),
        nm(geometry["fdtd"]["z_min"]), nm(geometry["fdtd"]["z_max"])
    ))
    if points:
        lines.append("- 扫描起止: {} -> {}".format(point_parameter_text(config, points[0]), point_parameter_text(config, points[-1])))
    lines.append("- 扫描点数: {}".format(len(points)))
    lines.append("")
    lines.append("## 源文件保护规则")
    lines.append("脚本不会修改 fsp 文件夹内源 .fsp；每个扫描点都从 results 中母版副本复制后再修改。")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def result_paths(folders, point):
    stem = point["name"]
    return {
        "fsp": folders["fsp"] / (stem + ".fsp"),
        "xlsx": folders["excel"] / (stem + "_transmission_abs2.xlsx"),
        "png": folders["png"] / (stem + "_transmission_abs2.png"),
    }


def parse_args(config):
    parser = argparse.ArgumentParser(description=config["PERTURBATION_NAME"])
    parser.add_argument("--mode", choices=["ask", "test", "full", "preview"], default=config.get("RUN_MODE_DEFAULT", "ask"))
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--max-points", type=int, default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--auto-retry-max", type=int, default=None)
    parser.add_argument("--disable-auto-retry", action="store_true")
    parser.add_argument("--quality-t-limit", type=float, default=None)
    parser.add_argument("--quality-ripple-limit", type=float, default=None)
    args = parser.parse_args()
    args.prompted_mode = False
    if args.test:
        args.mode = "test"
    if args.full:
        args.mode = "full"
    if args.preview:
        args.mode = "preview"
    if args.mode == "ask":
        args.prompted_mode = True
        print("")
        print("请选择 {} {} 脚本运行模式：".format(config["STRUCTURE_CN_NAME"], config["PERTURBATION_NAME"]))
        print("  1 = 测试模式：真实仿真前 {} 个点".format(config["TEST_POINT_COUNT"]))
        print("  2 = 完整真实仿真")
        print("  3 = 预览模式：只生成扫描计划，不仿真")
        choice = input("请输入 1/2/3 后按回车：").strip()
        args.mode = {"1": "test", "2": "full", "3": "preview"}.get(choice)
        if args.mode is None:
            raise ValueError("只能输入 1、2 或 3。")
    if args.auto_retry_max is not None:
        config["AUTO_RETRY_MAX"] = int(args.auto_retry_max)
    if args.disable_auto_retry:
        config["AUTO_RETRY_ENABLED"] = False
    if args.quality_t_limit is not None:
        config["QUALITY_T_LIMIT"] = float(args.quality_t_limit)
    if args.quality_ripple_limit is not None:
        config["QUALITY_RIPPLE_LIMIT"] = float(args.quality_ripple_limit)
    return args


def maybe_ask_fdtd_runtime_overrides(config):
    keys = ("SIMULATION_TIME_FS", "AUTO_SHUTOFF_MIN", "MESH_ACCURACY", "DT_STABILITY_FACTOR")
    if not any(key in config for key in keys):
        return
    print("")
    print("当前 FDTD 参数：simulation time = {} fs；auto shutoff min = {}；mesh accuracy = {}；dt stability factor = {}".format(
        config.get("SIMULATION_TIME_FS", float(config.get("SIMULATION_TIME_S", 0.0)) * 1e15),
        config.get("AUTO_SHUTOFF_MIN"),
        config.get("MESH_ACCURACY"),
        config.get("DT_STABILITY_FACTOR"),
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
        current = config.get(key, float(config.get("SIMULATION_TIME_S", 0.0)) * 1e15 if key == "SIMULATION_TIME_FS" else "")
        raw = input("{}，空白表示不改，当前 {}：".format(label, current)).strip()
        if not raw:
            continue
        value = float(raw)
        if value <= 0:
            print("{} 必须大于 0，已忽略。".format(label))
            continue
        config[key] = int(value) if key == "MESH_ACCURACY" else value
    if config.get("SIMULATION_TIME_FS") is not None:
        config["SIMULATION_TIME_S"] = float(config["SIMULATION_TIME_FS"]) * 1e-15
def run(config):
    args = parse_args(config)
    normalize_autotune_config(config)
    mode = args.mode
    if mode in ("test", "full") and getattr(args, "prompted_mode", False):
        maybe_ask_fdtd_runtime_overrides(config)
    structure_root = Path(config["STRUCTURE_ROOT"])
    source_fsp = find_source_fsp(structure_root)
    source_hash = file_sha256(source_fsp)
    run_dir = prepare_run_dir(structure_root, config["PERTURBATION_NAME"], mode, args.run_dir)
    folders = ensure_folders(run_dir)
    result_master, ascii_master, ascii_root = copy_master_templates(source_fsp, folders, config, run_dir)

    lumapi = import_lumapi(config["LUMERICAL_ROOT"])
    fdtd = lumapi.FDTD(hide=True)
    fdtd.load(str(ascii_master))
    geometry = read_geometry(fdtd, config)
    fdtd.close()

    points = build_scan_points(config, geometry, mode, args.max_points)
    write_scan_plan(folders["plan"] / "scan_points.csv", points)
    write_structure_note(run_dir / "结构状态说明.md", config, geometry, source_fsp, mode, points)

    print("源 FSP: {}".format(source_fsp))
    print("results 工作母版 FSP: {}".format(result_master))
    print("Lumerical 英文镜像母版 FSP: {}".format(ascii_master))
    print("输出批次目录: {}".format(run_dir))
    print("扰动: {}；降群路径: {}".format(config["PERTURBATION_NAME"], config["GROUP_PATH"]))
    print("计划仿真点数: {}".format(len(points)))

    if mode == "preview":
        print("预览模式结束：没有运行真实 FDTD。")
        return

    rows = []
    total_start = time.time()
    max_retry = int(config.get("AUTO_RETRY_MAX", 2)) if config.get("AUTO_RETRY_ENABLED", True) else 0
    base_runtime_config = clone_runtime_config(config)
    retry_history_path = folders["logs"] / "retry_history.csv"

    for idx, point in enumerate(points, 1):
        assert_source_unchanged(source_fsp, source_hash)
        paths = result_paths(folders, point)
        ascii_point_base = ascii_root / (point["name"] + ".fsp")
        shutil.copy2(str(ascii_master), str(ascii_point_base))

        print("[{}/{}] 开始仿真：{}".format(idx, len(points), point["name"]))

        final_quality = None
        final_summary = {"max": None}
        final_elapsed = 0.0
        final_solver_info = {}
        final_runtime_config = clone_runtime_config(base_runtime_config)
        accepted = False
        wavelength_m = None
        transmission = None
        final_ascii_point = ascii_point_base
        attempt = 0

        for attempt in range(0, max_retry + 1):
            runtime_config = final_runtime_config if attempt == 0 else next_retry_config(
                base_runtime_config, final_runtime_config, final_quality or {"flags": []}, attempt
            )
            final_runtime_config = runtime_config
            attempt_suffix = "" if attempt == 0 else "_retry{:02d}".format(attempt)
            ascii_point = ascii_root / (point["name"] + attempt_suffix + ".fsp")
            if attempt == 0:
                shutil.copy2(str(ascii_point_base), str(ascii_point))
            else:
                shutil.copy2(str(ascii_master), str(ascii_point))
            final_ascii_point = ascii_point

            print("  尝试 {}/{}：{}".format(attempt, max_retry, runtime_profile_text(runtime_config)))
            start = time.time()
            fdtd = None
            solver_info = {}
            quality = None
            wavelength_m = None
            transmission = None
            try:
                fdtd = lumapi.FDTD(hide=True)
                fdtd.load(str(ascii_point))
                apply_point(fdtd, runtime_config, point)
                fdtd.save(str(ascii_point))
                fdtd.run()
                solver_info = extract_solver_info(fdtd, runtime_config.get("FDTD_OBJECT_NAME", "FDTD"))
                wavelength_m, transmission = extract_transmission(fdtd, runtime_config["T_MONITOR_NAME"])
                fdtd.save(str(ascii_point))
                quality = evaluate_spectrum_quality(wavelength_m, transmission, solver_info, runtime_config)
            except Exception as exc:
                quality = {
                    "accepted": False,
                    "status": "need_retry",
                    "flags": ["exception"],
                    "reasons": [repr(exc)],
                    "tmax": "",
                    "tmin": "",
                    "ripple_score": "",
                    "sign_changes": "",
                }
            finally:
                try:
                    if fdtd is not None:
                        fdtd.close()
                except Exception:
                    pass

            elapsed = time.time() - start
            final_elapsed = elapsed
            final_quality = quality
            final_solver_info = solver_info
            append_retry_history(retry_history_path, {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "point_index": point["index"],
                "point_name": point["name"],
                "attempt": attempt,
                "accepted": quality.get("accepted"),
                "quality_status": quality.get("status"),
                "flags": quality.get("flags"),
                "reasons": quality.get("reasons"),
                "tmax": quality.get("tmax"),
                "tmin": quality.get("tmin"),
                "ripple_score": quality.get("ripple_score"),
                "sign_changes": quality.get("sign_changes"),
                "solver_status": solver_info.get("solver_status", ""),
                "solver_status_text": solver_info.get("solver_status_text", ""),
                "autoshutoff_final": solver_info.get("autoshutoff_final", ""),
                "simulation_time_fs": runtime_config.get("SIMULATION_TIME_FS"),
                "auto_shutoff_min": runtime_config.get("AUTO_SHUTOFF_MIN"),
                "mesh_accuracy": runtime_config.get("MESH_ACCURACY"),
                "dt_stability_factor": runtime_config.get("DT_STABILITY_FACTOR"),
                "elapsed_s": "{:.3f}".format(elapsed),
                "fsp": str(ascii_point),
                "xlsx": str(paths["xlsx"]),
                "png": str(paths["png"]),
            })

            if quality.get("accepted"):
                accepted = True
                break

        try:
            shutil.copy2(str(final_ascii_point), str(paths["fsp"]))
        except Exception:
            pass

        if wavelength_m is not None and transmission is not None:
            write_xlsx(paths["xlsx"], wavelength_m, transmission)
            save_abs2_plot(paths["png"], final_runtime_config, point, wavelength_m, transmission)
            final_summary = spectrum_summary(wavelength_m, transmission)

        row_status = final_quality.get("status") if final_quality else "unknown"
        if not accepted:
            row_status = "failed_quarantined"

        rows.append({
            "index": point["index"],
            "name": point["name"],
            "status": row_status,
            "retry_count": max(0, attempt),
            "quality_flags": ";".join(final_quality.get("flags") or []) if final_quality else "",
            "quality_reasons": ";".join(final_quality.get("reasons") or []) if final_quality else "",
            "solver_status": final_solver_info.get("solver_status", ""),
            "solver_status_text": final_solver_info.get("solver_status_text", ""),
            "autoshutoff_final": final_solver_info.get("autoshutoff_final", ""),
            "simulation_time_fs": final_runtime_config.get("SIMULATION_TIME_FS"),
            "auto_shutoff_min": final_runtime_config.get("AUTO_SHUTOFF_MIN"),
            "mesh_accuracy": final_runtime_config.get("MESH_ACCURACY"),
            "dt_stability_factor": final_runtime_config.get("DT_STABILITY_FACTOR"),
            "fsp": str(paths["fsp"]),
            "xlsx": str(paths["xlsx"]),
            "png": str(paths["png"]),
            "elapsed_s": "{:.3f}".format(final_elapsed),
            "max_abs2": "" if final_summary.get("max") is None else "{:.18e}".format(final_summary["max"]),
            "max_wavelength_nm": "" if final_summary.get("max") is None else "{:.9f}".format(final_summary["max_nm"]),
            "min_abs2": "" if final_summary.get("max") is None else "{:.18e}".format(final_summary["min"]),
            "min_wavelength_nm": "" if final_summary.get("max") is None else "{:.9f}".format(final_summary["min_nm"]),
        })
        write_manifest(run_dir / "manifest.csv", rows)
        assert_source_unchanged(source_fsp, source_hash)

    print("全部完成。总用时 {}".format(format_duration(time.time() - total_start)))

