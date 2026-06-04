# -*- coding: utf-8 -*-
"""
Search script for the D4 quasi-BIC double-ring eight-slit coupled cavity.

The script keeps the original seed FSP in the structure-level fsp folder and
writes every simulated candidate into a timestamped results batch.
"""
from __future__ import print_function

import argparse
import csv
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np


NM = 1e-9
UM = 1e-6
C0 = 299792458.0

STRUCTURE_ROOT = Path(__file__).resolve().parents[2]
STRUCTURE_NAME = "双环八缝耦合腔"
PERTURBATION_NAME = "对角失谐准BIC寻优"
SEED_FSP_NAME = "d4_double_ring_eight_slit_seed.fsp"
LUMERICAL_ROOT = Path(r"D:\Program Files\Lumerical\v202")
SIM_LOCK_NAME = ".fdtd_single_simulation.lock"
FDTD_PROCESS_NAMES = (
    "fdtd-solutions",
    "fdtd-engine",
    "fdtd-run-local",
    "lumerical",
)

THEORY_MODEL = {
    "target_lambda_nm": 1350.0,
    "effective_index_guess": 1.90,
    "dark_azimuthal_order": 2,
    "outer_ring_width_nm": 110.0,
    "inner_ring_width_nm": 75.0,
    "outer_inner_coupling_gap_nm": 35.0,
    "period_nm": 900.0,
    "height_nm": 420.0,
    "substrate_nm": 1000.0,
    "lambda_start_nm": 900.0,
    "lambda_stop_nm": 1700.0,
    "base_gap_nm": 18.0,
    "center_disk_radius_nm": 50.0,
    "bridge_width_nm": 38.0,
    "bridge_length_nm": 100.0,
    "use_gold_screen": True,
    "screen_metal_material": "Ag (Silver) - Palik (1-10um)",
    "gold_thickness_nm": 90.0,
    "screen_aperture_width_nm": 26.0,
    "screen_aperture_extra_length_nm": 58.0,
    "frequency_points": 601,
    "mesh_accuracy": 1,
    "simulation_time_fs": 1500.0,
    "auto_shutoff_min": 1e-5,
    "dt_stability_factor": 0.8,
}


def derive_base_config(model):
    # Ring resonance estimate: lambda0 ~= 2*pi*n_eff*R_eff/m.
    radius_eff_nm = (
        float(model["dark_azimuthal_order"])
        * float(model["target_lambda_nm"])
        / (2.0 * math.pi * float(model["effective_index_guess"]))
    )
    outer_width_nm = float(model["outer_ring_width_nm"])
    outer_inner_nm = radius_eff_nm - 0.5 * outer_width_nm
    outer_outer_nm = radius_eff_nm + 0.5 * outer_width_nm
    inner_outer_nm = outer_inner_nm - float(model["outer_inner_coupling_gap_nm"])
    inner_inner_nm = inner_outer_nm - float(model["inner_ring_width_nm"])
    config = dict(model)
    config.update(
        {
            "resonance_estimate_nm": float(model["target_lambda_nm"]),
            "outer_effective_radius_nm": radius_eff_nm,
            "outer_inner_radius_nm": outer_inner_nm,
            "outer_outer_radius_nm": outer_outer_nm,
            "inner_inner_radius_nm": inner_inner_nm,
            "inner_outer_radius_nm": inner_outer_nm,
            "screen_aperture_radius_nm": radius_eff_nm,
            "screen_aperture_length_nm": outer_width_nm + float(model["screen_aperture_extra_length_nm"]),
            "eta_nm": 0.0,
            "inner_outer_shift_nm": 0.0,
        }
    )
    return config


BASE_CONFIG = derive_base_config(THEORY_MODEL)

TARGETS = {
    "peak_min": 0.85,
    "peak_max": 1.0,
    "offband_p95_max": 0.03,
    "offband_local_peak_max": 0.03,
    "offband_local_peak_count_max": 2,
    "fwhm_max_nm": 8.0,
    "contrast_min": 30.0,
    "edge_margin_nm": 35.0,
}

TEST_TRIAL_COUNT = 2

USER_VALIDATION_RUNTIME = {
    "simulation_time_fs": 50000.0,
    "mesh_accuracy": 2,
    "dt_stability_factor": 0.99,
    "auto_shutoff_min": 1e-7,
    "auto_shutoff_max": 100000,
    "down_sample_time": 100,
    "min_mesh_step_um": 0.00025,
    "max_source_time_signal_length": 32768,
    "background_index": 1.0,
    "fdtd_z_min_um": None,
    "fdtd_z_max_air_um": 1.25,
    "source_z_offset_um": 0.82,
    "transmission_monitor_z_um": -0.25,
    "critical_mesh_enabled": False,
    "critical_mesh_span_nm": 760.0,
    "critical_mesh_z_margin_nm": 8.0,
    "critical_mesh_dx_nm": 10.0,
    "critical_mesh_dy_nm": 10.0,
    "critical_mesh_dz_nm": 10.0,
}


VALIDATION_REFERENCE_CANDIDATE = {
    "index": 0,
    "eta_nm": 6.60143809,
    "base_gap_nm": 14.0,
    "inner_outer_shift_nm": -10.0,
    "dimensionless_delta": 0.029188263609389992,
    "relative_q_rad": 1173.771283632527,
    "gap_angle_deg": 3.5466666666666664,
    "lambda0_estimate_nm": 1350.0,
    "coupling_hint": 2.640575236,
    "screen_aperture_width_nm": 36.0,
    "screen_aperture_extra_length_nm": 115.0,
    "gold_thickness_nm": 90.0,
}


VALIDATION_PROFILES = [
    {
        "name": "mesh1_critical",
        "simulation_time_fs": 50000.0,
        "mesh_accuracy": 1,
        "dt_stability_factor": 0.99,
        "auto_shutoff_min": 1e-7,
        "auto_shutoff_max": 100000,
        "down_sample_time": 100,
        "critical_mesh_enabled": True,
        "critical_mesh_span_nm": 620.0,
        "critical_mesh_z_margin_nm": 8.0,
        "critical_mesh_dx_nm": 10.0,
        "critical_mesh_dy_nm": 10.0,
        "critical_mesh_dz_nm": 15.0,
    },
    {
        "name": "mesh2_critical_ref",
        "simulation_time_fs": 50000.0,
        "mesh_accuracy": 2,
        "dt_stability_factor": 0.99,
        "auto_shutoff_min": 1e-7,
        "auto_shutoff_max": 100000,
        "down_sample_time": 100,
        "critical_mesh_enabled": True,
        "critical_mesh_span_nm": 620.0,
        "critical_mesh_z_margin_nm": 8.0,
        "critical_mesh_dx_nm": 10.0,
        "critical_mesh_dy_nm": 10.0,
        "critical_mesh_dz_nm": 15.0,
    },
    {
        "name": "mesh2_critical_long",
        "simulation_time_fs": 80000.0,
        "mesh_accuracy": 2,
        "dt_stability_factor": 0.995,
        "auto_shutoff_min": 1e-8,
        "auto_shutoff_max": 100000,
        "down_sample_time": 100,
        "critical_mesh_enabled": True,
        "critical_mesh_span_nm": 620.0,
        "critical_mesh_z_margin_nm": 8.0,
        "critical_mesh_dx_nm": 10.0,
        "critical_mesh_dy_nm": 10.0,
        "critical_mesh_dz_nm": 15.0,
    },
]


FIELD_ANALYSIS_PROFILE = {
    "name": "field_map",
    "simulation_time_fs": 50000.0,
    "mesh_accuracy": 2,
    "dt_stability_factor": 0.99,
    "auto_shutoff_min": 1e-7,
    "auto_shutoff_max": 100000,
    "down_sample_time": 100,
    "field_monitor_z_nm": 210.0,
}


