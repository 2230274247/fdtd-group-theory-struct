# -*- coding: utf-8 -*-
"""
C3 母结构扰动扫描公共模块。

本模块只负责“复制母版 -> 修改副本 -> 运行仿真 -> 保存结果”的通用流程。
源 fsp 文件夹中的 .fsp 永远只读，不会被 save 或 setnamed 写回。
"""
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


def nm(value_m):
    arr = np.asarray(value_m)
    if arr.shape == ():
        return float(arr) * 1e9
    return arr * 1e9


def um_from_nm(value_nm):
    return float(value_nm) / 1000.0


def chinese_timestamp():
    now = datetime.now()
    return "{}年{}月{}日_{:02d}时{:02d}分{:02d}秒".format(
        now.year, now.month, now.day, now.hour, now.minute, now.second
    )


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
        raise RuntimeError("源 FSP 文件发生变化，脚本已停止，避免误改源文件：{}".format(source_fsp))


def import_lumapi(lumerical_root):
    api_dir = Path(lumerical_root) / "api" / "python"
    bin_dir = Path(lumerical_root) / "bin"
    for p in (api_dir, bin_dir):
        os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(p))
    lumapi_file = api_dir / "lumapi.py"
    spec = importlib.util.spec_from_file_location("lumapi", str(lumapi_file))
    if spec is None or spec.loader is None:
        raise RuntimeError("无法导入 lumapi：{}".format(lumapi_file))
    lumapi = importlib.util.module_from_spec(spec)
    sys.modules["lumapi"] = lumapi
    spec.loader.exec_module(lumapi)
    return lumapi


def find_source_fsp(structure_root):
    files = sorted((Path(structure_root) / "fsp").glob("*.fsp"))
    if not files:
        raise RuntimeError("没有在 fsp 文件夹中找到 .fsp 文件。")
    # 如果有多个 .fsp，优先选择文件名时间戳较新的版本。
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


