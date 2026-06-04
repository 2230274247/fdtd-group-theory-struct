# -*- coding: utf-8 -*-
"""Build and test a mirror-symmetric DBR defect cavity bandpass filter."""
from __future__ import print_function

import argparse
import csv
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
import zipfile

import numpy as np


NM = 1e-9
UM = 1e-6
C0 = 299792458.0

STRUCTURE_ROOT = Path(__file__).resolve().parents[2]
STRUCTURE_NAME = "Cinf_DBR_defect_cavity"
SEED_FSP_NAME = "cinf_dbr_defect_cavity_seed.fsp"
LUMERICAL_ROOT = Path(r"D:\Program Files\Lumerical\v202")
SIM_LOCK_NAME = ".fdtd_single_simulation.lock"
FDTD_PROCESS_NAMES = ("fdtd-solutions", "fdtd-engine", "fdtd-run-local", "lumerical")

TARGETS = {
    "peak_abs2_min": 0.85,
    "peak_abs2_max": 1.0,
    "offband_p95_max": 0.03,
    "offband_max_max": 0.05,
    "side_peak_threshold_abs2": 0.10,
    "side_peak_count_max": 0,
    "fwhm_max_nm": 8.0,
    "contrast_min": 30.0,
    "edge_margin_nm": 0.15,
}

BASE_CONFIG = {
    "target_lambda_nm": 1310.6,
    "lambda_start_nm": 1309.0,
    "lambda_stop_nm": 1311.0,
    "period_nm": 700.0,
    "n_high": 3.48,
    "n_low": 1.45,
    "n_cavity": 1.45,
    "mirror_pairs": 14,
    "chirp_start_nm": 1310.0,
    "chirp_stop_nm": 1310.0,
    "cavity_length_multiplier": 0.7,
    "frequency_points": 1001,
    "simulation_time_fs": 80000.0,
    "mesh_accuracy": 2,
    "dt_stability_factor": 0.99,
    "auto_shutoff_min": 1e-8,
    "auto_shutoff_max": 100000,
    "down_sample_time": 100,
    "min_mesh_step_um": 0.00025,
    "max_source_time_signal_length": 32768,
    "background_index": 1.0,
    "mesh_dz_nm": 8.0,
    "mesh_dxy_nm": 180.0,
}


def import_lumapi():
    api_dir = LUMERICAL_ROOT / "api" / "python"
    bin_dir = LUMERICAL_ROOT / "bin"
    for path in (api_dir, bin_dir):
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(path))
        os.environ["PATH"] = str(path) + os.pathsep + os.environ.get("PATH", "")
    lumapi_file = api_dir / "lumapi.py"
    if not lumapi_file.exists():
        raise RuntimeError("Cannot find lumapi.py: {}".format(lumapi_file))
    spec = importlib.util.spec_from_file_location("lumapi", str(lumapi_file))
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot import lumapi from {}".format(lumapi_file))
    lumapi = importlib.util.module_from_spec(spec)
    sys.modules["lumapi"] = lumapi
    spec.loader.exec_module(lumapi)
    return lumapi


def running_fdtd_processes():
    try:
        output = subprocess.check_output(["tasklist", "/fo", "csv", "/nh"], stderr=subprocess.STDOUT)
    except Exception:
        return []
    rows = []
    text = output.decode("mbcs", errors="replace")
    for line in text.splitlines():
        parts = [part.strip().strip('"') for part in line.split('","')]
        if len(parts) < 2:
            continue
        image_name = parts[0].strip('"')
        pid = parts[1].strip('"')
        lower = image_name.lower()
        if any(name in lower for name in FDTD_PROCESS_NAMES):
            rows.append({"image": image_name, "pid": pid})
    return rows


def pid_exists(pid):
    try:
        output = subprocess.check_output(
            ["tasklist", "/fi", "PID eq {}".format(int(pid)), "/fo", "csv", "/nh"],
            stderr=subprocess.STDOUT,
        )
    except Exception:
        return True
    text = output.decode("mbcs", errors="replace").strip()
    if not text or "No tasks" in text or "INFO:" in text:
        return False
    needle = str(int(pid))
    for line in text.splitlines():
        parts = [part.strip().strip('"') for part in line.split('","')]
        if len(parts) >= 2 and parts[1].strip('"') == needle:
            return True
    return False