OPTIMIZATION_RUNTIME = {
    "name": "mesh2_long_opt",
    "simulation_time_fs": 80000.0,
    "mesh_accuracy": 2,
    "dt_stability_factor": 0.995,
    "auto_shutoff_min": 1e-8,
    "auto_shutoff_max": 100000,
    "down_sample_time": 100,
}


OPTIMIZATION_CANDIDATES = [
    {
        "study_case": "extra130_zpadding",
        "screen_aperture_extra_length_nm": 130.0,
        "screen_aperture_width_nm": 36.0,
        "gold_thickness_nm": 90.0,
        "fdtd_z_min_um": -1.25,
        "fdtd_z_max_air_um": 1.80,
        "source_z_offset_um": 1.05,
        "transmission_monitor_z_um": -0.35,
    },
    {
        "study_case": "extra120_zpadding",
        "screen_aperture_extra_length_nm": 120.0,
        "screen_aperture_width_nm": 36.0,
        "gold_thickness_nm": 90.0,
        "fdtd_z_min_um": -1.25,
        "fdtd_z_max_air_um": 1.80,
        "source_z_offset_um": 1.05,
        "transmission_monitor_z_um": -0.35,
    },
]


def chinese_timestamp():
    now = datetime.now()
    return "{}年{}月{}日_{:02d}时{:02d}分{:02d}秒".format(
        now.year, now.month, now.day, now.hour, now.minute, now.second
    )


def safe_token(text):
    out = []
    for ch in str(text):
        if ch.isalnum() or ch in ("_", "-", "."):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("_") or "item"


