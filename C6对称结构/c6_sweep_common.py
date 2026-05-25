# -*- coding: utf-8 -*-
"""
C6 姣嶇粨鏋勬壈鍔ㄦ壂鎻忓叕鍏辨ā鍧椼€?
鐩綍瑙勫垯娌跨敤鍓嶉潰鎵€鏈夎剼鏈細
- 鍏ュ彛鑴氭湰鏀惧湪 姣嶇粨鏋?coding/鎵板姩鍚?run_*.py锛?- 缁撴灉鏀惧湪 姣嶇粨鏋?results/鎵板姩鍚?run_妯″紡_鏃堕棿鎴?锛?- 婧?fsp 鏂囦欢澶瑰唴鐨?.fsp 姘镐笉鍐欏叆锛屽彧澶嶅埗銆?"""

from __future__ import print_function

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
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

warnings.filterwarnings("ignore", category=UserWarning, module=r"numpy\._distributor_init")
warnings.filterwarnings("ignore", message=r".*loaded more than 1 DLL.*")
warnings.filterwarnings("ignore", message=r".*deprecated.*")

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
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


def nm(value_m):
    arr = np.asarray(value_m)
    if arr.shape == ():
        return float(arr) * 1e9
    return arr * 1e9


def chinese_timestamp():
    now = datetime.now()
    return "{}年{}月{}日_{:02d}时{:02d}分{:02d}秒".format(now.year, now.month, now.day, now.hour, now.minute, now.second)


def safe_token(text):
    chars = []
    for ch in str(text):
        if ch.isalnum() or ch in ("_", "-", "."):
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars).strip("_") or "point"