@contextmanager
def single_fdtd_session_guard(run_dir=None):
    processes = running_fdtd_processes()
    if processes:
        message = "Detected running FDTD/Lumerical process; exiting this simulation thread: {}".format(processes)
        if run_dir is not None:
            write_json(Path(run_dir) / "04_logs" / "single_thread_blocked.json", {"reason": message, "processes": processes})
        raise RuntimeError(message)

    lock_path = STRUCTURE_ROOT / "logs" / SIM_LOCK_NAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError:
        existing = ""
        try:
            existing = lock_path.read_text(encoding="utf-8")
        except Exception:
            pass
        stale_lock = False
        try:
            lock_data = json.loads(existing)
            stale_pid = int(lock_data.get("pid", -1))
            stale_lock = stale_pid > 0 and not pid_exists(stale_pid)
        except Exception:
            stale_lock = False
        if not stale_lock:
            message = "Detected an active script simulation lock; exiting this simulation thread: {}".format(existing.strip())
            if run_dir is not None:
                write_json(Path(run_dir) / "04_logs" / "single_thread_blocked.json", {"reason": message, "lock": str(lock_path)})
            raise RuntimeError(message)
        lock_path.unlink()
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    try:
        payload = {"pid": os.getpid(), "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "script": str(Path(__file__).resolve())}
        os.write(fd, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        os.close(fd)
        yield
    finally:
        try:
            lock_path.unlink()
        except Exception:
            pass


def nm_to_m(value):
    return float(value) * NM


def layer_thicknesses(config):
    lambda0 = float(config["target_lambda_nm"])
    return {
        "d_high_nm": lambda0 / (4.0 * float(config["n_high"])),
        "d_low_nm": lambda0 / (4.0 * float(config["n_low"])),
        "d_cavity_nm": float(config.get("cavity_length_multiplier", 1.0)) * lambda0 / (2.0 * float(config["n_cavity"])),
    }


def chirp_centers_nm(config):
    return np.linspace(
        float(config["chirp_start_nm"]),
        float(config["chirp_stop_nm"]),
        int(config["mirror_pairs"]),
    )


def add_dielectric_layer(fdtd, name, z_min, z_max, period_m, index):
    fdtd.addrect()
    fdtd.set("name", name)
    fdtd.set("x", 0)
    fdtd.set("y", 0)
    fdtd.set("x span", period_m)
    fdtd.set("y span", period_m)
    fdtd.set("z min", z_min)
    fdtd.set("z max", z_max)
    fdtd.set("material", "<Object defined dielectric>")
    fdtd.set("index", float(index))


def build_geometry(fdtd, config):
    dims = layer_thicknesses(config)
    centers_nm = chirp_centers_nm(config)
    period = nm_to_m(config["period_nm"])
    d_cavity = nm_to_m(dims["d_cavity_nm"])
    half_stack = 0.5 * d_cavity
    for center_nm in centers_nm:
        half_stack += nm_to_m(center_nm / (4.0 * float(config["n_high"])))
        half_stack += nm_to_m(center_nm / (4.0 * float(config["n_low"])))

    fdtd.switchtolayout()
    fdtd.deleteall()

    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x", 0)
    fdtd.set("y", 0)
    fdtd.set("x span", period)
    fdtd.set("y span", period)
    fdtd.set("z min", -half_stack - 1.25 * UM)
    fdtd.set("z max", half_stack + 1.25 * UM)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", int(config["mesh_accuracy"]))
    fdtd.set("simulation time", float(config["simulation_time_fs"]) * 1e-15)
    for prop, value in (
        ("dt stability factor", config["dt_stability_factor"]),
        ("auto shutoff min", config["auto_shutoff_min"]),
        ("auto shutoff max", config["auto_shutoff_max"]),
        ("down sample time", config["down_sample_time"]),
        ("min mesh step", float(config["min_mesh_step_um"]) * UM),
        ("max source time signal length", config["max_source_time_signal_length"]),
    ):
        try:
            fdtd.set(prop, value)
        except Exception:
            pass
    try:
        fdtd.set("background material", "<Object defined dielectric>")
        fdtd.set("index", float(config["background_index"]))
    except Exception:
        pass
    try:
        fdtd.setglobalmonitor("frequency points", int(config["frequency_points"]))
    except Exception:
        pass

    add_dielectric_layer(fdtd, "L_halfwave_defect_cavity", -0.5 * d_cavity, 0.5 * d_cavity, period, config["n_cavity"])
    z_top = 0.5 * d_cavity
    z_bottom = -0.5 * d_cavity
    for idx, center_nm in enumerate(centers_nm):
        d_high = nm_to_m(center_nm / (4.0 * float(config["n_high"])))
        d_low = nm_to_m(center_nm / (4.0 * float(config["n_low"])))
        add_dielectric_layer(fdtd, "top_H_{:02d}".format(idx), z_top, z_top + d_high, period, config["n_high"])
        z_top += d_high
        add_dielectric_layer(fdtd, "top_L_{:02d}".format(idx), z_top, z_top + d_low, period, config["n_low"])
        z_top += d_low

        add_dielectric_layer(fdtd, "bottom_H_{:02d}".format(idx), z_bottom - d_high, z_bottom, period, config["n_high"])
        z_bottom -= d_high
        add_dielectric_layer(fdtd, "bottom_L_{:02d}".format(idx), z_bottom - d_low, z_bottom, period, config["n_low"])
        z_bottom -= d_low

    fdtd.addmesh()
    fdtd.set("name", "z_resolved_stack_mesh")
    fdtd.set("x", 0)
    fdtd.set("y", 0)
    fdtd.set("x span", period)
    fdtd.set("y span", period)
    fdtd.set("z min", -half_stack)
    fdtd.set("z max", half_stack)
    fdtd.set("dx", nm_to_m(config["mesh_dxy_nm"]))
    fdtd.set("dy", nm_to_m(config["mesh_dxy_nm"]))
    fdtd.set("dz", nm_to_m(config["mesh_dz_nm"]))

    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Backward")
    fdtd.set("x span", period)
    fdtd.set("y span", period)
    fdtd.set("z", half_stack + 0.65 * UM)
    fdtd.set("wavelength start", nm_to_m(config["lambda_start_nm"]))
    fdtd.set("wavelength stop", nm_to_m(config["lambda_stop_nm"]))

    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", period)
    fdtd.set("y span", period)
    fdtd.set("z", -half_stack - 0.65 * UM)
    try:
        fdtd.set("override global monitor settings", 1)
        fdtd.set("frequency points", int(config["frequency_points"]))
    except Exception:
        pass


def seed_fsp_path():
    return STRUCTURE_ROOT / "fsp" / SEED_FSP_NAME


def prepare_run_dir(mode):
    root = STRUCTURE_ROOT / "results" / "mirror_symmetric_dbr_defect_scan"
    run_dir = root / ("run_{}_{}".format(mode, datetime.now().strftime("%Y%m%d_%H%M%S")))
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def ensure_folders(run_dir):
    folders = {
        "plan": run_dir / "00_scan_plan",
        "fsp": run_dir / "01_fsp",
        "excel": run_dir / "02_transmission_excel",
        "png": run_dir / "03_transmission_abs2_png",
        "logs": run_dir / "04_logs",
    }
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def extract_transmission(fdtd):
    wl = None
    tr = None
    try:
        result = fdtd.getresult("T", "T")
        if isinstance(result, dict):
            wl = result.get("lambda", result.get("wavelength"))
            tr = result.get("T", result.get("t"))
    except Exception:
        pass
    if wl is None:
        try:
            wl = fdtd.getdata("T", "lambda")
        except Exception:
            wl = None
    if tr is None:
        tr = fdtd.transmission("T")
    wl = np.asarray(wl if wl is not None else []).reshape(-1).astype(float)
    tr = np.asarray(tr).reshape(-1)
    if wl.size == 0:
        wl = C0 / np.asarray(fdtd.getdata("T", "f")).reshape(-1).astype(float)
    n = min(wl.size, tr.size)
    wl = wl[:n]
    tr = tr[:n]
    order = np.argsort(wl)
    return wl[order], tr[order]


def transmission_abs2(transmission):
    return (np.abs(np.asarray(transmission).reshape(-1)) ** 2).astype(float)


def interpolate_crossing(x0, y0, x1, y1, target):
    if abs(y1 - y0) < 1e-30:
        return x0
    t = (target - y0) / (y1 - y0)
    return x0 + max(0.0, min(1.0, float(t))) * (x1 - x0)


def spectrum_metrics(wavelength_m, transmission):
    wl_nm = np.asarray(wavelength_m, dtype=float).reshape(-1) / NM
    power = transmission_abs2(transmission)
    n = min(wl_nm.size, power.size)
    if n < 20:
        return {"status": "too_few_points", "accepted": False}
    wl_nm = wl_nm[:n]
    power = power[:n]
    if not np.all(np.isfinite(power)):
        return {"status": "nan_or_inf", "accepted": False}
    peak_idx = int(np.nanargmax(power))
    peak = float(power[peak_idx])
    peak_nm = float(wl_nm[peak_idx])
    edge_margin = min(abs(peak_nm - float(wl_nm[0])), abs(float(wl_nm[-1]) - peak_nm))
    scan_span_nm = float(wl_nm[-1]) - float(wl_nm[0])
    exclude_half_width = max(0.15, min(20.0, 0.04 * scan_span_nm))
    offband_mask = np.abs(wl_nm - peak_nm) > exclude_half_width
    offband = power[offband_mask] if np.any(offband_mask) else power
    offband_p95 = float(np.nanpercentile(offband, 95))
    offband_max = float(np.nanmax(offband))
    offband_median = float(np.nanmedian(offband))
    baseline = float(np.nanpercentile(offband, 20))
    half = baseline + 0.5 * max(peak - baseline, 0.0)
    side_peak_count = 0
    side_threshold = float(TARGETS["side_peak_threshold_abs2"])
    for i in range(1, n - 1):
        if (
            offband_mask[i]
            and power[i] >= side_threshold
            and power[i] > power[i - 1]
            and power[i] > power[i + 1]
        ):
            side_peak_count += 1

    left_nm = None
    for i in range(peak_idx, 0, -1):
        if power[i - 1] <= half <= power[i] or power[i] <= half <= power[i - 1]:
            left_nm = interpolate_crossing(wl_nm[i], power[i], wl_nm[i - 1], power[i - 1], half)
            break
    right_nm = None
    for i in range(peak_idx, n - 1):
        if power[i] >= half >= power[i + 1] or power[i] <= half <= power[i + 1]:
            right_nm = interpolate_crossing(wl_nm[i], power[i], wl_nm[i + 1], power[i + 1], half)
            break
    fwhm_nm = float("inf") if left_nm is None or right_nm is None else max(0.0, float(right_nm - left_nm))
    contrast = peak / max(offband_p95, 1e-12)
    accepted = (
        peak >= TARGETS["peak_abs2_min"]
        and peak <= TARGETS["peak_abs2_max"]
        and offband_p95 <= TARGETS["offband_p95_max"]
        and offband_max <= TARGETS["offband_max_max"]
        and side_peak_count <= TARGETS["side_peak_count_max"]
        and fwhm_nm <= TARGETS["fwhm_max_nm"]
        and contrast >= TARGETS["contrast_min"]
        and edge_margin >= TARGETS["edge_margin_nm"]
    )
    score = (
        2.8 * min(peak / TARGETS["peak_abs2_min"], 2.0)
        + 2.2 * min(contrast / TARGETS["contrast_min"], 2.0)
        - 1.8 * min(fwhm_nm / TARGETS["fwhm_max_nm"], 5.0)
        - 2.6 * min(offband_p95 / TARGETS["offband_p95_max"], 5.0)
        - 2.6 * min(offband_max / TARGETS["offband_max_max"], 5.0)
        - 0.8 * side_peak_count
    )
    return {
        "status": "target_hit" if accepted else "candidate",
        "accepted": bool(accepted),
        "metric_basis": "gui_abs2_T",
        "peak_abs2": peak,
        "peak_nm": peak_nm,
        "baseline_abs2": baseline,
        "offband_median_abs2": offband_median,
        "offband_p95_abs2": offband_p95,
        "offband_max_abs2": offband_max,
        "side_peak_count": int(side_peak_count),
        "contrast_vs_p95": float(contrast),
        "fwhm_nm": float(fwhm_nm),
        "edge_margin_nm": float(edge_margin),
        "score": float(score),
    }


def xlsx_col_name(index):
    name = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def xlsx_cell(row_index, col_index, value):
    ref = "{}{}".format(xlsx_col_name(col_index), row_index + 1)
    if value is None or value == "":
        return '<c r="{}"/>'.format(ref)
    if isinstance(value, (int, float, np.integer, np.floating)) and np.isfinite(float(value)):
        return '<c r="{}"><v>{:.16g}</v></c>'.format(ref, float(value))
    return '<c r="{}" t="inlineStr"><is><t>{}</t></is></c>'.format(ref, escape(str(value)))


def xlsx_sheet_xml(rows):
    xml_rows = []
    for r, row in enumerate(rows):
        cells = [xlsx_cell(r, c, value) for c, value in enumerate(row)]
        xml_rows.append('<row r="{}">{}</row>'.format(r + 1, "".join(cells)))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>{}</sheetData></worksheet>'
    ).format("".join(xml_rows))


def save_xlsx(path, sheets):
    wb_sheets = []
    rels = []
    overrides = []
    for idx, (name, rows) in enumerate(sheets, start=1):
        wb_sheets.append('<sheet name="{}" sheetId="{}" r:id="rId{}"/>'.format(escape(name), idx, idx))
        rels.append('<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{}.xml"/>'.format(idx, idx))
        overrides.append('<Override PartName="/xl/worksheets/sheet{}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.format(idx))
    wb_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{}</sheets></workbook>'.format("".join(wb_sheets))
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{}</Relationships>'.format("".join(rels))
    root_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    ctype = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>{}</Types>'.format("".join(overrides))
    with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ctype)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", wb_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        for idx, (_, rows) in enumerate(sheets, start=1):
            zf.writestr("xl/worksheets/sheet{}.xml".format(idx), xlsx_sheet_xml(rows))


def save_outputs(folders, wavelength_m, transmission, config, metrics):
    stem = "chirped_dbr_N{}_cav{:.3f}".format(int(config["mirror_pairs"]), float(config["cavity_length_multiplier"])).replace(".", "d")
    xlsx_path = folders["excel"] / (stem + "_transmission_abs2.xlsx")
    png_path = folders["png"] / (stem + "_transmission_abs2.png")
    tr = np.asarray(transmission).reshape(-1)
    wl_nm = np.asarray(wavelength_m).reshape(-1) / NM
    abs2 = transmission_abs2(tr)
    rows = [["wavelength_nm", "T_abs2_gui", "T_real_raw", "T_imag_raw"]]
    for wl, val, pwr in zip(wl_nm, tr, abs2):
        rows.append([float(wl), float(pwr), float(np.real(val)), float(np.imag(val))])
    meta = [["key", "value"]]
    for key in sorted(config.keys()):
        meta.append([key, config[key]])
    for key in sorted(metrics.keys()):
        meta.append(["metric_" + key, metrics[key]])
    save_xlsx(xlsx_path, [("transmission_abs2_gui", rows), ("metadata", meta)])

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8.6, 5.2), dpi=170)
        ax.plot(wl_nm, abs2, linewidth=1.5, color="#155e75")
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Abs(T)^2")
        ax.set_title("Cinf mirror-symmetric chirped DBR defect cavity")
        ax.grid(True, alpha=0.25)
        if "peak_nm" in metrics:
            ax.axvline(metrics["peak_nm"], color="#c2410c", alpha=0.65, linewidth=1.0)
            ax.text(
                0.02,
                0.96,
                "peak={:.4g} @ {:.2f} nm\nFWHM={:.3g} nm\np95 offband={:.4g}".format(
                    metrics.get("peak_abs2", float("nan")),
                    metrics.get("peak_nm", float("nan")),
                    metrics.get("fwhm_nm", float("nan")),
                    metrics.get("offband_p95_abs2", float("nan")),
                ),
                transform=ax.transAxes,
                va="top",
                ha="left",
                fontsize=8,
                bbox=dict(facecolor="white", alpha=0.84, edgecolor="#cccccc"),
            )
        fig.tight_layout()
        fig.savefig(str(png_path))
        plt.close(fig)
    except Exception:
        png_path = ""
    return str(xlsx_path), str(png_path)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_manifest(path, config, metrics):
    fields = [
        "target_lambda_nm",
        "mirror_pairs",
        "chirp_start_nm",
        "chirp_stop_nm",
        "cavity_length_multiplier",
        "n_high",
        "n_low",
        "d_high_nm",
        "d_low_nm",
        "d_cavity_nm",
        "status",
        "accepted",
        "score",
        "metric_basis",
        "peak_abs2",
        "peak_nm",
        "fwhm_nm",
        "offband_p95_abs2",
        "offband_max_abs2",
        "side_peak_count",
        "contrast_vs_p95",
        "edge_margin_nm",
        "elapsed_s",
        "fsp",
        "xlsx",
        "png",
        "error",
    ]
    row = {}
    row.update(config)
    row.update(layer_thicknesses(config))
    row.update(metrics)
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fields})