def nm_to_m(value):
    return float(value) * NM


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
        output = subprocess.check_output(
            ["tasklist", "/fo", "csv", "/nh"],
            stderr=subprocess.STDOUT,
        )
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
        message = "检测到已有 FDTD/Lumerical 进程，当前仿真线程直接退出: {}".format(processes)
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
        message = "检测到已有脚本仿真锁，当前仿真线程直接退出: {}".format(existing.strip())
        if run_dir is not None:
            write_json(Path(run_dir) / "04_logs" / "single_thread_blocked.json", {"reason": message, "lock": str(lock_path)})
        raise RuntimeError(message)

    try:
        payload = {
            "pid": os.getpid(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "script": str(Path(__file__).resolve()),
        }
        os.write(fd, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        os.close(fd)
        yield
    finally:
        try:
            lock_path.unlink()
        except Exception:
            pass


# Stale locks can remain after a killed FDTD job; this guard keeps real process
# blocking strict while allowing confirmed-dead locks to be replaced.
@contextmanager
def single_fdtd_session_guard(run_dir=None):
    processes = running_fdtd_processes()
    if processes:
        message = "检测到已有 FDTD/Lumerical 进程，当前仿真线程直接退出: {}".format(processes)
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
            message = "检测到已有脚本仿真锁，当前仿真线程直接退出: {}".format(existing.strip())
            if run_dir is not None:
                write_json(Path(run_dir) / "04_logs" / "single_thread_blocked.json", {"reason": message, "lock": str(lock_path)})
            raise RuntimeError(message)
        lock_path.unlink()
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    try:
        payload = {
            "pid": os.getpid(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "script": str(Path(__file__).resolve()),
        }
        os.write(fd, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        os.close(fd)
        yield
    finally:
        try:
            lock_path.unlink()
        except Exception:
            pass


def add_rect(fdtd, name, x, y, x_span, y_span, z_min, z_max, material, rotation_deg=0.0, mesh_order=None):
    fdtd.addrect()
    fdtd.set("name", name)
    fdtd.set("x", x)
    fdtd.set("y", y)
    fdtd.set("x span", x_span)
    fdtd.set("y span", y_span)
    fdtd.set("z min", z_min)
    fdtd.set("z max", z_max)
    fdtd.set("material", material)
    if abs(rotation_deg) > 1e-12:
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", rotation_deg)
    if mesh_order is not None:
        fdtd.set("override mesh order from material database", 1)
        fdtd.set("mesh order", int(mesh_order))


def add_circle(fdtd, name, x, y, radius, z_min, z_max, material, mesh_order=None):
    fdtd.addcircle()
    fdtd.set("name", name)
    fdtd.set("x", x)
    fdtd.set("y", y)
    fdtd.set("radius", radius)
    fdtd.set("z min", z_min)
    fdtd.set("z max", z_max)
    fdtd.set("material", material)
    if mesh_order is not None:
        fdtd.set("override mesh order from material database", 1)
        fdtd.set("mesh order", int(mesh_order))


def add_poly(fdtd, name, vertices, z_min, z_max, material, mesh_order=None):
    fdtd.addpoly()
    fdtd.set("name", name)
    fdtd.set("vertices", np.asarray(vertices, dtype=float))
    fdtd.set("z min", z_min)
    fdtd.set("z max", z_max)
    fdtd.set("material", material)
    if mesh_order is not None:
        fdtd.set("override mesh order from material database", 1)
        fdtd.set("mesh order", int(mesh_order))


def add_critical_mesh_override(fdtd, config, z_min, z_max):
    if not config.get("critical_mesh_enabled"):
        return
    span = nm_to_m(float(config.get("critical_mesh_span_nm", config["period_nm"])))
    dx = nm_to_m(float(config.get("critical_mesh_dx_nm", 4.0)))
    dy = nm_to_m(float(config.get("critical_mesh_dy_nm", 4.0)))
    dz = nm_to_m(float(config.get("critical_mesh_dz_nm", 4.0)))

    fdtd.addmesh()
    fdtd.set("name", "critical_mesh_D4_slits_and_rings")
    fdtd.set("x", 0)
    fdtd.set("y", 0)
    fdtd.set("x span", span)
    fdtd.set("y span", span)
    fdtd.set("z min", z_min)
    fdtd.set("z max", z_max)
    for prop in ("override x mesh", "override y mesh", "override z mesh"):
        try:
            fdtd.set(prop, 1)
        except Exception:
            pass
    fdtd.set("dx", dx)
    fdtd.set("dy", dy)
    fdtd.set("dz", dz)


def apply_runtime_overrides(config, overrides):
    merged = dict(config)
    merged.update(overrides or {})
    return merged


def add_single_monitor(fdtd, config, monitor_mode="power", monitor_name=None):
    monitor_name = monitor_name or ("E_field" if monitor_mode == "field" else "T")
    if monitor_mode == "field":
        fdtd.addprofile()
    else:
        fdtd.addpower()
    fdtd.set("name", monitor_name)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", nm_to_m(config["period_nm"]))
    fdtd.set("y span", nm_to_m(config["period_nm"]))
    if monitor_mode == "field":
        fdtd.set("z", nm_to_m(config.get("field_monitor_z_nm", -250.0)))
    else:
        fdtd.set("z", float(config.get("transmission_monitor_z_um", -0.25)) * UM)
    try:
        fdtd.set("override global monitor settings", 1)
        fdtd.set("frequency points", int(config["frequency_points"]))
    except Exception:
        pass
    if monitor_mode == "field":
        try:
            fdtd.set("record electric field", 1)
        except Exception:
            pass
    return monitor_name


def angle_width_from_gap(gap_nm, radius_nm):
    return max(2.5, min(18.0, float(gap_nm) / max(float(radius_nm), 1.0) * 180.0 / math.pi))


def polar(radius_m, angle_deg):
    a = math.radians(angle_deg)
    return [radius_m * math.cos(a), radius_m * math.sin(a)]


def add_annular_sector(fdtd, name, inner_radius_m, outer_radius_m, start_deg, end_deg, z_min, z_max, material):
    while end_deg <= start_deg:
        end_deg += 360.0
    width = end_deg - start_deg
    steps = max(4, int(math.ceil(width / 4.0)))
    outer = [polar(outer_radius_m, start_deg + width * i / float(steps)) for i in range(steps + 1)]
    inner = [polar(inner_radius_m, end_deg - width * i / float(steps)) for i in range(steps + 1)]
    add_poly(fdtd, name, outer + inner, z_min, z_max, material)


def build_gap_angles(config):
    radius_nm = 0.5 * (config["outer_inner_radius_nm"] + config["outer_outer_radius_nm"])
    base_gap = angle_width_from_gap(config["base_gap_nm"], radius_nm)
    detune = angle_width_from_gap(config["eta_nm"], radius_nm)
    gaps = []
    for idx in range(8):
        angle = idx * 45.0
        sign = 0.0
        if angle in (45.0, 225.0):
            sign = 1.0
        elif angle in (135.0, 315.0):
            sign = -1.0
        gaps.append(max(2.5, base_gap + sign * detune))
    return gaps


def d4_detune_sign(angle_deg):
    angle = float(angle_deg) % 360.0
    if angle in (45.0, 225.0):
        return 1.0
    if angle in (135.0, 315.0):
        return -1.0
    return 0.0


def build_candidate_geometry(fdtd, config, monitor_mode="power", monitor_name=None):
    si = "Si (Silicon) - Palik"
    glass = "SiO2 (Glass) - Palik"
    metal = config.get("screen_metal_material", "Au (Gold) - Palik")
    air = "etch"
    period = nm_to_m(config["period_nm"])
    height = nm_to_m(config["height_nm"])
    substrate = nm_to_m(config["substrate_nm"])
    z0 = 0.0
    z1 = height

    fdtd.switchtolayout()
    fdtd.deleteall()

    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x", 0)
    fdtd.set("y", 0)
    fdtd.set("x span", period)
    fdtd.set("y span", period)
    z_min_override = config.get("fdtd_z_min_um")
    fdtd_z_min = -0.55 * substrate if z_min_override is None else float(z_min_override) * UM
    fdtd_z_max = height + float(config.get("fdtd_z_max_air_um", 1.25)) * UM
    fdtd.set("z min", fdtd_z_min)
    fdtd.set("z max", fdtd_z_max)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", int(config["mesh_accuracy"]))
    fdtd.set("simulation time", float(config["simulation_time_fs"]) * 1e-15)
    try:
        fdtd.set("auto shutoff min", float(config["auto_shutoff_min"]))
        fdtd.set("dt stability factor", float(config["dt_stability_factor"]))
    except Exception:
        pass
    for prop, value in (
        ("auto shutoff max", config.get("auto_shutoff_max")),
        ("down sample time", config.get("down_sample_time")),
        ("min mesh step", None if config.get("min_mesh_step_um") is None else float(config["min_mesh_step_um"]) * UM),
        ("max source time signal length", config.get("max_source_time_signal_length")),
    ):
        if value is None:
            continue
        try:
            fdtd.set(prop, value)
        except Exception:
            pass
    try:
        fdtd.set("background material", "<Object defined dielectric>")
        fdtd.set("index", float(config.get("background_index", 1.0)))
    except Exception:
        pass

    try:
        fdtd.setglobalmonitor("frequency points", int(config["frequency_points"]))
    except Exception:
        pass

    add_rect(fdtd, "SiO2_substrate", 0, 0, period, period, -substrate, 0, glass)
    if config.get("use_gold_screen"):
        gold_thickness = nm_to_m(config["gold_thickness_nm"])
        add_rect(fdtd, "metal_low_background_screen", 0, 0, period, period, -gold_thickness, 0, metal)
        aperture_radius = nm_to_m(config["screen_aperture_radius_nm"])
        aperture_length = nm_to_m(config["screen_aperture_length_nm"])
        aperture_base_width_nm = float(config["screen_aperture_width_nm"])
        for angle in (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0):
            width_nm = max(6.0, aperture_base_width_nm + d4_detune_sign(angle) * float(config["eta_nm"]))
            x, y = polar(aperture_radius, angle)
            add_rect(
                fdtd,
                "air_screen_slit_{:03d}".format(int(angle)),
                x,
                y,
                aperture_length,
                nm_to_m(width_nm),
                -gold_thickness - 1.0 * NM,
                1.0 * NM,
                air,
                rotation_deg=angle,
                mesh_order=1,
            )

    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Backward")
    fdtd.set("x span", period)
    fdtd.set("y span", period)
    fdtd.set("z", height + float(config.get("source_z_offset_um", 0.82)) * UM)
    fdtd.set("wavelength start", nm_to_m(config["lambda_start_nm"]))
    fdtd.set("wavelength stop", nm_to_m(config["lambda_stop_nm"]))

    add_single_monitor(fdtd, config, monitor_mode=monitor_mode, monitor_name=monitor_name)

    outer_inner = nm_to_m(config["outer_inner_radius_nm"])
    outer_outer = nm_to_m(config["outer_outer_radius_nm"])
    inner_inner = nm_to_m(config["inner_inner_radius_nm"])
    inner_outer = nm_to_m(config["inner_outer_radius_nm"] + config["inner_outer_shift_nm"])
    center_radius = nm_to_m(config["center_disk_radius_nm"])

    slit_centers = [idx * 45.0 for idx in range(8)]
    gap_angles = build_gap_angles(config)
    for idx in range(8):
        start = slit_centers[idx] + gap_angles[idx] / 2.0
        end = slit_centers[(idx + 1) % 8] - gap_angles[(idx + 1) % 8] / 2.0
        if idx == 7:
            end += 360.0
        add_annular_sector(
            fdtd,
            "Si_outer_arc_{:02d}".format(idx),
            outer_inner,
            outer_outer,
            start,
            end,
            z0,
            z1,
            si,
        )

    for idx, center in enumerate((0.0, 90.0, 180.0, 270.0)):
        add_annular_sector(
            fdtd,
            "Si_inner_arc_{:02d}".format(idx),
            inner_inner,
            inner_outer,
            center - 31.0,
            center + 31.0,
            z0,
            z1,
            si,
        )

    add_circle(fdtd, "Si_center_disk", 0, 0, center_radius, z0, z1, si)

    bridge_w = nm_to_m(config["bridge_width_nm"])
    bridge_l = nm_to_m(config["bridge_length_nm"])
    bridge_offset = nm_to_m(config["center_disk_radius_nm"] + 0.5 * config["bridge_length_nm"])
    add_rect(fdtd, "Si_bridge_px", bridge_offset, 0, bridge_l, bridge_w, z0, z1, si)
    add_rect(fdtd, "Si_bridge_nx", -bridge_offset, 0, bridge_l, bridge_w, z0, z1, si)
    add_rect(fdtd, "Si_bridge_py", 0, bridge_offset, bridge_w, bridge_l, z0, z1, si)
    add_rect(fdtd, "Si_bridge_ny", 0, -bridge_offset, bridge_w, bridge_l, z0, z1, si)
    z_margin = nm_to_m(float(config.get("critical_mesh_z_margin_nm", 0.0)))
    add_critical_mesh_override(fdtd, config, -nm_to_m(config["gold_thickness_nm"]) - z_margin, height + z_margin)


def seed_fsp_path():
    return STRUCTURE_ROOT / "fsp" / SEED_FSP_NAME


def save_seed_fsp(lumapi=None):
    path = seed_fsp_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    close_fdtd = False
    if lumapi is None:
        lumapi = import_lumapi()
    fdtd = lumapi.FDTD(hide=True)
    close_fdtd = True
    try:
        build_candidate_geometry(fdtd, dict(BASE_CONFIG))
        fdtd.save(str(path))
    finally:
        if close_fdtd:
            fdtd.close()
    return path


def make_config(candidate, mode):
    config = dict(BASE_CONFIG)
    config.update(candidate)
    config["screen_aperture_length_nm"] = (
        float(config["outer_ring_width_nm"]) + float(config["screen_aperture_extra_length_nm"])
    )
    if mode in ("test", "full"):
        config.update(USER_VALIDATION_RUNTIME)
    if mode == "test":
        config["frequency_points"] = 601
    if mode == "full":
        config["frequency_points"] = 901
    return config


def estimate_candidate_theory_fields(eta_nm, gap_nm, inner_shift_nm, screen_width_nm=None, gold_thickness_nm=None):
    radius_eff_nm = float(BASE_CONFIG["outer_effective_radius_nm"])
    lambda0_nm = float(BASE_CONFIG["resonance_estimate_nm"])
    delta = abs(float(eta_nm)) / max(radius_eff_nm, 1e-9)
    if delta <= 0:
        relative_q_rad = float("inf")
    else:
        # Quasi-BIC scaling: gamma_rad proportional to delta^2, so Q_rad proportional to 1/delta^2.
        relative_q_rad = 1.0 / (delta * delta)
    gap_angle_deg = angle_width_from_gap(gap_nm, radius_eff_nm)
    aperture_width_nm = float(screen_width_nm if screen_width_nm is not None else BASE_CONFIG["screen_aperture_width_nm"])
    gold_nm = float(gold_thickness_nm if gold_thickness_nm is not None else BASE_CONFIG["gold_thickness_nm"])
    coupling_hint = aperture_width_nm * max(float(eta_nm), 1e-9) / max(gold_nm, 1e-9)
    return {
        "dimensionless_delta": delta,
        "relative_q_rad": relative_q_rad,
        "gap_angle_deg": gap_angle_deg,
        "lambda0_estimate_nm": lambda0_nm,
        "outer_effective_radius_nm": radius_eff_nm,
        "coupling_hint": coupling_hint,
        "theory_note": "lambda0=2*pi*n_eff*R_eff/m; Q_rad~1/delta^2",
    }


def build_candidates(max_trials=None):
    target_lambda_nm = float(BASE_CONFIG["resonance_estimate_nm"])
    target_fwhm_nm = float(TARGETS["fwhm_max_nm"])
    target_q = target_lambda_nm / target_fwhm_nm
    radius_eff_nm = float(BASE_CONFIG["outer_effective_radius_nm"])

    # eta is the physical slit detuning length. The normalized detuning delta=eta/R_eff
    # is chosen around the Q target implied by FWHM ~= lambda0/Q.
    base_delta = max(0.006, min(0.12, math.sqrt(1.0 / target_q)))
    eta_candidates = [radius_eff_nm * base_delta * factor for factor in (0.25, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0)]
    gap_values = [14.0, 18.0]
    inner_shift_values = [0.0, 10.0, -10.0]
    coupler_profiles = [
        {"screen_aperture_width_nm": 140.0, "screen_aperture_extra_length_nm": 180.0, "gold_thickness_nm": 35.0},
        {"screen_aperture_width_nm": 115.0, "screen_aperture_extra_length_nm": 160.0, "gold_thickness_nm": 45.0},
        {"screen_aperture_width_nm": 90.0, "screen_aperture_extra_length_nm": 140.0, "gold_thickness_nm": 55.0},
        {"screen_aperture_width_nm": 34.0, "screen_aperture_extra_length_nm": 70.0, "gold_thickness_nm": 80.0},
        {"screen_aperture_width_nm": 38.0, "screen_aperture_extra_length_nm": 78.0, "gold_thickness_nm": 70.0},
        {"screen_aperture_width_nm": 30.0, "screen_aperture_extra_length_nm": 64.0, "gold_thickness_nm": 80.0},
        {"screen_aperture_width_nm": 42.0, "screen_aperture_extra_length_nm": 86.0, "gold_thickness_nm": 70.0},
        {"screen_aperture_width_nm": 26.0, "screen_aperture_extra_length_nm": 58.0, "gold_thickness_nm": 90.0},
    ]
    candidates = []
    index = 0
    replay_profiles = [
        {
            "eta_nm": 6.601438090,
            "base_gap_nm": 14.0,
            "inner_outer_shift_nm": -10.0,
            "screen_aperture_width_nm": 36.0,
            "screen_aperture_extra_length_nm": 110.0,
            "gold_thickness_nm": 90.0,
        }
    ]
    for replay in replay_profiles:
        theory = estimate_candidate_theory_fields(
            replay["eta_nm"],
            replay["base_gap_nm"],
            replay["inner_outer_shift_nm"],
            screen_width_nm=replay["screen_aperture_width_nm"],
            gold_thickness_nm=replay["gold_thickness_nm"],
        )
        row = {
            "index": index,
            "eta_nm": float(replay["eta_nm"]),
            "base_gap_nm": float(replay["base_gap_nm"]),
            "inner_outer_shift_nm": float(replay["inner_outer_shift_nm"]),
            "dimensionless_delta": theory["dimensionless_delta"],
            "relative_q_rad": theory["relative_q_rad"],
            "gap_angle_deg": theory["gap_angle_deg"],
            "lambda0_estimate_nm": theory["lambda0_estimate_nm"],
            "coupling_hint": theory["coupling_hint"],
            "screen_aperture_width_nm": replay["screen_aperture_width_nm"],
            "screen_aperture_extra_length_nm": replay["screen_aperture_extra_length_nm"],
            "gold_thickness_nm": replay["gold_thickness_nm"],
        }
        candidates.append(row)
        index += 1
    for profile in coupler_profiles:
        for eta in eta_candidates:
            for gap in gap_values:
                for inner_shift in inner_shift_values:
                    theory = estimate_candidate_theory_fields(
                        eta,
                        gap,
                        inner_shift,
                        screen_width_nm=profile["screen_aperture_width_nm"],
                        gold_thickness_nm=profile["gold_thickness_nm"],
                    )
                    row = {
                        "index": index,
                        "eta_nm": float(eta),
                        "base_gap_nm": float(gap),
                        "inner_outer_shift_nm": float(inner_shift),
                        "dimensionless_delta": theory["dimensionless_delta"],
                        "relative_q_rad": theory["relative_q_rad"],
                        "gap_angle_deg": theory["gap_angle_deg"],
                        "lambda0_estimate_nm": theory["lambda0_estimate_nm"],
                        "coupling_hint": theory["coupling_hint"],
                    }
                    row.update(profile)
                    candidates.append(row)
                    index += 1
    if max_trials is not None:
        candidates = candidates[: int(max_trials)]
    return candidates


def candidate_stem(candidate):
    return "{:04d}_eta{:.1f}_gap{:.1f}_inner{:+.1f}".format(
        int(candidate["index"]),
        float(candidate["eta_nm"]),
        float(candidate["base_gap_nm"]),
        float(candidate["inner_outer_shift_nm"]),
    ).replace(".", "d").replace("+", "p").replace("-", "m")


def prepare_run_dir(mode, explicit_run_dir=None):
    root = STRUCTURE_ROOT / "results" / PERTURBATION_NAME
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
        "field_csv": run_dir / "06_field_csv",
        "field_png": run_dir / "07_field_png",
    }
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def write_candidates_csv(path, candidates):
    fields = [
        "index",
        "eta_nm",
        "base_gap_nm",
        "inner_outer_shift_nm",
        "dimensionless_delta",
        "relative_q_rad",
        "gap_angle_deg",
        "lambda0_estimate_nm",
        "screen_aperture_width_nm",
        "screen_aperture_extra_length_nm",
        "gold_thickness_nm",
        "coupling_hint",
    ]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in candidates:
            writer.writerow({key: row.get(key, "") for key in fields})


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


def _dataset_get(result, key, default=None):
    if isinstance(result, dict):
        return result.get(key, default)
    try:
        return result[key]
    except Exception:
        return getattr(result, key, default)


def extract_field_spectrum(fdtd, monitor_name):
    result = None
    try:
        result = fdtd.getresult(monitor_name, "E")
    except Exception:
        result = None

    wl = _dataset_get(result, "lambda", None) if result is not None else None
    if wl is None:
        wl = _dataset_get(result, "wavelength", None) if result is not None else None
    if wl is None:
        f = _dataset_get(result, "f", None) if result is not None else None
        if f is not None:
            wl = C0 / np.asarray(f, dtype=float)

    e2 = _dataset_get(result, "E2", None) if result is not None else None
    if e2 is None:
        ex = _dataset_get(result, "Ex", None) if result is not None else None
        ey = _dataset_get(result, "Ey", None) if result is not None else None
        ez = _dataset_get(result, "Ez", None) if result is not None else None
        if ex is not None and ey is not None and ez is not None:
            e2 = np.abs(np.asarray(ex)) ** 2 + np.abs(np.asarray(ey)) ** 2 + np.abs(np.asarray(ez)) ** 2
    if e2 is None:
        try:
            ex = fdtd.getdata(monitor_name, "Ex")
            ey = fdtd.getdata(monitor_name, "Ey")
            ez = fdtd.getdata(monitor_name, "Ez")
            e2 = np.abs(np.asarray(ex)) ** 2 + np.abs(np.asarray(ey)) ** 2 + np.abs(np.asarray(ez)) ** 2
        except Exception:
            e2 = None
    if wl is None:
        try:
            wl = C0 / np.asarray(fdtd.getdata(monitor_name, "f"), dtype=float)
        except Exception:
            wl = None
    if wl is None or e2 is None:
        raise RuntimeError("field monitor result is missing wavelength or E2 data: {}".format(monitor_name))

    wl = np.asarray(wl, dtype=float).reshape(-1)
    e2 = np.asarray(e2, dtype=float)
    if e2.ndim == 1:
        spectrum = e2.reshape(-1)
    else:
        nf = e2.shape[-1]
        spectrum = np.nanmax(e2.reshape(-1, nf), axis=0)
    n = min(wl.size, spectrum.size)
    wl = wl[:n]
    spectrum = spectrum[:n]
    order = np.argsort(wl)
    return wl[order], spectrum[order], e2


def transmission_to_gui_abs2(transmission):
    tr = np.asarray(transmission).reshape(-1)
    if tr.size == 0:
        return np.asarray([], dtype=float), "empty_T"
    return (np.abs(tr) ** 2).astype(float), "gui_abs2_T"


def scalar_spectrum_metrics(wavelength_m, spectrum, metric_basis="scalar", target=None):
    wl_nm = np.asarray(wavelength_m, dtype=float).reshape(-1) / NM
    power = np.asarray(spectrum, dtype=float).reshape(-1)
    n = min(wl_nm.size, power.size)
    if n < 20:
        return {"status": "too_few_points", "accepted": False, "metric_basis": metric_basis}
    wl_nm = wl_nm[:n]
    power = power[:n]
    if not np.all(np.isfinite(power)):
        return {"status": "nan_or_inf", "accepted": False, "metric_basis": metric_basis}

    peak_idx = int(np.nanargmax(power))
    peak = float(power[peak_idx])
    peak_nm = float(wl_nm[peak_idx])
    edge_margin = min(abs(peak_nm - float(wl_nm[0])), abs(float(wl_nm[-1]) - peak_nm))

    exclude_half_width = max(18.0, 0.035 * (float(wl_nm[-1]) - float(wl_nm[0])))
    offband_mask = np.abs(wl_nm - peak_nm) > exclude_half_width
    offband = power[offband_mask] if np.any(offband_mask) else power
    offband_median = float(np.nanmedian(offband))
    offband_p95 = float(np.nanpercentile(offband, 95))
    offband_local_peak_count = 0
    offband_local_peak_max = 0.0
    if np.any(offband_mask):
        off_wl = wl_nm[offband_mask]
        off_power = power[offband_mask]
        if off_power.size >= 3:
            local = []
            threshold = max(float(np.nanmedian(off_power)) + 0.004, 0.01)
            for i in range(1, off_power.size - 1):
                if off_power[i] > off_power[i - 1] and off_power[i] > off_power[i + 1] and off_power[i] > threshold:
                    local.append(float(off_power[i]))
            offband_local_peak_count = len(local)
            offband_local_peak_max = float(max(local)) if local else 0.0
    baseline = float(np.nanpercentile(offband, 20))
    half = baseline + 0.5 * max(peak - baseline, 0.0)

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

    if left_nm is None or right_nm is None:
        fwhm_nm = float("inf")
    else:
        fwhm_nm = max(0.0, float(right_nm - left_nm))

    contrast = peak / max(offband_p95, 1e-12)
    accepted = False
    score = float(peak)
    if target:
        accepted = (
            peak >= target["peak_min"]
            and peak <= target.get("peak_max", float("inf"))
            and offband_p95 <= target["offband_p95_max"]
            and offband_local_peak_max <= target.get("offband_local_peak_max", float("inf"))
            and offband_local_peak_count <= target.get("offband_local_peak_count_max", 999999)
            and fwhm_nm <= target["fwhm_max_nm"]
            and contrast >= target["contrast_min"]
            and edge_margin >= target["edge_margin_nm"]
        )
        score = (
            2.5 * min(peak / target["peak_min"], 2.0)
            + 2.0 * min(contrast / target["contrast_min"], 2.0)
            - 1.8 * min(fwhm_nm / target["fwhm_max_nm"], 5.0)
            - 2.5 * min(offband_p95 / target["offband_p95_max"], 5.0)
        )
        if edge_margin < target["edge_margin_nm"]:
            score -= 2.0
        if peak > target.get("peak_max", float("inf")):
            score -= 10.0 * (peak - target["peak_max"])
        if offband_local_peak_max > target.get("offband_local_peak_max", float("inf")):
            score -= 3.0
        if offband_local_peak_count > target.get("offband_local_peak_count_max", 999999):
            score -= 1.0 * (offband_local_peak_count - target["offband_local_peak_count_max"])

    status = "target_hit" if accepted else "candidate"
    if target and peak > target.get("peak_max", float("inf")):
        status = "rejected_nonphysical_peak_gt_1"
    elif target and (
        offband_local_peak_max > target.get("offband_local_peak_max", float("inf"))
        or offband_local_peak_count > target.get("offband_local_peak_count_max", 999999)
    ):
        status = "rejected_oscillatory_background"

    return {
        "status": status,
        "accepted": bool(accepted),
        "metric_basis": metric_basis,
        "peak_T": peak,
        "peak_abs2": peak,
        "peak_nm": peak_nm,
        "baseline_T": baseline,
        "baseline_abs2": baseline,
        "offband_median_T": offband_median,
        "offband_median_abs2": offband_median,
        "offband_p95_T": offband_p95,
        "offband_p95_abs2": offband_p95,
        "offband_local_peak_count": int(offband_local_peak_count),
        "offband_local_peak_max": float(offband_local_peak_max),
        "contrast_vs_p95": float(contrast),
        "fwhm_nm": float(fwhm_nm),
        "edge_margin_nm": float(edge_margin),
        "score": float(score),
    }


def interpolate_crossing(x0, y0, x1, y1, target):
    if abs(y1 - y0) < 1e-30:
        return x0
    t = (target - y0) / (y1 - y0)
    t = max(0.0, min(1.0, float(t)))
    return x0 + t * (x1 - x0)


def spectrum_metrics(wavelength_m, transmission):
    power, metric_basis = transmission_to_gui_abs2(transmission)
    return scalar_spectrum_metrics(wavelength_m, power, metric_basis=metric_basis, target=TARGETS)


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
        rels.append(
            '<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{}.xml"/>'.format(
                idx, idx
            )
        )
        overrides.append(
            '<Override PartName="/xl/worksheets/sheet{}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.format(
                idx
            )
        )
    wb_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{}</sheets></workbook>'
    ).format("".join(wb_sheets))
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{}</Relationships>'
    ).format("".join(rels))
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    ctype = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        "{}</Types>"
    ).format("".join(overrides))
    with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ctype)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", wb_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        for idx, (_, rows) in enumerate(sheets, start=1):
            zf.writestr("xl/worksheets/sheet{}.xml".format(idx), xlsx_sheet_xml(rows))


