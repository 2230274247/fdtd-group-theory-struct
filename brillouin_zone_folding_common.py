# -*- coding: utf-8 -*-
"""
Brillouin-zone-folding FDTD supercell builder.

Implementation idea from the paper:
1. Keep the original source .fsp read-only.
2. Copy the source .fsp into each run folder as a master template.
3. Read the period from the substrate/FDTD region; the substrate x span is preferred.
4. Double the x-period to build a 2-cell supercell.
5. Place the primitive motif in a supercell baseline. For physical BZF perturbations,
   scan eta_nm so A/B subcells are no longer equivalent and the primitive period is broken.
6. Save one modified .fsp per scan point. Real simulation is optional and disabled by
   default because this entry is primarily a structure-generation step.
"""
from __future__ import print_function

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import time
import traceback
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

try:
    import numpy as np
except Exception:
    np = None


def nm(value_m):
    if np is not None:
        arr = np.asarray(value_m)
        out = arr * 1e9
        if out.ndim == 0:
            return float(out)
        return out
    return float(value_m) * 1e9


def m_from_nm(value_nm):
    return float(value_nm) * 1e-9


def format_duration(seconds):
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return "{:.1f} s".format(seconds)
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    if minutes < 60:
        return "{} min {} s".format(minutes, sec)
    return "{} h {} min {} s".format(minutes // 60, minutes % 60, sec)


def chinese_timestamp():
    now = datetime.now()
    return "{}年{}月{}日_{:02d}时{:02d}分{:02d}秒".format(now.year, now.month, now.day, now.hour, now.minute, now.second)


def safe_token(text):
    out = []
    for ch in str(text):
        out.append(ch if (ch.isalnum() or ch in "_-.+") else "_")
    return "".join(out).strip("_") or "item"


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_source_unchanged(source_fsp, expected_hash):
    current = file_sha256(source_fsp)
    if current != expected_hash:
        raise RuntimeError("源 FSP 已变化，停止运行以保护源文件：{}".format(source_fsp))


def frange(start, stop, step):
    if float(step) <= 0:
        raise ValueError("STEP_NM 必须大于 0")
    values = []
    current = float(start)
    guard = 0
    while current <= float(stop) + abs(float(step)) * 1e-9:
        values.append(round(current, 10))
        current += float(step)
        guard += 1
        if guard > 10000:
            raise RuntimeError("扫描点超过 10000，请检查 START_NM/END_NM/STEP_NM")
    if values and abs(values[-1] - float(stop)) > abs(float(step)) * 1e-6:
        values.append(float(stop))
    return values or [float(start)]


def import_lumapi(lumerical_root):
    api_dir = Path(lumerical_root) / "api" / "python"
    bin_dir = Path(lumerical_root) / "bin"
    for p in (api_dir, bin_dir):
        os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(p))
    lumapi_file = api_dir / "lumapi.py"
    if not lumapi_file.exists():
        raise RuntimeError("找不到 lumapi.py：{}".format(lumapi_file))
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
        raise RuntimeError("没有在 fsp 文件夹中找到 .fsp：{}".format(Path(structure_root) / "fsp"))
    return sorted(files, key=lambda p: (p.name, p.stat().st_mtime), reverse=True)[0]


def prepare_run_dir(structure_root, perturbation_name, mode, explicit_run_dir=None):
    root = Path(structure_root) / "results" / perturbation_name
    root.mkdir(parents=True, exist_ok=True)
    if explicit_run_dir:
        run_dir = Path(explicit_run_dir)
        if not run_dir.is_absolute():
            run_dir = root / run_dir
    else:
        run_dir = root / "run_{}_{}".format(mode, chinese_timestamp())
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def ensure_folders(run_dir):
    folders = {
        "plan": run_dir / "00_scan_plan",
        "fsp": run_dir / "01_supercell_fsp",
        "excel": run_dir / "02_transmission_excel",
        "png_abs2": run_dir / "03_transmission_abs2_png",
        "metrics": run_dir / "02_topology_metrics",
        "png": run_dir / "03_brillouin_folding_png",
        "logs": run_dir / "04_logs",
        "work": run_dir / "05_work_fsp",
        "html": run_dir / "06_report_html",
    }
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def build_scan_points(config, mode, max_points=None):
    values = frange(config["START_NM"], config["END_NM"], config["STEP_NM"])
    if mode == "test":
        values = values[:int(config.get("TEST_POINT_COUNT", 3))]
    if max_points is not None:
        values = values[:int(max_points)]
    scan_name = config.get("SCAN_PARAMETER_NAME", "eta_nm")
    points = []
    for i, eta_nm in enumerate(values):
        eta_nm = float(eta_nm)
        safe_scan = safe_token(scan_name.replace("_nm", ""))
        points.append({
            "index": i,
            "name": "{:04d}_BZF_{}_{:07.3f}nm".format(i, safe_scan, eta_nm),
            "scan_parameter_name": scan_name,
            "scan_parameter_value_nm": eta_nm,
            "eta_nm": eta_nm,
            "eta_m": m_from_nm(eta_nm),
            # Backward-compatible aliases for older viewers/controllers.
            "delta_L_nm": eta_nm,
            "delta_L_m": m_from_nm(eta_nm),
            "step_nm": float(config["STEP_NM"]),
        })
    return points
