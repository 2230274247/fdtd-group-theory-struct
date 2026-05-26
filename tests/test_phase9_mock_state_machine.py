# -*- coding: utf-8 -*-
from pathlib import Path

from fdtd_autotune_common import (
    append_retry_history,
    compute_badness_score,
    init_retry_state,
    normalize_autotune_config,
    should_continue_retry,
)


def _write_artifacts(base: Path, sample: str):
    fsp = base / "01_fsp" / f"{sample}.fsp"
    xlsx = base / "02_transmission_excel" / f"{sample}.xlsx"
    png = base / "03_transmission_abs2_png" / f"{sample}.png"
    diag = base / "04_logs" / "diagnostic_json" / f"{sample}.json"
    for p, data in [
        (fsp, "dummy fsp"),
        (xlsx, "dummy xlsx"),
        (png, "dummy png"),
        (diag, '{"ok": true}'),
    ]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data, encoding="utf-8")
    return fsp, xlsx, png, diag


def _run_sample(sample_name, attempts, cfg, root, sample_index):
    state = init_retry_state(cfg)
    retry_path = root / "04_logs" / "retry_history.csv"
    manifest_row = {}
    attempt = 0
    while True:
        q = attempts[min(attempt, len(attempts) - 1)]
        solver = q.get("solver_info", {"status": 2, "status_text": "auto_shutoff"})
        elapsed = float(q.get("elapsed_s", 1.0))
        score = float(compute_badness_score(q, solver, cfg))
        fsp, xlsx, png, diag = _write_artifacts(root, sample_name)
        append_retry_history(
            retry_path,
            {
                "point_index": sample_index,
                "point_name": sample_name,
                "attempt": attempt,
                "accepted": bool(q.get("accepted")),
                "quality_status": "accepted" if q.get("accepted") else "need_retry",
                "flags": q.get("flags", []),
                "reasons": q.get("reasons", []),
                "badness_score": score,
                "improvement_ratio": state.get("last_improvement_ratio", ""),
                "decision_reason": "",
                "action": q.get("action", ""),
                "solver_status": solver.get("status", ""),
                "solver_status_text": solver.get("status_text", ""),
                "elapsed_s": elapsed,
                "fsp": str(fsp),
                "xlsx": str(xlsx),
                "png": str(png),
            },
        )
        if q.get("accepted"):
            manifest_row = {
                "name": sample_name,
                "status": "accepted",
                "retry_count": attempt,
                "badness_score": score,
                "decision_reason": "accepted",
                "fsp": str(fsp),
                "xlsx": str(xlsx),
                "png": str(png),
                "diagnostic_json": str(diag),
            }
            break
        keep, state, reason = should_continue_retry(
            cfg, state, attempt, q, solver, elapsed
        )
        if not keep:
            manifest_row = {
                "name": sample_name,
                "status": "failed_quarantined",
                "retry_count": attempt,
                "badness_score": score,
                "decision_reason": reason,
                "fsp": str(fsp),
                "xlsx": str(xlsx),
                "png": str(png),
                "diagnostic_json": str(diag),
            }
            break
        attempt += 1
    return manifest_row


def test_phase9_mock_state_machine_full(tmp_path):
    root = tmp_path / "mock_run"
    cfg_fixed = normalize_autotune_config(
        {"AUTO_RETRY_MAX": 1, "AUTO_RETRY_MODE": "fixed", "AUTO_RETRY_ENABLED": True}
    )
    cfg_adaptive = normalize_autotune_config(
        {
            "AUTO_RETRY_MAX": "adaptive",
            "AUTO_RETRY_MODE": "adaptive",
            "AUTO_RETRY_ENABLED": True,
            "AUTO_RETRY_HARD_CAP": 8,
            "AUTO_RETRY_PATIENCE": 2,
            "AUTO_RETRY_MIN_IMPROVE": 0.03,
            "AUTO_RETRY_TIME_BUDGET_S": 900,
        }
    )

    # A: first attempt accepted
    row_a = _run_sample(
        "A",
        [{"accepted": True, "flags": [], "reasons": [], "tmax": 0.98, "ripple_score": 0.01, "elapsed_s": 20}],
        cfg_fixed,
        root,
        1,
    )
    # B: fail then accepted on retry
    row_b = _run_sample(
        "B",
        [
            {"accepted": False, "flags": ["transmission_gt_limit"], "reasons": ["T over"], "tmax": 1.2, "ripple_score": 0.03, "elapsed_s": 20},
            {"accepted": True, "flags": [], "reasons": [], "tmax": 0.95, "ripple_score": 0.01, "elapsed_s": 22},
        ],
        cfg_fixed,
        root,
        2,
    )
    # C: fixed max=1 then quarantine
    row_c = _run_sample(
        "C",
        [
            {"accepted": False, "flags": ["transmission_gt_limit"], "reasons": ["T over"], "tmax": 1.3, "ripple_score": 0.2, "elapsed_s": 30},
            {"accepted": False, "flags": ["transmission_gt_limit"], "reasons": ["T over"], "tmax": 1.25, "ripple_score": 0.15, "elapsed_s": 32},
        ],
        cfg_fixed,
        root,
        3,
    )
    # D: adaptive, short run and improvement -> continue then accept
    row_d = _run_sample(
        "D",
        [
            {"accepted": False, "flags": ["transmission_gt_limit"], "reasons": ["T over"], "tmax": 1.6, "ripple_score": 0.1, "elapsed_s": 30},
            {"accepted": True, "flags": [], "reasons": [], "tmax": 1.02, "ripple_score": 0.02, "elapsed_s": 28},
        ],
        cfg_adaptive,
        root,
        4,
    )
    # E: adaptive, long run and no improvement -> early stop
    row_e = _run_sample(
        "E",
        [
            {"accepted": False, "flags": ["transmission_gt_limit"], "reasons": ["T over"], "tmax": 1.3, "ripple_score": 0.1, "elapsed_s": 1300},
            {"accepted": False, "flags": ["transmission_gt_limit"], "reasons": ["T over"], "tmax": 1.29, "ripple_score": 0.1, "elapsed_s": 1300},
        ],
        cfg_adaptive,
        root,
        5,
    )

    assert row_a["status"] == "accepted" and row_a["retry_count"] == 0
    assert row_b["status"] == "accepted" and row_b["retry_count"] == 1
    assert row_c["status"] == "failed_quarantined" and row_c["retry_count"] == 1
    assert row_d["status"] == "accepted" and row_d["retry_count"] == 1
    assert row_e["status"] == "failed_quarantined"

    for row in [row_c, row_e]:
        assert Path(row["fsp"]).exists()
        assert Path(row["xlsx"]).exists()
        assert Path(row["png"]).exists()
        assert Path(row["diagnostic_json"]).exists()

    retry_path = root / "04_logs" / "retry_history.csv"
    assert retry_path.exists()
    text = retry_path.read_text(encoding="utf-8-sig")
    assert "point_name" in text and "attempt" in text and "quality_status" in text
    assert ",C,0," in text and ",C,1," in text
    assert ",D,0," in text and ",D,1," in text
    assert ",E,0," in text