def save_transmission_xlsx(path, wavelength_m, transmission, candidate, metrics):
    wl_nm = np.asarray(wavelength_m).reshape(-1) / NM
    tr = np.asarray(transmission).reshape(-1)
    t_abs2_gui, _ = transmission_to_gui_abs2(tr)
    t_real_power_check = np.maximum(np.real(tr).astype(float), 0.0)
    rows = [["wavelength_nm", "T_abs2_gui", "T_real_raw", "T_imag_raw", "T_real_power_check"]]
    for wl, val, abs2_gui, real_power in zip(wl_nm, tr, t_abs2_gui, t_real_power_check):
        rows.append([float(wl), float(abs2_gui), float(np.real(val)), float(np.imag(val)), float(real_power)])
    meta = [["key", "value"]]
    for key in sorted(candidate.keys()):
        meta.append([key, candidate[key]])
    for key in sorted(metrics.keys()):
        meta.append(["metric_" + key, metrics[key]])
    save_xlsx(path, [("transmission_abs2_gui", rows), ("metadata", meta)])


def save_plot(path, wavelength_m, transmission, candidate, metrics):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    wl_nm = np.asarray(wavelength_m).reshape(-1) / NM
    power, _ = transmission_to_gui_abs2(transmission)
    fig, ax = plt.subplots(figsize=(8.6, 5.2), dpi=170)
    ax.plot(wl_nm, power, linewidth=1.6, color="#155e75")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Abs(T)^2")
    title = "D4 diagonal detune eta={:.1f} nm, gap={:.1f} nm".format(
        float(candidate["eta_nm"]), float(candidate["base_gap_nm"])
    )
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    if "peak_nm" in metrics:
        ax.axvline(metrics["peak_nm"], color="#c2410c", alpha=0.65, linewidth=1.0)
        ax.text(
            0.02,
            0.96,
            "peak Abs(T)^2={:.4g} @ {:.2f} nm\nFWHM={:.3g} nm\np95 offband={:.4g}".format(
                metrics.get("peak_abs2", metrics.get("peak_T", float("nan"))),
                metrics.get("peak_nm", float("nan")),
                metrics.get("fwhm_nm", float("nan")),
                metrics.get("offband_p95_abs2", metrics.get("offband_p95_T", float("nan"))),
            ),
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            bbox=dict(facecolor="white", alpha=0.84, edgecolor="#cccccc"),
        )
    fig.tight_layout()
    fig.savefig(str(path))
    plt.close(fig)
    return True