def write_csv(path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def ascii_work_root(config, run_dir):
    root = Path(config.get("ASCII_WORK_ROOT", r"H:\FDTD_CodeX\fdtd_ascii_work")) / "brillouin_zone_folding" / safe_token(config.get("STRUCTURE_CN_NAME", "structure")) / safe_token(run_dir.name)
    root.mkdir(parents=True, exist_ok=True)
    return root


def getnamed(fdtd, name, prop, index=None):
    if index is None:
        return fdtd.getnamed(name, prop)
    return fdtd.getnamed(name, prop, int(index))


def setnamed(fdtd, name, prop, value, index=None):
    if index is None:
        fdtd.setnamed(name, prop, value)
    else:
        fdtd.setnamed(name, prop, value, int(index))


def object_count(fdtd, name):
    try:
        return int(fdtd.getnamednumber(name))
    except Exception:
        return 0


def first_existing(fdtd, names):
    for name in names:
        if object_count(fdtd, name) > 0:
            return name
    return None


def read_scalar(fdtd, name, prop, default=None, index=None):
    try:
        return float(getnamed(fdtd, name, prop, index))
    except Exception:
        return default


def set_if_exists(fdtd, names, prop, value):
    changed = []
    for name in names:
        count = object_count(fdtd, name)
        for idx in range(1, count + 1):
            try:
                setnamed(fdtd, name, prop, value, idx if count > 1 else None)
                changed.append(name if count == 1 else "{}[{}]".format(name, idx))
            except Exception:
                pass
    return changed


def read_project_geometry(fdtd, config):
    substrate = first_existing(fdtd, config.get("SUBSTRATE_OBJECT_CANDIDATES", ()))
    fdtd_name = config.get("FDTD_OBJECT_NAME", "FDTD")
    fdtd_x_span = read_scalar(fdtd, fdtd_name, "x span")
    fdtd_y_span = read_scalar(fdtd, fdtd_name, "y span")
    fdtd_x = read_scalar(fdtd, fdtd_name, "x", 0.0)
    fdtd_y = read_scalar(fdtd, fdtd_name, "y", 0.0)
    sub_x_span = read_scalar(fdtd, substrate, "x span") if substrate else None
    sub_y_span = read_scalar(fdtd, substrate, "y span") if substrate else None
    sub_x = read_scalar(fdtd, substrate, "x", fdtd_x) if substrate else fdtd_x
    sub_y = read_scalar(fdtd, substrate, "y", fdtd_y) if substrate else fdtd_y
    period_x = sub_x_span or fdtd_x_span
    period_y = sub_y_span or fdtd_y_span
    if not period_x or not period_y:
        raise RuntimeError("无法从衬底或 FDTD 区域读取周期，请检查对象名。")
    motif = []
    for name in config.get("MOTIF_OBJECT_NAMES", ()):
        count = object_count(fdtd, name)
        if count <= 0:
            continue
        xs = []
        ys = []
        for idx in range(1, count + 1):
            xs.append(read_scalar(fdtd, name, "x", 0.0, idx if count > 1 else None))
            ys.append(read_scalar(fdtd, name, "y", 0.0, idx if count > 1 else None))
        motif.append({"name": name, "count": count, "x": xs, "y": ys})
    if not motif:
        raise RuntimeError("没有找到可复制的 motif 对象。请检查 MOTIF_OBJECT_NAMES。")
    return {
        "substrate": substrate,
        "fdtd": fdtd_name,
        "center_x": sub_x,
        "center_y": sub_y,
        "period_x_m": float(period_x),
        "period_y_m": float(period_y),
        "fdtd_x_span_m": float(fdtd_x_span or period_x),
        "fdtd_y_span_m": float(fdtd_y_span or period_y),
        "motif": motif,
    }


def move_named_objects(fdtd, motif, dx):
    for item in motif:
        name = item["name"]
        count = object_count(fdtd, name)
        for idx in range(1, count + 1):
            old_x = read_scalar(fdtd, name, "x", None, idx if count > 1 else None)
            if old_x is None:
                continue
            setnamed(fdtd, name, "x", old_x + dx, idx if count > 1 else None)


def copy_named_objects(fdtd, motif_names, dx):
    for name in motif_names:
        if object_count(fdtd, name) <= 0:
            continue
        script = 'select("{}"); copy({:.16e},0,0);'.format(name.replace('"', '\\"'), float(dx))
        fdtd.eval(script)



def bzf_strategy(config):
    return str(config.get("BZF_STRATEGY", "center_distance") or "center_distance").strip().lower()


def is_physical_bzf_perturbation(strategy, eta_nm):
    strategy = str(strategy or "").strip().lower()
    try:
        eta_nm = float(eta_nm)
    except Exception:
        eta_nm = 0.0
    if strategy == "simple_copy":
        return False
    return abs(eta_nm) > 1e-9


def configured_period_x_m(config, geometry):
    if config.get("PRIMITIVE_PERIOD_X_NM") is not None:
        return m_from_nm(config["PRIMITIVE_PERIOD_X_NM"])
    if config.get("PRIMITIVE_PERIOD_NM") is not None:
        return m_from_nm(config["PRIMITIVE_PERIOD_NM"])
    return float(geometry["period_x_m"])


def supercell_period_x_m(config, geometry):
    if config.get("SUPERCELL_PERIOD_X_NM") is not None:
        return m_from_nm(config["SUPERCELL_PERIOD_X_NM"])
    order = int(config.get("FOLDING_ORDER", config.get("SUPERCELL_ORDER", 2)) or 2)
    return configured_period_x_m(config, geometry) * float(order)


def default_span_object_candidates(config):
    names = []
    names.extend([config.get("FDTD_OBJECT_NAME", "FDTD")])
    names.extend(config.get("SUPER_CELL_SPAN_OBJECTS", ()))
    names.extend(config.get("SUBSTRATE_OBJECT_CANDIDATES", ()))
    names.extend(("source", "T", "R", "E", "monitor", "mesh", "mesh override", "mesh_override"))
    seen = []
    for name in names:
        if name and name not in seen:
            seen.append(name)
    return tuple(seen)


def set_supercell_spans(fdtd, config, geometry, super_x, period_y):
    warnings = []
    span_status = {}
    for name in default_span_object_candidates(config):
        count = object_count(fdtd, name)
        if count <= 0:
            warnings.append("missing span object: {}".format(name))
            span_status["{}_exists".format(name)] = False
            continue
        span_status["{}_exists".format(name)] = True
        for idx in range(1, count + 1):
            index = idx if count > 1 else None
            label = name if count == 1 else "{}[{}]".format(name, idx)
            try:
                setnamed(fdtd, name, "x", geometry["center_x"], index)
                setnamed(fdtd, name, "x span", super_x, index)
                span_status["{}_x_span_nm".format(label)] = nm(read_scalar(fdtd, name, "x span", super_x, index))
            except Exception as exc:
                warnings.append("{} x span warning: {}".format(label, exc))
            try:
                setnamed(fdtd, name, "y", geometry["center_y"], index)
                setnamed(fdtd, name, "y span", period_y, index)
            except Exception:
                pass
    return warnings, span_status


def bzf_dual_disk_positions_nm(config, eta_nm):
    L = float(config.get("L_NM", 450.0))
    base_delta = float(config.get("BASE_DELTA_NM", 180.0))
    eta = float(eta_nm)
    return [-L - (base_delta + eta), -L + (base_delta + eta), +L - (base_delta - eta), +L + (base_delta - eta)]


def safe_lsf_name(name):
    return str(name).replace('\\', '\\\\').replace('"', '\\"')


def rename_object(fdtd, old_name, new_name):
    if old_name == new_name:
        return new_name
    try:
        setnamed(fdtd, old_name, "name", new_name)
        return new_name
    except Exception:
        try:
            fdtd.eval('select("{}"); set("name","{}");'.format(safe_lsf_name(old_name), safe_lsf_name(new_name)))
            return new_name
        except Exception:
            return old_name


def duplicate_object(fdtd, source_name, new_name):
    fdtd.eval('select("{}"); copy(0,0,0); set("name","{}");'.format(safe_lsf_name(source_name), safe_lsf_name(new_name)))
    return new_name


def ensure_dual_disk_objects(fdtd, config):
    desired = tuple(config.get("BZF_OBJECT_NAMES", ("Si_disk_1", "Si_disk_2", "Si_disk_3", "Si_disk_4")))
    if all(object_count(fdtd, name) > 0 for name in desired):
        return list(desired), []
    warnings = []
    templates = []
    base_names = tuple(config.get("MOTIF_OBJECT_NAMES", ("Si_disk",)))
    tmp_prefix = "__bzf_tmp_disk_{}".format(int(time.time() * 1000) % 1000000)
    for base in base_names:
        count = object_count(fdtd, base)
        if count <= 0:
            continue
        if count == 1:
            tmp = tmp_prefix + "_{:02d}".format(len(templates) + 1)
            templates.append(rename_object(fdtd, base, tmp))
        else:
            for idx in range(count, 0, -1):
                tmp = tmp_prefix + "_{:02d}".format(len(templates) + 1)
                try:
                    setnamed(fdtd, base, "name", tmp, idx)
                    templates.append(tmp)
                except Exception as exc:
                    warnings.append("rename {}[{}] failed: {}".format(base, idx, exc))
    if not templates:
        raise RuntimeError("BZF copy_then_eta_break could not find motif objects: {}".format(base_names))
    templates = sorted(templates, key=lambda name: read_scalar(fdtd, name, "x", 0.0))
    seed = list(templates)
    while len(templates) < len(desired):
        src = seed[(len(templates) - len(seed)) % len(seed)]
        tmp = tmp_prefix + "_{:02d}".format(len(templates) + 1)
        templates.append(duplicate_object(fdtd, src, tmp))
    templates = sorted(templates[:len(desired)], key=lambda name: read_scalar(fdtd, name, "x", 0.0))
    final = []
    for idx, src in enumerate(templates):
        final.append(rename_object(fdtd, src, desired[idx]))
    return final, warnings


def apply_copy_then_eta_break(fdtd, config, point, geometry, super_x, period_x, period_y):
    eta_nm = float(point["eta_nm"])
    names, warnings = ensure_dual_disk_objects(fdtd, config)
    positions_nm = bzf_dual_disk_positions_nm(config, eta_nm)
    radius_nm = float(config.get("DISK_RADIUS_NM", 145.0))
    height_nm = config.get("DISK_HEIGHT_NM")
    for name, x_nm in zip(names, positions_nm):
        setnamed(fdtd, name, "x", m_from_nm(x_nm))
        setnamed(fdtd, name, "y", geometry["center_y"])
        try:
            setnamed(fdtd, name, "radius", m_from_nm(radius_nm))
        except Exception:
            pass
        if height_nm is not None:
            try:
                setnamed(fdtd, name, "z span", m_from_nm(height_nm))
            except Exception:
                pass
    xs = sorted(float(x) for x in positions_nm)
    center_distances = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    edge_gaps = [d - 2.0 * radius_nm for d in center_distances]
    return {
        "strategy": "copy_then_eta_break",
        "motif_objects": ";".join(names),
        "object_x_nm_after": ";".join("{:.6g}".format(x) for x in xs),
        "x_positions_nm": ";".join("{:.6g}".format(x) for x in xs),
        "center_distances_nm": ";".join("{:.6g}".format(x) for x in center_distances),
        "edge_gaps_nm": ";".join("{:.6g}".format(x) for x in edge_gaps),
        "min_gap_nm": min(edge_gaps) if edge_gaps else "",
        "max_abs_x_nm": max(abs(x) for x in xs) if xs else "",
        "disk_radius_nm": radius_nm,
        "primitive_period_preserved": abs(eta_nm) < 1e-9,
        "physical_bzf_perturbation": is_physical_bzf_perturbation("copy_then_eta_break", eta_nm),
        "warnings": "; ".join(warnings),
    }


def custom_positions_nm(config, point, geometry):
    eta_nm = float(point.get("eta_nm", 0.0))
    fn = config.get("CUSTOM_POSITION_FN")
    if callable(fn):
        return [float(x) for x in fn(eta_nm, config, geometry)]
    positions = config.get("CUSTOM_POSITIONS_NM") or config.get("CUSTOM_X_POSITIONS_NM")
    if positions:
        return [float(x) for x in positions]
    base = config.get("BASE_X_POSITIONS_NM")
    signs = config.get("ETA_SIGNS")
    if base and signs:
        return [float(x) + float(s) * eta_nm for x, s in zip(base, signs)]
    raise ValueError("BZF_STRATEGY='custom_positions' requires CUSTOM_POSITION_FN, CUSTOM_POSITIONS_NM, or BASE_X_POSITIONS_NM + ETA_SIGNS")


def ensure_position_objects(fdtd, config, count):
    desired = tuple(config.get("BZF_OBJECT_NAMES", tuple("BZF_obj_{:02d}".format(i + 1) for i in range(count))))
    if len(desired) < count:
        desired = tuple(list(desired) + ["BZF_obj_{:02d}".format(i + 1) for i in range(len(desired), count)])
    if all(object_count(fdtd, name) > 0 for name in desired[:count]):
        return list(desired[:count]), []
    names, warnings = ensure_dual_disk_objects(fdtd, {**config, "BZF_OBJECT_NAMES": desired[:count]})
    return names[:count], warnings


def apply_custom_positions(fdtd, config, point, geometry, super_x):
    eta_nm = float(point.get("eta_nm", 0.0))
    positions_nm = custom_positions_nm(config, point, geometry)
    names, warnings = ensure_position_objects(fdtd, config, len(positions_nm))
    radius_nm = float(config.get("DISK_RADIUS_NM", config.get("MOTIF_RADIUS_NM", 0.0)) or 0.0)
    for name, x_nm in zip(names, positions_nm):
        setnamed(fdtd, name, "x", m_from_nm(x_nm))
        try:
            setnamed(fdtd, name, "y", geometry["center_y"])
        except Exception:
            pass
    xs = sorted(float(x) for x in positions_nm)
    center_distances = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    edge_gaps = [d - 2.0 * radius_nm for d in center_distances] if radius_nm else []
    return {
        "strategy": "custom_positions",
        "motif_objects": ";".join(names),
        "object_x_nm_after": ";".join("{:.6g}".format(x) for x in xs),
        "x_positions_nm": ";".join("{:.6g}".format(x) for x in xs),
        "center_distances_nm": ";".join("{:.6g}".format(x) for x in center_distances),
        "edge_gaps_nm": ";".join("{:.6g}".format(x) for x in edge_gaps),
        "min_gap_nm": min(edge_gaps) if edge_gaps else "",
        "max_abs_x_nm": max(abs(x) for x in xs) if xs else "",
        "primitive_period_preserved": abs(eta_nm) < 1e-9,
        "physical_bzf_perturbation": is_physical_bzf_perturbation("custom_positions", eta_nm),
        "warnings": "; ".join(warnings),
    }


def validate_bzf_geometry(config, metrics, span_status=None):
    span_status = span_status or {}
    super_nm = float(metrics.get("supercell_period_x_nm") or 0.0)
    radius_nm = float(config.get("DISK_RADIUS_NM", metrics.get("disk_radius_nm") or 0.0) or 0.0)
    xs = []
    for raw in str(metrics.get("x_positions_nm", "")).split(";"):
        try:
            xs.append(float(raw))
        except Exception:
            pass
    gaps = []
    for raw in str(metrics.get("edge_gaps_nm", "")).split(";"):
        try:
            gaps.append(float(raw))
        except Exception:
            pass
    boundary_ok = True
    if super_nm and radius_nm and xs:
        boundary_ok = all(abs(x) + radius_nm <= super_nm / 2.0 + 1e-6 for x in xs)
    overlap_ok = all(g > 0 for g in gaps) if gaps else True
    expected_span = super_nm
    span_ok_flags = []
    for key, value in span_status.items():
        if key.endswith("_x_span_nm"):
            try:
                span_ok_flags.append(abs(float(value) - expected_span) <= max(1e-6, expected_span * 1e-6))
            except Exception:
                pass
    span_ok = all(span_ok_flags) if span_ok_flags else None
    fatal = []
    if not boundary_ok:
        fatal.append("motif_out_of_supercell")
    if not overlap_ok:
        fatal.append("motif_overlap_or_nonpositive_gap")
    return {"geometry_validation_status": "fatal" if fatal else ("ok" if span_ok is not False else "warning"), "boundary_ok": boundary_ok, "overlap_ok": overlap_ok, "span_ok": span_ok if span_ok is not None else "unknown", "fatal": ";".join(fatal)}


def estimate_spectrum_features(wavelength_m, transmission):
    summary = spectrum_summary(wavelength_m, transmission)
    if np is None:
        return summary
    wl_nm = np.asarray(nm(wavelength_m), dtype=float).reshape(-1)
    y = abs2(transmission).reshape(-1)
    if wl_nm.size < 5 or y.size < 5:
        summary.update({"peak_count": 0, "main_peak_nm": summary.get("max_nm"), "main_peak_T": summary.get("max"), "fwhm_nm_est": None, "q_est": None})
        return summary
    peak_count = sum(1 for i in range(1, len(y) - 1) if y[i] >= y[i - 1] and y[i] >= y[i + 1])
    imax = int(np.argmax(y))
    baseline = float(min(y[0], y[-1], np.min(y)))
    half = baseline + (float(y[imax]) - baseline) / 2.0
    crossings = []
    for i in range(len(y) - 1):
        y0, y1 = float(y[i]), float(y[i + 1])
        if (y0 - half) * (y1 - half) < 0:
            ratio = (half - y0) / (y1 - y0)
            crossings.append(float(wl_nm[i] + ratio * (wl_nm[i + 1] - wl_nm[i])))
    left = [x for x in crossings if x < wl_nm[imax]]
    right = [x for x in crossings if x > wl_nm[imax]]
    fwhm = abs(right[0] - left[-1]) if left and right else None
    q = float(wl_nm[imax] / fwhm) if fwhm and fwhm > 0 else None
    summary.update({"peak_count": peak_count, "main_peak_nm": float(wl_nm[imax]), "main_peak_T": float(y[imax]), "fwhm_nm_est": fwhm, "q_est": q})
    return summary


def save_point_geometry_plot(path, config, point, metrics):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    xs = []
    for raw in str(metrics.get("x_positions_nm", "")).split(";"):
        try:
            xs.append(float(raw))
        except Exception:
            pass
    if not xs:
        return None
    super_nm = float(metrics.get("supercell_period_x_nm") or config.get("SUPERCELL_PERIOD_X_NM") or 0.0)
    primitive_nm = float(metrics.get("primitive_period_x_nm") or config.get("PRIMITIVE_PERIOD_X_NM") or super_nm / 2.0)
    radius_nm = float(config.get("DISK_RADIUS_NM", metrics.get("disk_radius_nm") or 20.0) or 20.0)
    fig, ax = plt.subplots(figsize=(8.4, 2.8), dpi=150)
    ax.axvspan(-super_nm / 2.0, super_nm / 2.0, color="#e0f2f1", alpha=0.45)
    for x in (-primitive_nm / 2.0, primitive_nm / 2.0):
        ax.axvline(x, color="#334155", linestyle="--", linewidth=1.0)
    ax.axvline(-super_nm / 2.0, color="#0f766e", linewidth=1.5)
    ax.axvline(super_nm / 2.0, color="#0f766e", linewidth=1.5)
    for i, x in enumerate(xs, 1):
        circle = plt.Circle((x, 0), radius_nm, edgecolor="#0f766e", facecolor="#99f6e4", alpha=0.75, linewidth=1.2)
        ax.add_patch(circle)
        ax.text(x, 0, str(i), ha="center", va="center", fontsize=9, weight="bold")
    ax.set_xlim(-super_nm / 2.0 - 80, super_nm / 2.0 + 80)
    ax.set_ylim(-max(radius_nm * 1.8, 120), max(radius_nm * 1.8, 120))
    ax.set_xlabel("x (nm)")
    ax.set_yticks([])
    ax.set_title("BZF point {}: eta={:.3f} nm | primitive preserved={}".format(point.get("index"), float(point.get("eta_nm", 0.0)), metrics.get("primitive_period_preserved")))
    ax.grid(True, axis="x", alpha=0.22)
    fig.tight_layout()
    fig.savefig(str(path))
    plt.close(fig)
    return path

def apply_bzf_supercell(fdtd, config, point, geometry):
    fdtd.switchtolayout()
    fdtd_name = config.get("FDTD_OBJECT_NAME", "FDTD")
    if config.get("SIMULATION_TIME_S") is not None:
        set_if_exists(fdtd, (fdtd_name,), "simulation time", float(config["SIMULATION_TIME_S"]))
    if config.get("AUTO_SHUTOFF_MIN") is not None:
        set_if_exists(fdtd, (fdtd_name,), "auto shutoff min", float(config["AUTO_SHUTOFF_MIN"]))
    if config.get("MESH_ACCURACY") is not None:
        set_if_exists(fdtd, (fdtd_name,), "mesh accuracy", int(float(config["MESH_ACCURACY"])))
    if config.get("DT_STABILITY_FACTOR") is not None:
        set_if_exists(fdtd, (fdtd_name,), "dt stability factor", float(config["DT_STABILITY_FACTOR"]))

    period_x = configured_period_x_m(config, geometry)
    period_y = geometry["period_y_m"]
    super_x = supercell_period_x_m(config, geometry)
    order = float(super_x) / float(period_x) if period_x else float(config.get("FOLDING_ORDER", 2) or 2)
    strategy = bzf_strategy(config)
    span_warnings, span_status = set_supercell_spans(fdtd, config, geometry, super_x, period_y)
    for prop, value in (("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic")):
        try:
            set_if_exists(fdtd, (fdtd_name,), prop, value)
        except Exception:
            pass

    metrics = {
        "bzf_strategy": strategy,
        "scan_parameter_name": config.get("SCAN_PARAMETER_NAME", "eta_nm"),
        "scan_parameter_value_nm": float(point.get("eta_nm", point.get("delta_L_nm", 0.0))),
        "eta_nm": float(point.get("eta_nm", point.get("delta_L_nm", 0.0))),
        "primitive_period_x_nm": nm(period_x),
        "supercell_period_x_nm": nm(super_x),
        "folding_order": order,
        "period_y_nm": nm(period_y),
        "span_warnings": "; ".join(span_warnings),
    }
    metrics.update(span_status)

    if strategy == "copy_then_eta_break":
        metrics.update(apply_copy_then_eta_break(fdtd, config, point, geometry, super_x, period_x, period_y))
    elif strategy == "custom_positions":
        metrics.update(apply_custom_positions(fdtd, config, point, geometry, super_x))
    else:
        if strategy not in ("simple_copy", "center_distance"):
            raise ValueError("Unsupported BZF_STRATEGY '{}'. Use simple_copy, center_distance, copy_then_eta_break, or custom_positions.".format(strategy))
        delta_l = 0.0 if strategy == "simple_copy" else float(point.get("delta_L_m", 0.0))
        center_distance = period_x - delta_l
        if center_distance <= 0:
            raise ValueError("eta/deltaL too large: primitive period {:.3f} nm, value {:.3f} nm".format(nm(period_x), point.get("eta_nm", point.get("delta_L_nm", 0))))
        motif = geometry["motif"]
        motif_names = [m["name"] for m in motif]
        left_shift = -0.5 * center_distance
        move_named_objects(fdtd, motif, left_shift)
        copy_named_objects(fdtd, motif_names, center_distance)
        primitive_preserved = abs(float(point.get("eta_nm", 0.0))) < 1e-9 or strategy == "simple_copy"
        metrics.update({
            "strategy": strategy,
            "delta_L_nm": float(point.get("delta_L_nm", 0.0)),
            "cell_center_distance_nm": nm(center_distance),
            "left_shift_nm": nm(left_shift),
            "right_copy_shift_nm": nm(center_distance),
            "motif_objects": ";".join(motif_names),
            "primitive_period_preserved": primitive_preserved,
            "physical_bzf_perturbation": is_physical_bzf_perturbation(strategy, point.get("eta_nm", 0.0)),
        })
    metrics.update(validate_bzf_geometry(config, metrics, span_status))
    return metrics
def save_supercell_sketch(path, rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    xs = []
    ds = []
    for r in rows:
        if r.get("status") == "failed":
            continue
        try:
            xs.append(float(r.get("eta_nm", r.get("delta_L_nm", 0.0))))
            raw = r.get("cell_center_distance_nm")
            if raw in (None, ""):
                distances = [float(v) for v in str(r.get("center_distances_nm", "")).split(";") if v not in ("", None)]
                raw = min(distances) if distances else 0.0
            ds.append(float(raw))
        except Exception:
            pass
    if not xs or not ds:
        return None
    fig, ax = plt.subplots(figsize=(7.4, 4.2), dpi=150)
    ax.plot(xs, ds, marker="o", color="#0c7c70")
    ax.set_xlabel("BZF perturbation eta (nm)")
    ax.set_ylabel("representative center distance (nm)")
    ax.set_title("BZF supercell geometry trend")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(str(path))
    plt.close(fig)
    return path

def extract_transmission(fdtd, monitor_name):
    if np is None:
        raise RuntimeError("需要 numpy 才能整理透射谱。")
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
    if np is None:
        return []
    return np.abs(np.asarray(values)) ** 2


def spectrum_summary(wavelength_m, transmission):
    t = abs2(transmission)
    if getattr(t, "size", 0) == 0:
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
        return None
    fig, ax = plt.subplots(figsize=(8.6, 5.2), dpi=160)
    ax.plot(nm(wavelength_m), abs2(transmission), color="#1f77b4", linewidth=1.7)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("|T|^2")
    ax.set_title("{} - {}".format(config.get("PERTURBATION_NAME", "BZF"), point["name"]))
    ax.grid(True, alpha=0.28)
    ax.text(0.03, 0.97, "eta = {:.3f} nm".format(float(point.get("eta_nm", point.get("delta_L_nm", 0.0)))), transform=ax.transAxes, va="top", ha="left", fontsize=8, bbox=dict(facecolor="white", alpha=0.82, edgecolor="#dddddd"))
    fig.tight_layout()
    fig.savefig(str(path))
    plt.close(fig)
    return path


def result_paths(folders, point):
    return {
        "fsp": folders["fsp"] / (point["name"] + ".fsp"),
        "xlsx": folders["excel"] / (point["name"] + "_transmission_abs2.xlsx"),
        "png": folders["png_abs2"] / (point["name"] + "_transmission_abs2.png"),
    }


def write_note(run_dir, config, source_fsp, geometry, rows):
    lines = [
        "# 布里渊区折叠脚本实现说明",
        "",
        "## 这版代码具体做了什么",
        "",
        "1. 保护 `fsp` 目录下的源 `.fsp`：只读取 SHA256，不直接保存回源文件。",
        "2. 每次运行把源 `.fsp` 复制到本次 `run_*\\05_work_fsp\\master_template.fsp`，作为母文件。",
        "3. 每个 delta L 扫描点都从母文件再复制一个工作 `.fsp`，只修改该工作副本。",
        "4. 优先读取衬底对象的 `x span/y span` 作为原始周期 `Lx/Ly`；如果衬底不存在，就退回读取 FDTD 区域。",
        "5. 把 FDTD、衬底、source、T 等大范围对象的 `x span` 改成 `2Lx`，`y span` 保持 `Ly`。",
        "6. 把 resonator motif 先整体移动到 `-0.5*(Lx-deltaL)`，再复制一份到右侧，形成两个 cell 的超胞。",
        "7. `test/full` 会继续运行 FDTD，读取 `T` monitor，并输出透射谱 Excel/PNG；`--structure-only` 才只保存 `.fsp`。",
        "",
        "## 和论文图示的对应",
        "",
        "- 原始周期：`L = ax`，通常由衬底尺寸决定。",
        "- 折叠后周期：`ax -> 2ax`，即 x 方向 Brillouin zone 减半，X/M 折叠到新的高对称点。",
        "- gap perturbation：同一超胞内两个 motif 的中心距从 `L` 改为 `L - deltaL`。",
        "- 这一步只生成结构和后续仿真输入，真正的拓扑荷需要继续做远场偏振/相位绕数验证。",
        "",
        "## 当前结构读取结果",
        "",
        "- 源文件：{}".format(source_fsp),
        "- 衬底对象：{}".format(geometry.get("substrate")),
        "- 原始 Lx：{:.3f} nm".format(nm(geometry["period_x_m"])),
        "- 原始 Ly：{:.3f} nm".format(nm(geometry["period_y_m"])),
        "- motif 对象：{}".format(", ".join(m["name"] for m in geometry["motif"])),
        "",
        "## 输出结果",
        "",
        "- `00_scan_plan/scan_points.csv`：delta L 扫描计划。",
        "- `01_supercell_fsp/*.fsp`：最终保存的双 cell 超胞 FSP。",
        "- `02_topology_metrics/bzf_supercell_metrics.csv`：每个扫描点对应的 L、2L、L-deltaL。",
        "- `02_transmission_excel/*.xlsx`：真实仿真后的透射谱数据。",
        "- `03_transmission_abs2_png/*.png`：真实仿真后的 |T|^2 谱图。",
        "- `04_logs/manifest.csv`：总控/网页可识别的运行记录。",
    ]
    Path(run_dir, "布里渊区折叠_脚本实现说明.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(config):
    parser = argparse.ArgumentParser(description=config.get("PERTURBATION_NAME", "布里渊区折叠"))
    parser.add_argument("--mode", choices=["ask", "preview", "test", "full"], default=config.get("RUN_MODE_DEFAULT", "ask"))
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--max-points", type=int, default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--structure-only", action="store_true", help="只生成 2-cell 超胞 FSP，不运行真实 FDTD 仿真")
    args = parser.parse_args()
    args.prompted_mode = False
    if args.preview:
        args.mode = "preview"
    if args.test:
        args.mode = "test"
    if args.full:
        args.mode = "full"
    if args.mode == "ask":
        args.prompted_mode = True
        print("请选择 {} / 布里渊区折叠 的运行模式：".format(config.get("STRUCTURE_CN_NAME", "结构")))
        print("  1 = preview：只生成扫描计划，不打开 FDTD")
        print("  2 = test：真实仿真前 {} 个 delta L 超胞点".format(config.get("TEST_POINT_COUNT", 3)))
        print("  3 = full：真实仿真全部 delta L 超胞点")
        choice = input("请输入 1/2/3：").strip()
        args.mode = {"1": "preview", "2": "test", "3": "full"}.get(choice)
        if args.mode is None:
            raise ValueError("只能输入 1/2/3")
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
    if args.mode in ("test", "full") and getattr(args, "prompted_mode", False):
        maybe_ask_fdtd_runtime_overrides(config)
    structure_only = bool(args.structure_only or config.get("STRUCTURE_ONLY", False))
    structure_root = Path(config["STRUCTURE_ROOT"])
    source_fsp = find_source_fsp(structure_root)
    source_hash = file_sha256(source_fsp)
    run_dir = prepare_run_dir(structure_root, config.get("PERTURBATION_NAME", "??????"), args.mode, args.run_dir)
    folders = ensure_folders(run_dir)
    points = build_scan_points(config, args.mode, args.max_points)
    write_csv(folders["plan"] / "scan_points.csv", points)
    created_at = datetime.now().isoformat(timespec="seconds")
    run_id = run_dir.name
    geometry_validation_file = str(folders["logs"] / "geometry_validation.csv")
    common_manifest = {
        "structure_name": config.get("STRUCTURE_CN_NAME", ""),
        "run_id": run_id,
        "strategy": bzf_strategy(config),
        "bzf_strategy": bzf_strategy(config),
        "source_fsp": str(source_fsp),
        "source_fsp_sha256": source_hash,
        "output_dir": str(run_dir),
        "max_point_walltime_s": config.get("MAX_POINT_WALLTIME_S", ""),
        "geometry_validation_file": geometry_validation_file,
        "created_at": created_at,
    }

    if args.mode == "preview":
        rows = []
        validation_rows = []
        for p in points:
            row = dict(p)
            row.update({
                **common_manifest,
                "status": "preview_only",
                "parameters": json.dumps(p, ensure_ascii=False, sort_keys=True),
                "scan_parameter_name": config.get("SCAN_PARAMETER_NAME", "eta_nm"),
                "primitive_period_x_nm": config.get("PRIMITIVE_PERIOD_X_NM", ""),
                "supercell_period_x_nm": config.get("SUPERCELL_PERIOD_X_NM", ""),
                "walltime_s": 0,
                "error_message": "",
                "traceback_file": "",
            })
            rows.append(row)
            validation_rows.append({
                "index": p.get("index", ""),
                "name": p.get("name", ""),
                "eta_nm": p.get("eta_nm", ""),
                "status": "preview_only",
                "geometry_validation_status": "not_run_preview",
                "geometry_validation_file": geometry_validation_file,
            })
        write_csv(folders["logs"] / "manifest.csv", rows)
        write_csv(folders["logs"] / "geometry_validation.csv", validation_rows)
        print("preview completed: scan plan only, no FDTD opened: {}".format(run_dir))
        return

    master_template = folders["work"] / "master_template.fsp"
    shutil.copy2(str(source_fsp), str(master_template))
    source_copy = folders["fsp"] / "source_readonly_copy.fsp"
    shutil.copy2(str(source_fsp), str(source_copy))
    ascii_root = ascii_work_root(config, run_dir)
    ascii_master = ascii_root / "master_template.fsp"
    shutil.copy2(str(source_fsp), str(ascii_master))

    lumapi = import_lumapi(config.get("LUMERICAL_ROOT", r"D:\Program Files\Lumerical\v202"))
    fdtd = lumapi.FDTD(hide=not bool(args.show_gui))
    try:
        fdtd.load(str(ascii_master))
        geometry = read_project_geometry(fdtd, config)
    finally:
        try:
            fdtd.close()
        except Exception:
            pass

    metric_rows = []
    manifest_rows = []
    validation_rows = []
    total_start = time.time()
    monitor_name = config.get("T_MONITOR_NAME", "T")
    print("Source FSP: {}".format(source_fsp))
    print("Run master template copy: {}".format(master_template))
    print("Lumerical ASCII master: {}".format(ascii_master))
    print("Output run directory: {}".format(run_dir))
    print("BZF strategy: {}; scan parameter: {}; mode: {}; structure_only: {}".format(
        bzf_strategy(config), config.get("SCAN_PARAMETER_NAME", "eta_nm"), args.mode, structure_only
    ))
    if config.get("SIMULATION_TIME_S") is not None:
        print("Single simulation time limit: {:.3f} ps; auto shutoff min: {}".format(float(config["SIMULATION_TIME_S"]) * 1e12, config.get("AUTO_SHUTOFF_MIN")))

    for idx, point in enumerate(points, 1):
        work_fsp = ascii_root / (point["name"] + "_work.fsp")
        paths = result_paths(folders, point)
        row = dict(point)
        manifest = {
            **common_manifest,
            "index": point["index"],
            "name": point["name"],
            "run_mode": args.mode,
            "structure_only": structure_only,
            "parameters": json.dumps(point, ensure_ascii=False, sort_keys=True),
            "scan_parameter_name": config.get("SCAN_PARAMETER_NAME", "eta_nm"),
            "scan_parameter_value_nm": point.get("eta_nm", ""),
            "eta_nm": point.get("eta_nm", ""),
            "step_nm": point.get("step_nm", ""),
            "status": "",
            "error_message": "",
            "traceback_file": "",
        }
        t0 = time.time()
        fdtd = None
        print("[{}/{}] start BZF point: {}; eta={:.3f} nm".format(idx, len(points), point["name"], float(point.get("eta_nm", 0.0))))
        try:
            assert_source_unchanged(source_fsp, source_hash)
            shutil.copy2(str(ascii_master), str(work_fsp))
            fdtd = lumapi.FDTD(hide=not bool(args.show_gui))
            fdtd.load(str(work_fsp))
            metrics = apply_bzf_supercell(fdtd, config, point, geometry)
            fdtd.save(str(work_fsp))
            shutil.copy2(str(work_fsp), str(paths["fsp"]))
            metrics["fsp"] = str(paths["fsp"])
            geometry_png = folders["png"] / (point["name"] + "_geometry_topview.png")
            if save_point_geometry_plot(geometry_png, config, point, metrics):
                metrics["geometry_png"] = str(geometry_png)
            if not structure_only:
                fdtd.run()
                wavelength_m, transmission = extract_transmission(fdtd, monitor_name)
                fdtd.save(str(work_fsp))
                shutil.copy2(str(work_fsp), str(paths["fsp"]))
                write_xlsx(paths["xlsx"], wavelength_m, transmission)
                save_abs2_plot(paths["png"], config, point, wavelength_m, transmission)
                summary = estimate_spectrum_features(wavelength_m, transmission)
                metrics.update({
                    "xlsx": str(paths["xlsx"]),
                    "png": str(paths["png"]),
                    "max_abs2": summary.get("max"),
                    "max_wavelength_nm": summary.get("max_nm"),
                    "min_abs2": summary.get("min"),
                    "min_wavelength_nm": summary.get("min_nm"),
                    "peak_count": summary.get("peak_count"),
                    "main_peak_nm": summary.get("main_peak_nm"),
                    "main_peak_T": summary.get("main_peak_T"),
                    "fwhm_nm_est": summary.get("fwhm_nm_est"),
                    "q_est": summary.get("q_est"),
                    "is_unconverged": bool(summary.get("max") is not None and summary.get("max") > 1.0),
                })
            elapsed = round(time.time() - t0, 3)
            max_wall = config.get("MAX_POINT_WALLTIME_S")
            timeout = bool(max_wall and elapsed > float(max_wall))
            status = "built_supercell_fsp" if structure_only else "ok"
            if timeout:
                status = "timeout_warning"
            row.update(metrics)
            row.update({"status": status, "elapsed_s": elapsed, "python_elapsed_s": elapsed, "walltime_s": elapsed, "timeout": timeout})
            manifest.update(row)
            avg = (time.time() - total_start) / float(idx)
            eta = avg * (len(points) - idx)
            print("    saved; elapsed {}; estimated remaining {}".format(format_duration(elapsed), format_duration(eta)))
        except Exception as exc:
            elapsed = round(time.time() - t0, 3)
            tb_path = folders["logs"] / (point["name"] + "_traceback.txt")
            tb_path.write_text(traceback.format_exc(), encoding="utf-8")
            row.update({
                "status": "failed",
                "elapsed_s": elapsed,
                "python_elapsed_s": elapsed,
                "walltime_s": elapsed,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback_file": str(tb_path),
            })
            manifest.update(row)
            print("    FAILED but continuing: {}: {}".format(type(exc).__name__, exc))
            print("    traceback: {}".format(tb_path))
        finally:
            try:
                if fdtd is not None:
                    fdtd.close()
            except Exception:
                pass
        metric_rows.append(row)
        validation_rows.append({k: row.get(k, "") for k in (
            "index", "name", "eta_nm", "primitive_period_x_nm", "supercell_period_x_nm",
            "primitive_period_preserved", "physical_bzf_perturbation", "min_gap_nm", "max_abs_x_nm", "boundary_ok",
            "overlap_ok", "span_ok", "geometry_validation_status", "fatal", "span_warnings",
            "warnings", "status", "error_type", "error_message"
        )})
        manifest_rows.append(manifest)
        write_csv(folders["logs"] / "manifest.csv", manifest_rows)
        write_csv(folders["logs"] / "geometry_validation.csv", validation_rows)

    write_csv(folders["metrics"] / "bzf_supercell_metrics.csv", metric_rows)
    save_supercell_sketch(folders["png"] / "bzf_eta_center_distance.png", metric_rows)
    write_note(run_dir, config, source_fsp, geometry, metric_rows)
    print("All done. manifest: {}".format(folders["logs"] / "manifest.csv"))
    print("BZF results: {}".format(run_dir))
    print("Master template copy: {}".format(master_template))
    print("Supercell FSP: {}".format(folders["fsp"]))