def write_plan(run_dir, config):
    dims = layer_thicknesses(config)
    centers = chirp_centers_nm(config)
    lines = [
        "# Cinf mirror-symmetric chirped DBR defect cavity",
        "",
        "- Goal: low offband transmission across the full scan, high narrow resonant transmission through a tuned defect.",
        "- Symmetry: in-plane Cinf approximation under periodic boundary, plus z mirror symmetry around the defect cavity.",
        "- Chirped quarter-wave mirrors cover center wavelengths from {:.1f} nm to {:.1f} nm.".format(float(centers[0]), float(centers[-1])),
        "- Each local mirror pair uses d_H(lambda_c)=lambda_c/(4*n_H), d_L(lambda_c)=lambda_c/(4*n_L).",
        "- Defect cavity: d_cavity = multiplier*lambda0/(2*n_cavity), multiplier = {}.".format(config["cavity_length_multiplier"]),
        "- Reference d_H(lambda0) = {:.3f} nm, d_L(lambda0) = {:.3f} nm, d_cavity = {:.3f} nm.".format(dims["d_high_nm"], dims["d_low_nm"], dims["d_cavity_nm"]),
        "- Mirror pairs per side: {}.".format(config["mirror_pairs"]),
        "- Metric basis: Lumerical visualizer-compatible Abs(T)^2.",
        "",
        "## Targets",
    ]
    for key in sorted(TARGETS.keys()):
        lines.append("- {}: {}".format(key, TARGETS[key]))
    (run_dir / "00_scan_plan" / "principle_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(run_dir / "00_scan_plan" / "config.json", config)


def run_once(mode):
    config = dict(BASE_CONFIG)
    run_dir = prepare_run_dir(mode)
    folders = ensure_folders(run_dir)
    write_plan(run_dir, config)
    start = time.time()
    metrics = {}
    fsp_path = folders["fsp"] / SEED_FSP_NAME
    with single_fdtd_session_guard(run_dir):
        lumapi = import_lumapi()
        fdtd = lumapi.FDTD(hide=True)
        try:
            build_geometry(fdtd, config)
            seed_fsp_path().parent.mkdir(parents=True, exist_ok=True)
            fdtd.save(str(seed_fsp_path()))
            fdtd.save(str(fsp_path))
            if mode != "preview":
                fdtd.run()
                wavelength_m, transmission = extract_transmission(fdtd)
                fdtd.save(str(fsp_path))
                metrics = spectrum_metrics(wavelength_m, transmission)
                xlsx, png = save_outputs(folders, wavelength_m, transmission, config, metrics)
                metrics["xlsx"] = xlsx
                metrics["png"] = png
            else:
                metrics = {"status": "preview_only", "accepted": False}
        except Exception as exc:
            metrics = {"status": "failed", "accepted": False, "error": repr(exc)}
        finally:
            try:
                fdtd.close()
            except Exception:
                pass
    metrics["elapsed_s"] = time.time() - start
    metrics["fsp"] = str(fsp_path)
    write_json(folders["logs"] / "metrics.json", {"config": config, "derived": layer_thicknesses(config), "metrics": metrics})
    write_manifest(folders["logs"] / "manifest.csv", config, metrics)
    return run_dir, metrics


def parse_args():
    parser = argparse.ArgumentParser(description=STRUCTURE_NAME)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--test", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    mode = "test"
    if args.preview:
        mode = "preview"
    if args.test:
        mode = "test"
    run_dir, metrics = run_once(mode)
    print("run_dir={}".format(run_dir))
    print("status={} peak_abs2={} fwhm_nm={} offband_p95_abs2={}".format(
        metrics.get("status"),
        metrics.get("peak_abs2", ""),
        metrics.get("fwhm_nm", ""),
        metrics.get("offband_p95_abs2", ""),
    ))
    return 0 if metrics.get("status") != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