def save_field_csv(path, wavelength_m, spectrum, candidate, metrics):
    wl_nm = np.asarray(wavelength_m).reshape(-1) / NM
    spectrum = np.asarray(spectrum).reshape(-1)
    rows = [["wavelength_nm", "E2_max"]]
    for wl, val in zip(wl_nm, spectrum):
        rows.append([float(wl), float(val)])
    meta = [["key", "value"]]
    for key in sorted(candidate.keys()):
        meta.append([key, candidate[key]])
    for key in sorted(metrics.keys()):
        meta.append(["metric_" + key, metrics[key]])
    save_xlsx(path, [("field_spectrum", rows), ("metadata", meta)])


def save_field_plots(spectrum_path, map_path, wavelength_m, spectrum, field_e2, candidate, metrics):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    wl_nm = np.asarray(wavelength_m).reshape(-1) / NM
    spectrum = np.asarray(spectrum).reshape(-1)
    fig, ax = plt.subplots(figsize=(8.6, 5.2), dpi=170)
    ax.plot(wl_nm, spectrum, linewidth=1.6, color="#1d4ed8")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Max(|E|^2)")
    title = "Field monitor, eta={:.1f} nm, gap={:.1f} nm".format(float(candidate["eta_nm"]), float(candidate["base_gap_nm"]))
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    if "peak_nm" in metrics:
        ax.axvline(metrics["peak_nm"], color="#c2410c", alpha=0.65, linewidth=1.0)
        ax.text(
            0.02,
            0.96,
            "peak Max(|E|^2)={:.4g} @ {:.2f} nm\nFWHM={:.3g} nm\np95 offband={:.4g}".format(
                metrics.get("peak_abs2", metrics.get("peak_T", float("nan"))),
                metrics.get("peak_nm", float("nan")),
                metrics.get("fwhm_nm", float("nan")),
                metrics.get("offband_p95_abs2", metrics.get("offband_p95_T", float("nan"))),
            ),
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            bbox=dict(facecolor="white", alpha=0.84, edgecolor="#cccccc"),
        )
    fig.tight_layout()
    fig.savefig(str(spectrum_path))
    plt.close(fig)

    e2 = np.asarray(field_e2, dtype=float)
    if e2.ndim >= 3:
        peak_idx = int(np.nanargmax(spectrum))
        if e2.ndim == 3:
            field_map = np.asarray(e2[:, :, peak_idx], dtype=float)
        else:
            field_map = np.squeeze(np.asarray(e2[..., peak_idx], dtype=float))
            if field_map.ndim > 2:
                field_map = np.nanmax(field_map, axis=-1)
    elif e2.ndim == 2:
        field_map = e2
    else:
        field_map = e2.reshape(1, -1)

    fig, ax = plt.subplots(figsize=(6.4, 5.8), dpi=170)
    im = ax.imshow(np.asarray(field_map, dtype=float), origin="lower", cmap="magma", aspect="auto")
    ax.set_title("Field map at spectral peak")
    ax.set_xlabel("x index")
    ax.set_ylabel("y index")
    fig.colorbar(im, ax=ax, label="|E|^2")
    fig.tight_layout()
    fig.savefig(str(map_path))
    plt.close(fig)
    return True


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_candidate(lumapi, candidate, mode, folders, runtime_overrides=None, monitor_mode="power"):
    config = make_config(candidate, mode)
    config = apply_runtime_overrides(config, runtime_overrides)
    config.update(candidate)
    config["screen_aperture_length_nm"] = (
        float(config["outer_ring_width_nm"]) + float(config["screen_aperture_extra_length_nm"])
    )
    stem = candidate_stem(candidate)
    fsp_path = folders["fsp"] / (stem + ".fsp")
    xlsx_path = folders["excel"] / (stem + "_transmission_abs2.xlsx")
    png_path = folders["png"] / (stem + "_transmission_abs2.png")
    field_xlsx_path = folders["field_csv"] / (stem + "_field_E2.xlsx")
    field_png_path = folders["field_png"] / (stem + "_field_E2_spectrum.png")
    field_map_png_path = folders["field_png"] / (stem + "_field_E2_map.png")
    json_path = folders["logs"] / (stem + "_metrics.json")
    start = time.time()
    fdtd = lumapi.FDTD(hide=True)
    wavelength_m = None
    transmission = None
    field_response = None
    field_e2 = None
    monitor_name = "E_field" if monitor_mode == "field" else "T"
    try:
        build_candidate_geometry(fdtd, config, monitor_mode=monitor_mode, monitor_name=monitor_name)
        fdtd.save(str(fsp_path))
        fdtd.run()
        if monitor_mode == "field":
            wavelength_m, field_response, field_e2 = extract_field_spectrum(fdtd, monitor_name)
            metrics = scalar_spectrum_metrics(wavelength_m, field_response, metric_basis="max_E2", target=None)
            metrics["field_monitor_name"] = monitor_name
            metrics["field_profile_shape"] = list(np.asarray(field_e2).shape)
        else:
            wavelength_m, transmission = extract_transmission(fdtd)
            metrics = spectrum_metrics(wavelength_m, transmission)
        fdtd.save(str(fsp_path))
    except Exception as exc:
        metrics = {"status": "failed", "accepted": False, "error": repr(exc)}
    finally:
        try:
            fdtd.close()
        except Exception:
            pass

    elapsed_s = time.time() - start
    metrics["elapsed_s"] = elapsed_s
    metrics["fsp"] = str(fsp_path)
    if monitor_mode == "field":
        metrics["xlsx"] = str(field_xlsx_path)
        metrics["png"] = str(field_png_path)
        metrics["map_png"] = str(field_map_png_path)
        if wavelength_m is not None and field_response is not None:
            save_field_csv(field_xlsx_path, wavelength_m, field_response, candidate, metrics)
            save_field_plots(field_png_path, field_map_png_path, wavelength_m, field_response, field_e2, candidate, metrics)
    else:
        metrics["xlsx"] = str(xlsx_path)
        metrics["png"] = str(png_path)
        if wavelength_m is not None and transmission is not None:
            save_transmission_xlsx(xlsx_path, wavelength_m, transmission, candidate, metrics)
            save_plot(png_path, wavelength_m, transmission, candidate, metrics)
    write_json(json_path, {"candidate": candidate, "config": config, "metrics": metrics})
    return metrics


