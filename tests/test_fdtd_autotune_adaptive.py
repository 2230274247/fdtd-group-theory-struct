# -*- coding: utf-8 -*-
from fdtd_autotune_common import (
    normalize_autotune_config,
    compute_badness_score,
    init_retry_state,
    estimate_adaptive_retry_limit,
    should_continue_retry,
    next_retry_config,
)


def _base_runtime():
    return {
        "SIMULATION_TIME_FS": 70.0,
        "AUTO_SHUTOFF_MIN": 1e-5,
        "MESH_ACCURACY": 2,
        "DT_STABILITY_FACTOR": 0.99,
    }


def test_normalize_retry_max_empty_to_adaptive():
    cfg = normalize_autotune_config({"AUTO_RETRY_MAX": ""})
    assert cfg["AUTO_RETRY_MODE"] == "adaptive"
    assert cfg["AUTO_RETRY_MAX"] is None


def test_normalize_retry_max_adaptive_text_to_adaptive():
    cfg = normalize_autotune_config({"AUTO_RETRY_MAX": "adaptive"})
    assert cfg["AUTO_RETRY_MODE"] == "adaptive"
    assert cfg["AUTO_RETRY_MAX"] is None


def test_normalize_retry_max_zero_to_fixed_zero():
    cfg = normalize_autotune_config({"AUTO_RETRY_MAX": 0})
    assert cfg["AUTO_RETRY_MODE"] == "fixed"
    assert cfg["AUTO_RETRY_MAX"] == 0


def test_normalize_retry_max_two_to_fixed_two():
    cfg = normalize_autotune_config({"AUTO_RETRY_MAX": 2})
    assert cfg["AUTO_RETRY_MODE"] == "fixed"
    assert cfg["AUTO_RETRY_MAX"] == 2


def test_badness_improves_when_tmax_drops():
    cfg = normalize_autotune_config({"QUALITY_T_LIMIT": 1.03})
    q1 = {"accepted": False, "flags": ["transmission_gt_limit"], "tmax": 1.6, "ripple_score": 0.0}
    q2 = {"accepted": False, "flags": ["transmission_gt_limit"], "tmax": 1.12, "ripple_score": 0.0}
    b1 = compute_badness_score(q1, {"solver_status": 2}, cfg)
    b2 = compute_badness_score(q2, {"solver_status": 2}, cfg)
    assert b2 < b1


def test_patience_stop_after_no_improvement():
    cfg = normalize_autotune_config({
        "AUTO_RETRY_MAX": "adaptive",
        "AUTO_RETRY_PATIENCE": 2,
        "AUTO_RETRY_TIME_BUDGET_S": 99999,
        "AUTO_RETRY_HARD_CAP": 10,
    })
    st = init_retry_state(cfg)
    q = {"accepted": False, "flags": ["transmission_gt_limit"], "tmax": 1.5, "ripple_score": 0.0}

    c1, st, _ = should_continue_retry(cfg, st, 0, q, {"solver_status": 2}, 60)
    c2, st, _ = should_continue_retry(cfg, st, 1, q, {"solver_status": 2}, 60)
    c3, st, reason = should_continue_retry(cfg, st, 2, q, {"solver_status": 2}, 60)

    assert c1 is True
    assert c2 is True
    assert c3 is False
    assert reason == "patience_exhausted"


def test_adaptive_limit_short_run_allows_more():
    cfg = normalize_autotune_config({"AUTO_RETRY_HARD_CAP": 8})
    limit = estimate_adaptive_retry_limit(cfg, 30)
    assert limit >= 5


def test_adaptive_limit_long_run_allows_fewer():
    cfg = normalize_autotune_config({"AUTO_RETRY_HARD_CAP": 8})
    limit = estimate_adaptive_retry_limit(cfg, 1300)
    assert limit <= 1


def test_next_retry_diverged_prioritizes_dt_drop():
    base = _base_runtime()
    q = {"flags": ["diverged"], "tmax": ""}
    out = next_retry_config(base, base, q, 1)
    assert out["DT_STABILITY_FACTOR"] <= 0.95
    assert "lower_dt" in str(out.get("AUTO_RETRY_LAST_ACTION", ""))


def test_next_retry_t_gt_limit_first_retry_prioritizes_time_and_shutoff():
    base = _base_runtime()
    q = {"flags": ["transmission_gt_limit"], "tmax": 1.10}
    out = next_retry_config(base, base, q, 1)
    assert out["SIMULATION_TIME_FS"] > base["SIMULATION_TIME_FS"]
    assert out["AUTO_SHUTOFF_MIN"] < base["AUTO_SHUTOFF_MIN"]
    assert "increase_time_and_reduce_shutoff" in str(out.get("AUTO_RETRY_LAST_ACTION", ""))
