# -*- coding: utf-8 -*-
"""
FDTD autotune common module.
Python 3.6 compatible, no lumapi dependency, suitable for offline tests.
"""
from __future__ import print_function

import csv
from pathlib import Path

import numpy as np


def _float_or_none(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _int_or_none(value):
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except Exception:
        return None


def _is_adaptive_value(value):
    if value is None:
        return True
    text = str(value).strip().lower()
    return text in ("", "adaptive", "auto", "none", "null")


def normalize_autotune_config(config):
    """Normalize autotune runtime config and defaults."""
    config = dict(config or {})
    config.setdefault("AUTO_RETRY_ENABLED", True)

    raw_retry_mode = str(config.get("AUTO_RETRY_MODE", "") or "").strip().lower()
    raw_retry_max = config.get("AUTO_RETRY_MAX", None)
    if raw_retry_mode == "adaptive" or _is_adaptive_value(raw_retry_max):
        config["AUTO_RETRY_MODE"] = "adaptive"
        config["AUTO_RETRY_MAX"] = None
    else:
        parsed_max = _int_or_none(raw_retry_max)
        if parsed_max is None:
            config["AUTO_RETRY_MODE"] = "adaptive"
            config["AUTO_RETRY_MAX"] = None
        else:
            config["AUTO_RETRY_MODE"] = "fixed"
            config["AUTO_RETRY_MAX"] = max(0, parsed_max)

    config.setdefault("QUALITY_T_LIMIT", 1.03)
    config.setdefault("QUALITY_RIPPLE_LIMIT", 0.12)
    config.setdefault("QUALITY_MIN_POINTS", 20)

    config.setdefault("AUTO_RETRY_HARD_CAP", 8)
    config.setdefault("AUTO_RETRY_PATIENCE", 2)
    config.setdefault("AUTO_RETRY_MIN_IMPROVE", 0.15)
    config.setdefault("AUTO_RETRY_WEAK_IMPROVE", 0.03)
    config.setdefault("AUTO_RETRY_BUDGET_FACTOR", 4.0)
    config.setdefault("AUTO_RETRY_MIN_BUDGET_S", 180.0)
    config.setdefault("AUTO_RETRY_MAX_BUDGET_S", 3600.0)
    config.setdefault("AUTO_RETRY_TIME_BUDGET_S", None)
    config.setdefault("AUTO_RETRY_MAX_SINGLE_RUN_S", None)

    config.setdefault("AUTO_RETRY_MAX_MESH_ACCURACY", 5)
    config.setdefault("AUTO_RETRY_MIN_AUTO_SHUTOFF", 1e-9)
    config.setdefault("AUTO_RETRY_MIN_DT", 0.50)
    config.setdefault("AUTO_RETRY_TIME_GROWTH", 1.8)
    config.setdefault("AUTO_RETRY_TIME_GROWTH_STRONG", 2.5)
    config.setdefault("AUTO_RETRY_SHUTOFF_FACTOR", 0.1)
    return config


def clone_runtime_config(config):
    """Copy runtime config and maintain SIMULATION_TIME_FS/S mapping."""
    out = dict(config or {})
    if out.get("SIMULATION_TIME_FS") is None and out.get("SIMULATION_TIME_S") is not None:
        out["SIMULATION_TIME_FS"] = float(out["SIMULATION_TIME_S"]) * 1e15
    if out.get("SIMULATION_TIME_FS") is not None:
        out["SIMULATION_TIME_S"] = float(out["SIMULATION_TIME_FS"]) * 1e-15
    return out


def extract_solver_info(fdtd, fdtd_name):
    """Read solver status and autoshutoff level; return empty fields on failure."""
    info = {
        "solver_status": "",
        "solver_status_text": "unknown",
        "autoshutoff_final": "",
    }
    try:
        status = fdtd.getresult(fdtd_name, "status")
        if isinstance(status, dict):
            for key in ("status", "STATUS"):
                if key in status:
                    status = status[key]
                    break
        arr = np.asarray(status).reshape(-1)
        if arr.size:
            code = int(float(arr[-1]))
            info["solver_status"] = code
            info["solver_status_text"] = {
                0: "layout",
                1: "full_simulation_time",
                2: "auto_shutoff",
                3: "diverged",
            }.get(code, "unknown")
    except Exception:
        pass

    try:
        shut = fdtd.getresult(fdtd_name, "autoshutoff level")
        if isinstance(shut, dict):
            candidates = []
            for value in shut.values():
                try:
                    arr = np.asarray(value).reshape(-1)
                    if arr.size:
                        candidates.append(arr)
                except Exception:
                    pass
            if candidates:
                info["autoshutoff_final"] = float(candidates[-1][-1])
        else:
            arr = np.asarray(shut).reshape(-1)
            if arr.size:
                info["autoshutoff_final"] = float(arr[-1])
    except Exception:
        pass
    return info


def transmission_abs_power(transmission):
    return np.abs(np.asarray(transmission).reshape(-1)) ** 2


def moving_average(values, window):
    values = np.asarray(values, dtype=float).reshape(-1)
    n = values.size
    if n == 0:
        return values
    window = int(max(3, window))
    if window % 2 == 0:
        window += 1
    if window >= n:
        window = max(3, n // 2 * 2 - 1)
    if window < 3:
        return values.copy()
    kernel = np.ones(window, dtype=float) / float(window)
    return np.convolve(values, kernel, mode="same")


def estimate_ripple_score(power):
    y = np.asarray(power, dtype=float).reshape(-1)
    n = y.size
    if n < 20:
        return 0.0, 0
    window = max(7, int(n * 0.035))
    if window % 2 == 0:
        window += 1
    smooth = moving_average(y, window)
    start = min(window, n // 4)
    end = max(n - start, start + 1)
    yc = y[start:end]
    sc = smooth[start:end]
    resid = yc - sc
    amp = max(float(np.nanmax(y) - np.nanmin(y)), 1e-12)
    ripple_score = float(np.nanstd(resid) / amp)
    diff = np.diff(resid)
    sign_changes = int(np.sum(np.diff(np.sign(diff)) != 0)) if diff.size > 2 else 0
    return ripple_score, sign_changes


def evaluate_spectrum_quality(wavelength_m, transmission, solver_info, config):
    cfg = normalize_autotune_config(config)
    flags = []
    reasons = []
    wl = np.asarray(wavelength_m).reshape(-1) if wavelength_m is not None else np.asarray([])
    tr = np.asarray(transmission).reshape(-1) if transmission is not None else np.asarray([])
    n = min(wl.size, tr.size)

    if n < int(cfg.get("QUALITY_MIN_POINTS", 20)):
        flags.append("empty_or_too_few_points")
        reasons.append("too few spectrum points")
        return {
            "accepted": False,
            "status": "need_retry",
            "flags": flags,
            "reasons": reasons,
            "tmax": "",
            "tmin": "",
            "ripple_score": "",
            "sign_changes": "",
        }

    power = transmission_abs_power(tr[:n])
    if not np.all(np.isfinite(power)):
        flags.append("nan_or_inf")
        reasons.append("spectrum contains NaN or Inf")

    tmax = float(np.nanmax(power)) if power.size else float("nan")
    tmin = float(np.nanmin(power)) if power.size else float("nan")
    ripple_score, sign_changes = estimate_ripple_score(power)

    t_limit = float(cfg.get("QUALITY_T_LIMIT", 1.03))
    ripple_limit = float(cfg.get("QUALITY_RIPPLE_LIMIT", 0.12))

    solver_status = (solver_info or {}).get("solver_status")
    if solver_status == 3:
        flags.append("diverged")
        reasons.append("solver diverged")
    if solver_status == 1:
        flags.append("ended_by_simulation_time")
        reasons.append("ended by simulation time")

    if np.isfinite(tmax) and tmax > t_limit:
        flags.append("transmission_gt_limit")
        reasons.append("tmax {:.4g} exceeds {:.4g}".format(tmax, t_limit))

    if ripple_score > ripple_limit and sign_changes > max(8, int(0.08 * n)):
        flags.append("ripple_spectrum")
        reasons.append("strong ripple score {:.4g}".format(ripple_score))

    hard_fail_flags = set(["nan_or_inf", "diverged", "transmission_gt_limit", "ripple_spectrum"])
    need_retry = bool(hard_fail_flags.intersection(set(flags)))

    accepted = not need_retry
    status = "accepted" if accepted else "need_retry"
    if accepted and solver_status == 1:
        status = "accepted_with_warning"

    return {
        "accepted": accepted,
        "status": status,
        "flags": flags,
        "reasons": reasons,
        "tmax": tmax,
        "tmin": tmin,
        "ripple_score": ripple_score,
        "sign_changes": sign_changes,
    }


def compute_badness_score(quality, solver_info, config):
    cfg = normalize_autotune_config(dict(config or {}))
    quality = quality or {}
    solver_info = solver_info or {}
    if bool(quality.get("accepted")):
        return 0.0

    score = 0.0
    flags = set(quality.get("flags") or [])
    t_limit = float(cfg.get("QUALITY_T_LIMIT", 1.03))
    ripple_limit = float(cfg.get("QUALITY_RIPPLE_LIMIT", 0.12))
    tmax = _float_or_none(quality.get("tmax"))
    ripple = _float_or_none(quality.get("ripple_score"))
    solver_status = solver_info.get("solver_status")

    if "diverged" in flags or solver_status == 3:
        score += 10.0
    if "nan_or_inf" in flags:
        score += 8.0
    if "exception" in flags:
        score += 7.0
    if "transmission_gt_limit" in flags and tmax is not None:
        score += max(0.0, (tmax - t_limit) * 12.0)
    if "ripple_spectrum" in flags and ripple is not None:
        score += max(0.0, (ripple - ripple_limit) * 20.0)
    if "ended_by_simulation_time" in flags or solver_status == 1:
        score += 1.5
    if "empty_or_too_few_points" in flags:
        score += 3.0

    return max(0.0, float(score))


def init_retry_state(config):
    cfg = normalize_autotune_config(dict(config or {}))
    return {
        "mode": cfg.get("AUTO_RETRY_MODE"),
        "adaptive_limit": None,
        "time_spent_s": 0.0,
        "no_improve_count": 0,
        "last_badness": None,
        "best_badness": None,
        "last_decision_reason": "init",
    }


def estimate_adaptive_retry_limit(config, first_elapsed_s):
    cfg = normalize_autotune_config(dict(config or {}))
    hard_cap = max(0, int(float(cfg.get("AUTO_RETRY_HARD_CAP", 8))))
    if first_elapsed_s is None or first_elapsed_s <= 0:
        return min(hard_cap, 3)
    t = float(first_elapsed_s)
    if t <= 60:
        return min(hard_cap, 6)
    if t <= 180:
        return min(hard_cap, 5)
    if t <= 600:
        return min(hard_cap, 3)
    if t <= 1200:
        return min(hard_cap, 2)
    return min(hard_cap, 1)


def should_continue_retry(config, state, attempt, quality, solver_info, elapsed_s):
    cfg = normalize_autotune_config(dict(config or {}))
    st = dict(state or init_retry_state(cfg))
    elapsed = max(0.0, float(elapsed_s or 0.0))
    st["time_spent_s"] = float(st.get("time_spent_s", 0.0)) + elapsed
    badness = compute_badness_score(quality, solver_info, cfg)
    prev = st.get("last_badness")
    best = st.get("best_badness")
    min_improve = float(cfg.get("AUTO_RETRY_MIN_IMPROVE", 0.15))
    weak_improve = float(cfg.get("AUTO_RETRY_WEAK_IMPROVE", 0.03))

    if badness <= 0.0:
        st["last_badness"] = badness
        st["best_badness"] = 0.0 if best is None else min(float(best), 0.0)
        st["last_decision_reason"] = "accepted_badness_zero"
        return False, st, st["last_decision_reason"]

    if prev is None:
        improvement_ratio = None
    else:
        denom = max(abs(float(prev)), 1e-12)
        improvement_ratio = (float(prev) - float(badness)) / denom

    if best is None:
        st["best_badness"] = badness
    else:
        st["best_badness"] = min(float(best), badness)

    if improvement_ratio is None:
        # First measured attempt: establish baseline only.
        st["no_improve_count"] = int(st.get("no_improve_count", 0))
    elif improvement_ratio >= min_improve:
        st["no_improve_count"] = 0
    elif improvement_ratio >= weak_improve:
        st["no_improve_count"] = max(0, int(st.get("no_improve_count", 0)) - 1)
    else:
        st["no_improve_count"] = int(st.get("no_improve_count", 0)) + 1

    st["last_badness"] = badness
    mode = cfg.get("AUTO_RETRY_MODE")
    patience = max(0, int(float(cfg.get("AUTO_RETRY_PATIENCE", 2))))
    hard_cap = max(0, int(float(cfg.get("AUTO_RETRY_HARD_CAP", 8))))

    if mode == "fixed":
        max_retry = max(0, int(float(cfg.get("AUTO_RETRY_MAX", 0) or 0)))
        if int(attempt) >= max_retry:
            st["last_decision_reason"] = "fixed_reach_max_retry"
            return False, st, st["last_decision_reason"]
        st["last_decision_reason"] = "fixed_allow_retry"
        return True, st, st["last_decision_reason"]

    if st.get("adaptive_limit") is None:
        st["adaptive_limit"] = estimate_adaptive_retry_limit(cfg, elapsed)
    if int(attempt) >= int(st.get("adaptive_limit", 0)):
        st["last_decision_reason"] = "adaptive_limit_reached"
        return False, st, st["last_decision_reason"]
    if int(attempt) >= hard_cap:
        st["last_decision_reason"] = "hard_cap_reached"
        return False, st, st["last_decision_reason"]
    if int(st.get("no_improve_count", 0)) >= patience:
        st["last_decision_reason"] = "patience_exhausted"
        return False, st, st["last_decision_reason"]

    time_budget = _float_or_none(cfg.get("AUTO_RETRY_TIME_BUDGET_S"))
    if time_budget is None:
        factor = float(cfg.get("AUTO_RETRY_BUDGET_FACTOR", 4.0))
        time_budget = elapsed * factor
        time_budget = max(float(cfg.get("AUTO_RETRY_MIN_BUDGET_S", 180.0)), time_budget)
        time_budget = min(float(cfg.get("AUTO_RETRY_MAX_BUDGET_S", 3600.0)), time_budget)
    if float(st.get("time_spent_s", 0.0)) >= float(time_budget):
        st["last_decision_reason"] = "time_budget_exhausted"
        return False, st, st["last_decision_reason"]

    st["last_decision_reason"] = "adaptive_allow_retry"
    return True, st, st["last_decision_reason"]


def next_retry_config(base_config, current_config, quality, attempt_index, retry_state=None):
    """Generate config for next retry; backward compatible signature."""
    quality = quality or {}
    cfg = normalize_autotune_config(clone_runtime_config(current_config))
    base = normalize_autotune_config(clone_runtime_config(base_config))
    flags = set(quality.get("flags") or [])

    sim_fs = _float_or_none(cfg.get("SIMULATION_TIME_FS"))
    if sim_fs is None:
        sim_fs = 1000.0
    shut = _float_or_none(cfg.get("AUTO_SHUTOFF_MIN"))
    if shut is None:
        shut = 1e-5
    mesh = int(float(cfg.get("MESH_ACCURACY", 2) or 2))
    dt = _float_or_none(cfg.get("DT_STABILITY_FACTOR"))
    if dt is None:
        dt = 0.99

    min_shut = float(base.get("AUTO_RETRY_MIN_AUTO_SHUTOFF", 1e-9))
    max_mesh = int(float(base.get("AUTO_RETRY_MAX_MESH_ACCURACY", 5)))
    min_dt = float(base.get("AUTO_RETRY_MIN_DT", 0.50))
    action = "none"
    no_improve = int((retry_state or {}).get("no_improve_count", 0))
    strong_no_improve = no_improve >= max(1, int(float(base.get("AUTO_RETRY_PATIENCE", 2)) - 1))

    tmax = _float_or_none(quality.get("tmax"))
    t_limit = float(base.get("QUALITY_T_LIMIT", 1.03))
    not_decayed = ("ended_by_simulation_time" in flags) or (
        "transmission_gt_limit" in flags and tmax is not None and tmax > t_limit
    )

    if "diverged" in flags or "nan_or_inf" in flags:
        if dt >= 0.98:
            dt = 0.95
        elif dt >= 0.95:
            dt = 0.90
        else:
            dt = max(dt - 0.10, min_dt)
        sim_fs = sim_fs * 1.25
        action = "lower_dt_for_diverged_or_nan"
    else:
        strong = (
            "transmission_gt_limit" in flags
            and quality.get("tmax") not in ("", None)
            and float(quality.get("tmax")) > 1.20
        )
        grow = float(base.get("AUTO_RETRY_TIME_GROWTH_STRONG", 2.5)) if strong else float(
            base.get("AUTO_RETRY_TIME_GROWTH", 1.8)
        )

        if not_decayed:
            sim_fs = sim_fs * grow
            shut = max(shut * float(base.get("AUTO_RETRY_SHUTOFF_FACTOR", 0.1)), min_shut)
            action = "increase_time_and_reduce_shutoff"
        elif "ripple_spectrum" in flags:
            sim_fs = sim_fs * float(base.get("AUTO_RETRY_TIME_GROWTH", 1.8))
            action = "increase_time_for_ripple"

        if (("ripple_spectrum" in flags and int(attempt_index) >= 2 and mesh < max_mesh) or strong_no_improve):
            mesh = min(max_mesh, mesh + 1)
            action = action + "+raise_mesh" if action != "none" else "raise_mesh_for_stability"

        if (("ripple_spectrum" in flags and int(attempt_index) >= 2) or strong_no_improve):
            dt = 0.95 if dt >= 0.98 else max(dt - 0.05, min_dt)
            action = action + "+lower_dt" if action != "none" else "lower_dt_for_stability"

        if action == "none":
            sim_fs = sim_fs * float(base.get("AUTO_RETRY_TIME_GROWTH", 1.8))
            action = "fallback_increase_time"

    cfg["SIMULATION_TIME_FS"] = float(sim_fs)
    cfg["SIMULATION_TIME_S"] = float(sim_fs) * 1e-15
    cfg["AUTO_SHUTOFF_MIN"] = float(shut)
    cfg["MESH_ACCURACY"] = int(mesh)
    cfg["DT_STABILITY_FACTOR"] = float(dt)
    cfg["AUTO_RETRY_LAST_ACTION"] = action
    return cfg


def runtime_profile_text(config):
    return "simulation_time_fs={}; auto_shutoff_min={}; mesh_accuracy={}; dt_stability_factor={}".format(
        config.get("SIMULATION_TIME_FS"),
        config.get("AUTO_SHUTOFF_MIN"),
        config.get("MESH_ACCURACY"),
        config.get("DT_STABILITY_FACTOR"),
    )


def append_retry_history(path, row):
    """Append-mode writer for retry_history.csv."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "time",
        "point_index",
        "point_name",
        "attempt",
        "accepted",
        "quality_status",
        "flags",
        "reasons",
        "tmax",
        "tmin",
        "ripple_score",
        "sign_changes",
        "solver_status",
        "solver_status_text",
        "autoshutoff_final",
        "simulation_time_fs",
        "auto_shutoff_min",
        "mesh_accuracy",
        "dt_stability_factor",
        "elapsed_s",
        "fsp",
        "xlsx",
        "png",
    ]
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        clean = {}
        for key in fields:
            value = row.get(key, "")
            if isinstance(value, (list, tuple)):
                value = ";".join([str(x) for x in value])
            clean[key] = value
        writer.writerow(clean)