def manifest_fields():
    return [
        "index",
        "eta_nm",
        "base_gap_nm",
        "inner_outer_shift_nm",
        "screen_aperture_width_nm",
        "screen_aperture_extra_length_nm",
        "gold_thickness_nm",
        "coupling_hint",
        "dimensionless_delta",
        "relative_q_rad",
        "gap_angle_deg",
        "lambda0_estimate_nm",
        "status",
        "accepted",
        "score",
        "metric_basis",
        "peak_T",
        "peak_abs2",
        "peak_nm",
        "fwhm_nm",
        "offband_p95_T",
        "offband_p95_abs2",
        "contrast_vs_p95",
        "edge_margin_nm",
        "elapsed_s",
        "fsp",
        "xlsx",
        "png",
        "error",
    ]


def append_manifest(path, candidate, metrics):
    exists = Path(path).exists()
    fields = manifest_fields()
    with Path(path).open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        row = {}
        for key in fields:
            row[key] = candidate.get(key, metrics.get(key, ""))
        writer.writerow(row)


def write_overview(run_dir, seed_path, candidates, mode):
    lines = [
        "# {} - {}".format(STRUCTURE_NAME, PERTURBATION_NAME),
        "",
        "- 运行模式: {}".format(mode),
        "- 原始母版 FSP: {}".format(seed_path),
        "- 候选数量: {}".format(len(candidates)),
        "- 对称路径: D4 -> C2/C1，对角裂缝成对失谐打开准 BIC 透射通道。",
        "- 目标: 高峰值透射、低带外透射、窄 FWHM、峰位不贴扫描边界。",
        "",
        "## 公式来源",
        "- 环形暗模中心波长估计: lambda0 ~= 2*pi*n_eff*R_eff/m。",
        "- 当前取 m = {}, n_eff = {}，目标 lambda0 = {} nm，因此 R_eff = {:.3f} nm。".format(
            THEORY_MODEL["dark_azimuthal_order"],
            THEORY_MODEL["effective_index_guess"],
            THEORY_MODEL["target_lambda_nm"],
            BASE_CONFIG["outer_effective_radius_nm"],
        ),
        "- 准 BIC 辐射泄漏: gamma_rad proportional to delta^2，因此 Q_rad proportional to 1/delta^2。",
        "- delta = eta/R_eff，eta 为对角裂缝的成对失谐长度。",
        "",
        "## 判据",
    ]
    for key in sorted(TARGETS.keys()):
        lines.append("- {}: {}".format(key, TARGETS[key]))
    (run_dir / "结构状态说明.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description=PERTURBATION_NAME)
    parser.add_argument("--mode", choices=["preview", "test", "full"], default="preview")
    parser.add_argument("--study", choices=["search", "validation", "optimize", "field"], default="search")
    parser.add_argument("--monitor-mode", choices=["power", "field"], default="power")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--max-trials", type=int, default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--build-seed-only", action="store_true")
    return parser.parse_args()