def format_duration(seconds):
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return "{:.1f} s".format(seconds)
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    if minutes < 60:
        return "{} min {} s".format(minutes, sec)
    return "{} h {} min {} s".format(minutes // 60, minutes % 60, sec)


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_source_unchanged(source_fsp, expected_hash):
    if file_sha256(source_fsp) != expected_hash:
        raise RuntimeError("婧?FSP 鏂囦欢鍙戠敓鍙樺寲锛屼负閬垮厤璇敼婧愭枃浠讹紝鑴氭湰鍋滄锛歿}".format(source_fsp))


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
    if len(files) == 0:
        raise RuntimeError("没有在 fsp 文件夹内找到 .fsp。")
    # 若存在多个 .fsp，优先使用最新文件。
    return sorted(files, key=lambda p: (p.name, p.stat().st_mtime), reverse=True)[0]


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
    root = Path(config["ASCII_WORK_ROOT"]) / config["SAFE_NAME"] / safe_token(run_dir.name)
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


def frange(start, stop, step):
    if step <= 0:
        raise ValueError("步长必须大于 0。")
    vals = []
    v = float(start)
    guard = 0
    while v <= float(stop) + abs(step) * 1e-9 + 1e-18:
        vals.append(v)
        v += step
        guard += 1
        if guard > 10000:
            raise RuntimeError("扫描点超过 10000，请检查范围和步长。")
    if vals and abs(vals[-1] - stop) > abs(step) * 1e-6:
        vals.append(float(stop))
    return vals or [float(start)]


def auto_step(start, stop, manual, enabled, target, step_min, step_max):
    if not enabled:
        return float(manual)
    span = abs(float(stop) - float(start))
    if span <= 0:
        return float(manual)
    raw = span / float(max(1, int(target) - 1))
    return max(float(step_min), min(float(step_max), raw))


def read_basic_geometry(fdtd, config):
    g = {"objects": {}}
    for name in (config.get("OBJECT_NAME"), "Si_outer_ring", "air_inner_ring", "SiO2_substrate", "FDTD"):
        if not name:
            continue
        try:
            count = int(fdtd.getnamednumber(name))
        except Exception:
            count = 0
        arr = []
        for i in range(1, count + 1):
            d = {"index": i}
            for p in ("x", "y", "x span", "y span", "z min", "z max", "z span", "radius", "rotation 1"):
                try:
                    d[p] = float(getnamed(fdtd, name, p, i))
                except Exception:
                    pass
            arr.append(d)
        if arr:
            g["objects"][name] = arr
    return g


def build_scan_points(config, mode, max_points=None):
    label = safe_token(config["SCAN_LABEL"])
    value_name = safe_token(config["VALUE_NAME"])
    stem = label if label == value_name or label.endswith("_" + value_name) else "{}_{}".format(label, value_name)
    start = float(config["SCAN_START_NM"]) * 1e-9
    stop = float(config["SCAN_STOP_NM"]) * 1e-9
    step = auto_step(
        start, stop, float(config["SCAN_STEP_NM"]) * 1e-9,
        bool(config["AUTO_SCAN_STEP"]), int(config["TARGET_SCAN_POINTS"]),
        float(config["SCAN_STEP_MIN_NM"]) * 1e-9, float(config["SCAN_STEP_MAX_NM"]) * 1e-9,
    )
    points = []
    for i, value in enumerate(frange(start, stop, step)):
        points.append({
            "index": i,
            "name": "{:04d}_{}_{:.3f}nm".format(i, stem, nm(value)),
            "value": value,
            "value_nm": nm(value),
            "step_nm": nm(step),
        })
    if mode == "test":
        points = points[:int(config["TEST_POINT_COUNT"])]
    if max_points is not None:
        points = points[:int(max_points)]
    return points


def radial_offset(base_x, base_y, offset):
    r = (base_x * base_x + base_y * base_y) ** 0.5
    if r <= 0:
        return base_x + offset, base_y
    return base_x + base_x / r * offset, base_y + base_y / r * offset


def apply_fdtd_runtime_settings(fdtd, config):
    fdtd_name = config.get("FDTD_OBJECT_NAME", "FDTD")
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


def apply_point(fdtd, config, point):
    fdtd.switchtolayout()
    apply_fdtd_runtime_settings(fdtd, config)

    kind = config["OPERATION"]
    obj = config["OBJECT_NAME"]
    v = float(point["value"])
    if kind == "set_radius":
        for idx in config["TARGET_INDICES"]:
            setnamed(fdtd, obj, "radius", v, idx)
    elif kind == "set_x_span":
        for idx in config["TARGET_INDICES"]:
            setnamed(fdtd, obj, "x span", v, idx)
    elif kind == "set_y_span":
        for idx in config["TARGET_INDICES"]:
            setnamed(fdtd, obj, "y span", v, idx)
    elif kind == "scale_y_span":
        scale = v / (float(config["BASE_REFERENCE_NM"]) * 1e-9)
        for idx in config["TARGET_INDICES"]:
            old = float(getnamed(fdtd, obj, "y span", idx))
            setnamed(fdtd, obj, "y span", old * scale, idx)
    elif kind == "offset_single":
        idx = int(config["TARGET_INDICES"][0])
        x0 = float(getnamed(fdtd, obj, "x", idx))
        y0 = float(getnamed(fdtd, obj, "y", idx))
        x, y = radial_offset(x0, y0, v)
        setnamed(fdtd, obj, "x", x, idx)
        setnamed(fdtd, obj, "y", y, idx)
    elif kind == "insert_cut":
        # 鍗曠偣缂哄彛锛氬湪鍏缂濈幆鍙充晶鎻掑叆涓€涓?etch 鐭╁舰鍒囧彛锛屽昂瀵搁殢 cut 鎵弿銆?        outer = float(getnamed(fdtd, "Si_outer_ring", "radius"))
        zmin = float(getnamed(fdtd, "air_inner_ring", "z min"))
        zmax = float(getnamed(fdtd, "air_inner_ring", "z max"))
        fdtd.addrect()
        fdtd.set("name", "air_single_cut")
        fdtd.set("material", "etch")
        fdtd.set("x", outer - v / 2.0)
        fdtd.set("y", 0)
        fdtd.set("x span", max(v, 1e-12))
        fdtd.set("y span", float(config["CUT_WIDTH_NM"]) * 1e-9)
        fdtd.set("z min", zmin)
        fdtd.set("z max", zmax)
        try:
            fdtd.set("override mesh order from material database", 1)
            fdtd.set("mesh order", 1)
        except Exception:
            pass
    else:
        raise ValueError("鏈煡 OPERATION: {}".format(kind))


def extract_transmission(fdtd, monitor_name):
    wl = None
    tr = None
    try:
        result = fdtd.getresult(monitor_name, "T")
        if isinstance(result, dict):
            for key in ("lambda", "wavelength"):
                if key in result:
                    wl = np.asarray(result[key]).reshape(-1)
                    break
            if "T" in result:
                tr = np.asarray(result["T"]).reshape(-1)
    except Exception:
        pass
    if wl is None:
        wl = np.asarray(fdtd.getdata(monitor_name, "lambda")).reshape(-1)
    if tr is None:
        tr = np.asarray(fdtd.transmission(monitor_name)).reshape(-1)
    n = min(wl.size, tr.size)
    wl = wl[:n]
    tr = tr[:n]
    order = np.argsort(wl)
    return wl[order], tr[order]


def abs2(values):
    return np.abs(np.asarray(values)) ** 2


def spectrum_summary(wavelength_m, transmission):
    t = abs2(transmission)
    if t.size == 0:
        return {"max": None}
    imax = int(np.argmax(t))
    imin = int(np.argmin(t))
    return {"max": float(t[imax]), "max_nm": float(nm(wavelength_m[imax])), "min": float(t[imin]), "min_nm": float(nm(wavelength_m[imin]))}


def write_xlsx(path, wavelength_m, transmission):
    rows = [("Wavelength_nm", "Transmission_raw", "Transmission_abs2")]
    for wl, tr, tr2 in zip(nm(wavelength_m), np.asarray(transmission), abs2(transmission)):
        raw = complex(tr)
        raw_text = "{:.18e}".format(raw.real) if abs(raw.imag) < 1e-30 else "{:.18e}{:+.18e}j".format(raw.real, raw.imag)
        rows.append(("{:.18e}".format(float(wl)), raw_text, "{:.18e}".format(float(tr2))))
    sheet_rows = []
    for r, row in enumerate(rows, 1):
        cells = []
        for c, val in enumerate(row, 1):
            ref = "{}{}".format(chr(ord("A") + c - 1), r)
            if r == 1 or c == 2:
                cells.append('<c r="{}" t="inlineStr"><is><t>{}</t></is></c>'.format(ref, escape(str(val))))
            else:
                cells.append('<c r="{}"><v>{}</v></c>'.format(ref, val))
        sheet_rows.append('<row r="{}">{}</row>'.format(r, "".join(cells)))
    sheet = '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{}</sheetData></worksheet>'.format("".join(sheet_rows))
    workbook = '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="abs2" sheetId="1" r:id="rId1"/></sheets></workbook>'
    rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    wb_rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
    ctype = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'
    with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ctype)
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
    fig, ax = plt.subplots(figsize=(8.6, 5.2), dpi=160)
    ax.plot(nm(wavelength_m), abs2(transmission), color="#1f77b4", linewidth=1.7)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("|T|^2")
    ax.set_title("{} - {}".format(config["PERTURBATION_NAME"], point["name"]))
    ax.grid(True, alpha=0.28)
    ax.text(0.03, 0.97, "{} = {:.3f} nm".format(config["VALUE_NAME"], point["value_nm"]), transform=ax.transAxes, va="top", ha="left", fontsize=8, bbox=dict(facecolor="white", alpha=0.82, edgecolor="#dddddd"))
    fig.tight_layout()
    fig.savefig(str(path))
    plt.close(fig)


