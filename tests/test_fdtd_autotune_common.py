# -*- coding: utf-8 -*-
import numpy as np

from fdtd_autotune_common import evaluate_spectrum_quality, next_retry_config


def test_tmax_gt_limit_triggers_retry():
    wl = np.linspace(1.2e-6, 1.6e-6, 100)
    tr = np.ones(100) * np.sqrt(1.06)  # |T|^2 = 1.06 > 1.03
    q = evaluate_spectrum_quality(wl, tr, {"solver_status": 2}, {"QUALITY_T_LIMIT": 1.03})
    assert q["accepted"] is False
    assert "transmission_gt_limit" in q["flags"]


def test_nan_inf_triggers_retry():
    wl = np.linspace(1.2e-6, 1.6e-6, 100)
    tr = np.ones(100, dtype=float)
    tr[3] = np.nan
    tr[8] = np.inf
    q = evaluate_spectrum_quality(wl, tr, {"solver_status": 2}, {})
    assert q["accepted"] is False
    assert "nan_or_inf" in q["flags"]


def test_solver_status_3_triggers_diverged():
    wl = np.linspace(1.2e-6, 1.6e-6, 100)
    tr = np.ones(100) * 0.9
    q = evaluate_spectrum_quality(wl, tr, {"solver_status": 3}, {})
    assert q["accepted"] is False
    assert "diverged" in q["flags"]


def test_ripple_spectrum_triggers_retry():
    wl = np.linspace(1.2e-6, 1.6e-6, 600)
    base = 0.8
    ripple = 0.12 * np.sin(np.linspace(0, 220 * np.pi, 600))
    tr = np.sqrt(np.clip(base + ripple, 1e-6, None))
    q = evaluate_spectrum_quality(
        wl,
        tr,
        {"solver_status": 2},
        {"QUALITY_T_LIMIT": 1.03, "QUALITY_RIPPLE_LIMIT": 0.02, "QUALITY_MIN_POINTS": 20},
    )
    assert q["accepted"] is False
    assert "ripple_spectrum" in q["flags"]


def test_retry_not_decayed_or_t_gt_limit_prioritizes_time_and_shutoff():
    base = {
        "SIMULATION_TIME_FS": 70.0,
        "AUTO_SHUTOFF_MIN": 1e-5,
        "MESH_ACCURACY": 2,
        "DT_STABILITY_FACTOR": 0.99,
    }
    quality = {"flags": ["ended_by_simulation_time", "transmission_gt_limit"], "tmax": 1.10}
    new_cfg = next_retry_config(base, base, quality, 1)
    assert new_cfg["SIMULATION_TIME_FS"] > 70.0
    assert new_cfg["AUTO_SHUTOFF_MIN"] < 1e-5


def test_retry_diverged_prioritizes_lower_dt():
    base = {
        "SIMULATION_TIME_FS": 70.0,
        "AUTO_SHUTOFF_MIN": 1e-5,
        "MESH_ACCURACY": 2,
        "DT_STABILITY_FACTOR": 0.99,
    }
    quality = {"flags": ["diverged"], "tmax": ""}
    new_cfg = next_retry_config(base, base, quality, 1)
    assert new_cfg["DT_STABILITY_FACTOR"] <= 0.95


def test_first_t_gt_limit_retry_should_not_bump_mesh_immediately():
    base = {
        "SIMULATION_TIME_FS": 70.0,
        "AUTO_SHUTOFF_MIN": 1e-5,
        "MESH_ACCURACY": 2,
        "DT_STABILITY_FACTOR": 0.99,
    }
    quality = {"flags": ["transmission_gt_limit"], "tmax": 1.08}
    new_cfg = next_retry_config(base, base, quality, 1)
    assert new_cfg["MESH_ACCURACY"] == 2