def selected_mode(args):
    if args.full:
        return "full"
    if args.test:
        return "test"
    if args.preview:
        return "preview"
    return args.mode


def validation_run_name(profile):
    return "validation_{}_{}".format(profile["name"], chinese_timestamp())


def field_run_name():
    return "field_analysis_{}".format(chinese_timestamp())


def candidate_from_reference():
    return dict(VALIDATION_REFERENCE_CANDIDATE)


def validation_batch_summary(run_dir, profiles, outputs):
    summary = {
        "study": "validation",
        "profiles": profiles,
        "outputs": outputs,
    }
    write_json(run_dir / "04_logs" / "validation_summary.json", summary)


def field_batch_summary(run_dir, result):
    summary = {
        "study": "field",
        "result": result,
    }
    write_json(run_dir / "04_logs" / "field_summary.json", summary)


def run_validation_suite(lumapi, base_candidate, mode, root_run_dir):
    outputs = []
    for idx, profile in enumerate(VALIDATION_PROFILES, start=1):
        case_dir = root_run_dir / "{:02d}_{}".format(idx, profile["name"])
        case_dir.mkdir(parents=True, exist_ok=True)
        folders = ensure_folders(case_dir)
        candidate = dict(base_candidate)
        candidate["study_case"] = profile["name"]
        print("[validation {}/{}] {}".format(idx, len(VALIDATION_PROFILES), profile["name"]))
        metrics = run_candidate(
            lumapi,
            candidate,
            mode,
            folders,
            runtime_overrides=profile,
            monitor_mode="power",
        )
        outputs.append({"profile": profile, "candidate": candidate, "metrics": metrics, "run_dir": str(case_dir)})
    validation_batch_summary(root_run_dir, VALIDATION_PROFILES, outputs)
    return outputs


def run_field_analysis(lumapi, base_candidate, mode, root_run_dir):
    case_dir = root_run_dir / "field_case"
    case_dir.mkdir(parents=True, exist_ok=True)
    folders = ensure_folders(case_dir)
    candidate = dict(base_candidate)
    candidate["study_case"] = "field_case"
    metrics = run_candidate(
        lumapi,
        candidate,
        mode,
        folders,
        runtime_overrides=FIELD_ANALYSIS_PROFILE,
        monitor_mode="field",
    )
    field_batch_summary(root_run_dir, {"candidate": candidate, "metrics": metrics, "run_dir": str(case_dir)})
    return metrics


def optimization_batch_summary(run_dir, outputs):
    summary = {
        "study": "optimize",
        "mechanism": "increase screen aperture radial overlap to tune external coupling toward critical coupling",
        "runtime": OPTIMIZATION_RUNTIME,
        "outputs": outputs,
    }
    write_json(run_dir / "04_logs" / "optimization_summary.json", summary)


def run_optimization_suite(lumapi, base_candidate, mode, root_run_dir):
    outputs = []
    for idx, update in enumerate(OPTIMIZATION_CANDIDATES, start=1):
        case_name = update["study_case"]
        case_dir = root_run_dir / "{:02d}_{}".format(idx, case_name)
        case_dir.mkdir(parents=True, exist_ok=True)
        folders = ensure_folders(case_dir)
        candidate = dict(base_candidate)
        candidate.update(update)
        print("[optimize {}/{}] {}".format(idx, len(OPTIMIZATION_CANDIDATES), case_name))
        metrics = run_candidate(
            lumapi,
            candidate,
            mode,
            folders,
            runtime_overrides=OPTIMIZATION_RUNTIME,
            monitor_mode="power",
        )
        outputs.append({"candidate": candidate, "metrics": metrics, "run_dir": str(case_dir)})
    optimization_batch_summary(root_run_dir, outputs)
    return outputs