def build_scan_points(config, mode, max_points=None):
    unit = config.get("SCAN_UNIT", "nm")
    label = safe_token(config["SCAN_LABEL"])
    value_name = safe_token(config["VALUE_NAME"])
    stem = label if label == value_name or label.endswith("_" + value_name) else "{}_{}".format(label, value_name)
    if unit == "deg":
        start = float(config["SCAN_START_DEG"])
        stop = float(config["SCAN_STOP_DEG"])
        step = auto_step(
            start, stop, float(config["SCAN_STEP_DEG"]), bool(config["AUTO_SCAN_STEP"]),
            int(config["TARGET_SCAN_POINTS"]), float(config["SCAN_STEP_MIN_DEG"]), float(config["SCAN_STEP_MAX_DEG"])
        )
        points = []
        for i, value in enumerate(frange(start, stop, step)):
            points.append({
                "index": i,
                "name": "{:04d}_{}_{:+.3f}deg".format(i, stem, value),
                "value": value,
                "value_deg": value,
                "step_deg": step,
            })
    else:
        start = float(config["SCAN_START_NM"]) * 1e-9
        stop = float(config["SCAN_STOP_NM"]) * 1e-9
        step = auto_step(
            start, stop, float(config["SCAN_STEP_NM"]) * 1e-9, bool(config["AUTO_SCAN_STEP"]),
            int(config["TARGET_SCAN_POINTS"]), float(config["SCAN_STEP_MIN_NM"]) * 1e-9,
            float(config["SCAN_STEP_MAX_NM"]) * 1e-9
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
            try:
                setnamed(fdtd, obj, "radius 2", v, idx)
            except Exception:
                pass
    elif kind == "set_x_span":
        for idx in config["TARGET_INDICES"]:
            setnamed(fdtd, obj, "x span", v, idx)
    elif kind == "set_y_span":
        for idx in config["TARGET_INDICES"]:
            setnamed(fdtd, obj, "y span", v, idx)
    elif kind == "scale_xy_span":
        scale = v / (float(config["BASE_REFERENCE_NM"]) * 1e-9)
        for idx in config["TARGET_INDICES"]:
            old_x = float(getnamed(fdtd, obj, "x span", idx))
            old_y = float(getnamed(fdtd, obj, "y span", idx))
            setnamed(fdtd, obj, "x span", old_x * scale, idx)
            setnamed(fdtd, obj, "y span", old_y * scale, idx)
    elif kind == "offset_single":
        idx = int(config["TARGET_INDICES"][0])
        x0 = float(getnamed(fdtd, obj, "x", idx))
        y0 = float(getnamed(fdtd, obj, "y", idx))
        x, y = radial_offset(x0, y0, v)
        setnamed(fdtd, obj, "x", x, idx)
        setnamed(fdtd, obj, "y", y, idx)
    elif kind == "set_rotation_delta":
        for idx in config["TARGET_INDICES"]:
            base = float(getnamed(fdtd, obj, "rotation 1", idx))
            setnamed(fdtd, obj, "rotation 1", base + v, idx)
    else:
        raise ValueError("未知 OPERATION: {}".format(kind))


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
    return {
        "max": float(t[imax]), "max_nm": float(nm(wavelength_m[imax])),
        "min": float(t[imin]), "min_nm": float(nm(wavelength_m[imin])),
    }


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
    if config.get("SCAN_UNIT") == "deg":
        text = "{} = {:+.3f} deg".format(config["VALUE_NAME"], point["value_deg"])
    else:
        text = "{} = {:.3f} nm".format(config["VALUE_NAME"], point["value_nm"])
    ax.text(0.03, 0.97, text, transform=ax.transAxes, va="top", ha="left", fontsize=8,
            bbox=dict(facecolor="white", alpha=0.82, edgecolor="#dddddd"))
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
    keys = ["index", "name", "status", "fsp", "xlsx", "png", "elapsed_s", "max_abs2", "max_wavelength_nm", "min_abs2", "min_wavelength_nm"]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_basic_geometry(fdtd, config):
    g = {"objects": {}}
    names = list(config.get("GEOMETRY_OBJECTS", []))
    for name in ("SiO2_substrate", "FDTD", "source", "T"):
        if name not in names:
            names.append(name)
    for name in names:
        try:
            count = int(fdtd.getnamednumber(name))
        except Exception:
            count = 0
        arr = []
        for i in range(1, count + 1):
            d = {"index": i}
            for p in ("x", "y", "x span", "y span", "z min", "z max", "z span", "radius", "radius 2", "rotation 1"):
                try:
                    d[p] = float(getnamed(fdtd, name, p, i if count > 1 else None))
                except Exception:
                    pass
            arr.append(d)
        if arr:
            g["objects"][name] = arr
    return g


def write_note(path, config, source_fsp, geometry, points, mode):
    lines = [
        "# {} 结构状态说明".format(config["STRUCTURE_CN_NAME"]),
        "",
        "- 运行模式：{}".format(mode),
        "- 源 FSP：{}".format(source_fsp),
        "- 扰动名称：{}".format(config["PERTURBATION_NAME"]),
        "- 降群路径：{}".format(config["GROUP_PATH"]),
        "- 操作对象：{}".format(config["OBJECT_NAME"]),
        "- 操作说明：{}".format(config["OPERATION_DESCRIPTION"]),
        "- 扫描点数：{}".format(len(points)),
        "- 结果目录：00_scan_plan / 01_fsp / 02_transmission_excel / 03_transmission_abs2_png / 04_logs / 05_work_fsp",
        "",
        "## 用户主要修改区解释",
    ]
    lines.extend(config.get("USER_GUIDE", []))
    lines.extend(["", "## 实际读取到的主要几何"])
    for name, arr in geometry.get("objects", {}).items():
        lines.append("- {}：{} 个对象".format(name, len(arr)))
        for d in arr[:10]:
            chunks = []
            for k in ("x", "y", "x span", "y span", "radius", "radius 2", "z span", "rotation 1"):
                if k in d:
                    if k == "rotation 1":
                        chunks.append("{}={:.3f} deg".format(k, d[k]))
                    else:
                        chunks.append("{}={:.3f} um".format(k, float(d[k]) * 1e6))
            lines.append("  - index {} {}".format(d.get("index"), ", ".join(chunks)))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def result_paths(folders, point):
    return {
        "fsp": folders["fsp"] / (point["name"] + ".fsp"),
        "xlsx": folders["excel"] / (point["name"] + "_transmission_abs2.xlsx"),
        "png": folders["png"] / (point["name"] + "_transmission_abs2.png"),
    }


def describe_scan(config, points):
    if config.get("SCAN_UNIT") == "deg":
        step = points[0].get("step_deg", 0) if points else 0
        return "{}：{:+.3f} deg 到 {:+.3f} deg，自动/当前步长 {:.3f} deg，共 {} 组".format(
            config["VALUE_NAME"], float(config["SCAN_START_DEG"]), float(config["SCAN_STOP_DEG"]), float(step), len(points)
        )
    step = points[0].get("step_nm", 0) if points else 0
    return "{}：{:.4f} um 到 {:.4f} um，自动/当前步长 {:.4f} um，共 {} 组".format(
        config["VALUE_NAME"], um_from_nm(config["SCAN_START_NM"]), um_from_nm(config["SCAN_STOP_NM"]),
        float(step) * 1e-3, len(points)
    )


def parse_args(config):
    parser = argparse.ArgumentParser(description=config["PERTURBATION_NAME"])
    parser.add_argument("--mode", choices=["ask", "test", "full", "preview"], default=config.get("RUN_MODE_DEFAULT", "ask"))
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--max-points", type=int, default=None)
    parser.add_argument("--run-dir", default=None)
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
    note_path = run_dir / "结构状态说明.md"
    write_note(note_path, config, source_fsp, geometry, points, mode)

    print("源 FSP: {}".format(source_fsp))
    print("results 工作母版 FSP: {}".format(result_master))
    print("Lumerical 英文镜像母版 FSP: {}".format(ascii_master))
    print("输出批次目录: {}".format(run_dir))
    print("扰动: {}；降群路径: {}".format(config["PERTURBATION_NAME"], config["GROUP_PATH"]))
    print("当前用户修改区影响: {}".format(describe_scan(config, points)))
    if config.get("SIMULATION_TIME_S") is not None:
        print("单次仿真时间上限: {:.3f} ps；auto shutoff min: {}".format(float(config["SIMULATION_TIME_S"]) * 1e12, config.get("AUTO_SHUTOFF_MIN")))
    print("扫描计划已保存: {}".format(folders["plan"] / "scan_points.csv"))
    print("结构说明已保存: {}".format(note_path))

    if mode == "preview":
        print("预览模式结束：没有运行真实 FDTD。")
        return

    rows = []
    total_start = time.time()
    for idx, point in enumerate(points, 1):
        assert_source_unchanged(source_fsp, source_hash)
        paths = result_paths(folders, point)
        ascii_point = ascii_root / (point["name"] + ".fsp")
        shutil.copy2(str(ascii_master), str(ascii_point))
        value_text = "{:+.3f} deg".format(point["value_deg"]) if config.get("SCAN_UNIT") == "deg" else "{:.4f} um".format(point["value_nm"] / 1000.0)
        print("[{}/{}] 开始仿真：{}；{}={}".format(idx, len(points), point["name"], config["VALUE_NAME"], value_text))
        print("    剩余组数(含当前): {}/{}".format(len(points) - idx + 1, len(points)))
        start = time.time()
        fdtd = lumapi.FDTD(hide=True)
        try:
            fdtd.load(str(ascii_point))
            apply_point(fdtd, config, point)
            fdtd.save(str(ascii_point))
            fdtd.run()
            wavelength_m, transmission = extract_transmission(fdtd, config["T_MONITOR_NAME"])
            fdtd.save(str(ascii_point))
            shutil.copy2(str(ascii_point), str(paths["fsp"]))
            write_xlsx(paths["xlsx"], wavelength_m, transmission)
            save_abs2_plot(paths["png"], config, point, wavelength_m, transmission)
            summary = spectrum_summary(wavelength_m, transmission)
            elapsed = time.time() - start
            done = idx
            avg = (time.time() - total_start) / float(done)
            eta = avg * (len(points) - idx)
            print("    完成并保存，用时 {}；|T|^2 max={:.6g} @ {:.3f} nm，min={:.6g} @ {:.3f} nm；预计剩余 {}".format(
                format_duration(elapsed), summary["max"], summary["max_nm"], summary["min"], summary["min_nm"], format_duration(eta)
            ))
            rows.append({
                "index": point["index"], "name": point["name"], "status": "ok",
                "fsp": str(paths["fsp"]), "xlsx": str(paths["xlsx"]), "png": str(paths["png"]),
                "elapsed_s": "{:.3f}".format(elapsed),
                "max_abs2": summary["max"], "max_wavelength_nm": summary["max_nm"],
                "min_abs2": summary["min"], "min_wavelength_nm": summary["min_nm"],
            })
        finally:
            try:
                fdtd.close()
            except Exception:
                pass
        write_manifest(folders["logs"] / "manifest.csv", rows)

    print("全部完成。manifest: {}".format(folders["logs"] / "manifest.csv"))