def write_scan_plan(path, points):
    if not points:
        return
    keys = sorted(points[0].keys())
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
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


def write_note(path, config, source_fsp, geometry, points, mode):
    lines = [
        "# {} 结构状态说明".format(config["STRUCTURE_CN_NAME"]),
        "",
        "- 运行模式: {}".format(mode),
        "- 源 FSP: {}".format(source_fsp),
        "- 扰动名称: {}".format(config["PERTURBATION_NAME"]),
        "- 降群路径: {}".format(config["GROUP_PATH"]),
        "- 对象名称: {}".format(config["OBJECT_NAME"]),
        "- 操作说明: {}".format(config["OPERATION_DESCRIPTION"]),
        "- 扫描点数: {}".format(len(points)),
        "- 结果目录遵循 00_scan_plan / 01_fsp / 02_transmission_excel / 03_transmission_abs2_png / 04_logs / 05_work_fsp。",
        "",
        "## 实际读取到的主要几何",
    ]
    for name, arr in geometry.get("objects", {}).items():
        lines.append("- {}: {} 个对象".format(name, len(arr)))
        for d in arr[:8]:
            desc = ", ".join("{}={:.3f} nm".format(k, nm(v)) for k, v in d.items() if k in ("x", "y", "x span", "y span", "radius", "z span"))
            lines.append("  - index {} {}".format(d.get("index"), desc))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def result_paths(folders, point):
    return {
        "fsp": folders["fsp"] / (point["name"] + ".fsp"),
        "xlsx": folders["excel"] / (point["name"] + "_transmission_abs2.xlsx"),
        "png": folders["png"] / (point["name"] + "_transmission_abs2.png"),
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
    geometry = read_basic_geometry(fdtd, config)
    fdtd.close()

    points = build_scan_points(config, mode, args.max_points)
    write_scan_plan(folders["plan"] / "scan_points.csv", points)
    write_note(run_dir / "结构状态说明.md", config, source_fsp, geometry, points, mode)

    print("源 FSP: {}".format(source_fsp))
    print("results 工作母版 FSP: {}".format(result_master))
    print("Lumerical 英文镜像母版 FSP: {}".format(ascii_master))
    print("输出批次目录: {}".format(run_dir))
    print("扰动: {}；降群路径: {}".format(config["PERTURBATION_NAME"], config["GROUP_PATH"]))
    print("扫描: {} 从 {:.3f} nm 到 {:.3f} nm，计划点数 {}".format(config["VALUE_NAME"], config["SCAN_START_NM"], config["SCAN_STOP_NM"], len(points)))
    print("扫描计划已保存: {}".format(folders["plan"] / "scan_points.csv"))
    print("结构说明已保存: {}".format(run_dir / "结构状态说明.md"))

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

        print("[{}/{}] 开始仿真：{}；{}={:.3f} nm".format(idx, len(points), point["name"], config["VALUE_NAME"], point["value_nm"]))

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
                # attempt 0 uses the base file path directly; avoid self-copy on Windows.
                if str(ascii_point_base) != str(ascii_point):
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

            print("  质量检测：{}；flags={}".format(quality.get("status"), ",".join(quality.get("flags") or [])))
            if quality.get("accepted"):
                accepted = True
                break
            if attempt < max_retry:
                print("  当前点不收敛，暂停后续扰动点，优先重试当前点。")
            else:
                print("  超过最大自动重试次数，标记 failed_quarantined，继续下一个扰动点。")

        try:
            shutil.copy2(str(final_ascii_point), str(paths["fsp"]))
        except Exception:
            pass

        if wavelength_m is not None and transmission is not None:
            write_xlsx(paths["xlsx"], wavelength_m, transmission)
            save_abs2_plot(paths["png"], final_runtime_config, point, wavelength_m, transmission)
            final_summary = spectrum_summary(wavelength_m, transmission)
        else:
            final_summary = {"max": None}

        eta = ((time.time() - total_start) / float(idx)) * (len(points) - idx)
        print("    完成，用时 {}；预计剩余 {}".format(format_duration(final_elapsed), format_duration(eta)))
        if final_summary.get("max") is not None:
            print("    本点谱信息: max |T|^2={:.6g} @ {:.3f} nm；min |T|^2={:.6g} @ {:.3f} nm".format(final_summary["max"], final_summary["max_nm"], final_summary["min"], final_summary["min_nm"]))

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