def main():
    args = parse_args()
    mode = selected_mode(args)
    if args.max_trials is None and mode == "test":
        max_trials = TEST_TRIAL_COUNT
    else:
        max_trials = args.max_trials

    candidates = build_candidates(max_trials=max_trials)
    run_dir = prepare_run_dir(mode, args.run_dir)
    folders = ensure_folders(run_dir)

    try:
        with single_fdtd_session_guard(run_dir):
            lumapi = import_lumapi()
            seed_path = save_seed_fsp(lumapi)
            print("原始母版 FSP 已保存: {}".format(seed_path))
            if args.build_seed_only:
                return 0

            shutil.copy2(str(seed_path), str(folders["work"] / "source_seed.fsp"))
            write_candidates_csv(folders["plan"] / "candidates.csv", candidates)
            write_overview(run_dir, seed_path, candidates, mode)
            print("输出批次目录: {}".format(run_dir))
            print("候选计划已保存: {}".format(folders["plan"] / "candidates.csv"))

            if mode == "preview":
                print("预览模式结束：已生成母版 FSP 和候选计划，没有运行真实 FDTD。")
                return 0

            manifest_path = folders["logs"] / "manifest.csv"
            best = None
            for done, candidate in enumerate(candidates, start=1):
                print(
                    "[{}/{}] eta={:.1f} nm, gap={:.1f} nm, inner_shift={:+.1f} nm".format(
                        done,
                        len(candidates),
                        float(candidate["eta_nm"]),
                        float(candidate["base_gap_nm"]),
                        float(candidate["inner_outer_shift_nm"]),
                    )
                )
                metrics = run_candidate(lumapi, candidate, mode, folders)
                append_manifest(manifest_path, candidate, metrics)
                score = metrics.get("score", -1e9)
                if best is None or float(score) > float(best["metrics"].get("score", -1e9)):
                    best = {"candidate": dict(candidate), "metrics": dict(metrics)}
                    write_json(folders["logs"] / "best_so_far.json", best)
                print(
                    "  status={} score={} peak_abs2={} fwhm={} offband_p95_abs2={}".format(
                        metrics.get("status"),
                        metrics.get("score", ""),
                        metrics.get("peak_abs2", metrics.get("peak_T", "")),
                        metrics.get("fwhm_nm", ""),
                        metrics.get("offband_p95_abs2", metrics.get("offband_p95_T", "")),
                    )
                )
                if metrics.get("accepted"):
                    write_json(folders["logs"] / "accepted_candidate.json", {"candidate": candidate, "metrics": metrics})
                    print("达到目标判据，停止搜索。")
                    break

            write_json(folders["logs"] / "run_summary.json", {"mode": mode, "best": best, "targets": TARGETS})
            print("完成。manifest: {}".format(manifest_path))
            return 0
    except RuntimeError as exc:
        if "当前仿真线程直接退出" in str(exc):
            print(str(exc))
            return 2
        raise


def main():
    args = parse_args()
    mode = selected_mode(args)

    if args.study == "validation":
        run_dir = prepare_run_dir("validation", args.run_dir)
        folders = ensure_folders(run_dir)
        with single_fdtd_session_guard(run_dir):
            lumapi = import_lumapi()
            seed_path = save_seed_fsp(lumapi)
            print("原始母版 FSP 已保存: {}".format(seed_path))
            if args.build_seed_only:
                return 0
            shutil.copy2(str(seed_path), str(folders["work"] / "source_seed.fsp"))
            base_candidate = candidate_from_reference()
            run_validation_suite(lumapi, base_candidate, mode, run_dir)
            print("收敛验证完成: {}".format(run_dir))
            return 0

    if args.study == "field":
        run_dir = prepare_run_dir("field", args.run_dir)
        folders = ensure_folders(run_dir)
        with single_fdtd_session_guard(run_dir):
            lumapi = import_lumapi()
            seed_path = save_seed_fsp(lumapi)
            print("原始母版 FSP 已保存: {}".format(seed_path))
            if args.build_seed_only:
                return 0
            shutil.copy2(str(seed_path), str(folders["work"] / "source_seed.fsp"))
            base_candidate = candidate_from_reference()
            metrics = run_field_analysis(lumapi, base_candidate, mode, run_dir)
            print("场分析完成: {}".format(run_dir))
            print("peak_nm={} peak_E2={}".format(metrics.get("peak_nm"), metrics.get("peak_abs2")))
            return 0

    if args.study == "optimize":
        run_dir = prepare_run_dir("optimize", args.run_dir)
        folders = ensure_folders(run_dir)
        with single_fdtd_session_guard(run_dir):
            lumapi = import_lumapi()
            seed_path = save_seed_fsp(lumapi)
            print("原始母版 FSP 已保存: {}".format(seed_path))
            if args.build_seed_only:
                return 0
            shutil.copy2(str(seed_path), str(folders["work"] / "source_seed.fsp"))
            base_candidate = candidate_from_reference()
            run_optimization_suite(lumapi, base_candidate, mode, run_dir)
            print("优化验证完成: {}".format(run_dir))
            return 0

    if args.max_trials is None and mode == "test":
        max_trials = TEST_TRIAL_COUNT
    else:
        max_trials = args.max_trials

    candidates = build_candidates(max_trials=max_trials)
    run_dir = prepare_run_dir(mode, args.run_dir)
    folders = ensure_folders(run_dir)

    with single_fdtd_session_guard(run_dir):
        lumapi = import_lumapi()
        seed_path = save_seed_fsp(lumapi)
        print("原始母版 FSP 已保存: {}".format(seed_path))
        if args.build_seed_only:
            return 0

        shutil.copy2(str(seed_path), str(folders["work"] / "source_seed.fsp"))
        write_candidates_csv(folders["plan"] / "candidates.csv", candidates)
        write_overview(run_dir, seed_path, candidates, mode)
        print("输出批次目录: {}".format(run_dir))
        print("候选计划已保存: {}".format(folders["plan"] / "candidates.csv"))

        if mode == "preview":
            print("预览模式结束：已生成母版 FSP 和候选计划，没有运行真实 FDTD。")
            return 0

        manifest_path = folders["logs"] / "manifest.csv"
        best = None
        for done, candidate in enumerate(candidates, start=1):
            print(
                "[{}/{}] eta={:.1f} nm, gap={:.1f} nm, inner_shift={:+.1f} nm".format(
                    done,
                    len(candidates),
                    float(candidate["eta_nm"]),
                    float(candidate["base_gap_nm"]),
                    float(candidate["inner_outer_shift_nm"]),
                )
            )
            metrics = run_candidate(lumapi, candidate, mode, folders, monitor_mode=args.monitor_mode)
            append_manifest(manifest_path, candidate, metrics)
            score = metrics.get("score", -1e9)
            if best is None or float(score) > float(best["metrics"].get("score", -1e9)):
                best = {"candidate": dict(candidate), "metrics": dict(metrics)}
                write_json(folders["logs"] / "best_so_far.json", best)
            print(
                "  status={} score={} peak_abs2={} fwhm={} offband_p95_abs2={}".format(
                    metrics.get("status"),
                    metrics.get("score", ""),
                    metrics.get("peak_abs2", metrics.get("peak_T", "")),
                    metrics.get("fwhm_nm", ""),
                    metrics.get("offband_p95_abs2", metrics.get("offband_p95_T", "")),
                )
            )
            if metrics.get("accepted"):
                write_json(folders["logs"] / "accepted_candidate.json", {"candidate": candidate, "metrics": metrics})
                print("已达到目标判据，停止搜索。")
                break

        write_json(folders["logs"] / "run_summary.json", {"mode": mode, "best": best, "targets": TARGETS})
        print("完成。manifest: {}".format(manifest_path))
        return 0


if __name__ == "__main__":
    sys.exit(main())
