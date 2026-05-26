# -*- coding: utf-8 -*-
from __future__ import print_function

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fdtd_autotune_common import (
    append_retry_history,
    clone_runtime_config,
    next_retry_config,
    normalize_autotune_config,
    runtime_profile_text,
)


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def status_from_quality(quality):
    if quality.get("accepted"):
        if "ended_by_simulation_time" in set(quality.get("flags") or []):
            return "accepted_with_warning"
        return "accepted"
    return "need_retry"


def main():
    root = Path.cwd().resolve()
    out_dir = root / "tests" / "mock_outputs" / ("run_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    logs_dir = out_dir / "04_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "AUTO_RETRY_ENABLED": True,
        "AUTO_RETRY_MAX": 2,
        "SIMULATION_TIME_FS": 70.0,
        "AUTO_SHUTOFF_MIN": 1e-5,
        "MESH_ACCURACY": 2,
        "DT_STABILITY_FACTOR": 0.99,
    }
    normalize_autotune_config(config)
    base_runtime = clone_runtime_config(config)

    # A: accepted immediately
    # B: fail once with transmission_gt_limit, then accepted
    # C: fail repeatedly and finally failed_quarantined
    scenarios = [
        {
            "index": 1,
            "name": "sample_A",
            "attempt_qualities": [
                {"accepted": True, "flags": [], "reasons": [], "tmax": 0.92, "ripple_score": 0.01},
            ],
        },
        {
            "index": 2,
            "name": "sample_B",
            "attempt_qualities": [
                {"accepted": False, "flags": ["transmission_gt_limit"], "reasons": ["T over limit"], "tmax": 1.12, "ripple_score": 0.03},
                {"accepted": True, "flags": [], "reasons": [], "tmax": 0.97, "ripple_score": 0.02},
            ],
        },
        {
            "index": 3,
            "name": "sample_C",
            "attempt_qualities": [
                {"accepted": False, "flags": ["transmission_gt_limit", "ripple_spectrum"], "reasons": ["T over limit", "ripple"], "tmax": 1.25, "ripple_score": 0.20},
                {"accepted": False, "flags": ["transmission_gt_limit"], "reasons": ["T over limit"], "tmax": 1.18, "ripple_score": 0.08},
                {"accepted": False, "flags": ["transmission_gt_limit"], "reasons": ["T over limit"], "tmax": 1.10, "ripple_score": 0.05},
            ],
        },
    ]

    manifest_rows = []
    quality_rows = []
    retry_history_path = logs_dir / "retry_history.csv"

    for sample in scenarios:
        runtime = clone_runtime_config(base_runtime)
        final_quality = None
        final_attempt = 0
        accepted = False

        for attempt in range(0, int(config["AUTO_RETRY_MAX"]) + 1):
            final_attempt = attempt
            if attempt > 0:
                runtime = next_retry_config(base_runtime, runtime, final_quality or {"flags": []}, attempt)

            qlist = sample["attempt_qualities"]
            quality = qlist[attempt] if attempt < len(qlist) else qlist[-1]
            final_quality = dict(quality)
            quality_status = status_from_quality(final_quality)

            append_retry_history(retry_history_path, {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "point_index": sample["index"],
                "point_name": sample["name"],
                "attempt": attempt,
                "accepted": final_quality.get("accepted"),
                "quality_status": quality_status,
                "flags": final_quality.get("flags", []),
                "reasons": final_quality.get("reasons", []),
                "tmax": final_quality.get("tmax", ""),
                "tmin": "",
                "ripple_score": final_quality.get("ripple_score", ""),
                "sign_changes": "",
                "solver_status": 2,
                "solver_status_text": "auto_shutoff",
                "autoshutoff_final": "1e-6",
                "simulation_time_fs": runtime.get("SIMULATION_TIME_FS"),
                "auto_shutoff_min": runtime.get("AUTO_SHUTOFF_MIN"),
                "mesh_accuracy": runtime.get("MESH_ACCURACY"),
                "dt_stability_factor": runtime.get("DT_STABILITY_FACTOR"),
                "elapsed_s": "0.010",
                "fsp": str(out_dir / "01_fsp" / (sample["name"] + ".fsp")),
                "xlsx": str(out_dir / "02_transmission_excel" / (sample["name"] + ".xlsx")),
                "png": str(out_dir / "03_transmission_abs2_png" / (sample["name"] + ".png")),
            })

            quality_rows.append({
                "sample": sample["name"],
                "attempt": attempt,
                "accepted": bool(final_quality.get("accepted")),
                "flags": ";".join(final_quality.get("flags") or []),
                "runtime_profile": runtime_profile_text(runtime),
            })

            if final_quality.get("accepted"):
                accepted = True
                break

        status = status_from_quality(final_quality or {})
        if not accepted:
            status = "failed_quarantined"

        manifest_rows.append({
            "index": sample["index"],
            "name": sample["name"],
            "status": status,
            "retry_count": max(0, final_attempt),
            "quality_flags": ";".join((final_quality or {}).get("flags") or []),
            "quality_reasons": ";".join((final_quality or {}).get("reasons") or []),
            "solver_status": 2,
            "solver_status_text": "auto_shutoff",
            "autoshutoff_final": "1e-6",
            "simulation_time_fs": runtime.get("SIMULATION_TIME_FS"),
            "auto_shutoff_min": runtime.get("AUTO_SHUTOFF_MIN"),
            "mesh_accuracy": runtime.get("MESH_ACCURACY"),
            "dt_stability_factor": runtime.get("DT_STABILITY_FACTOR"),
            "fsp": str(out_dir / "01_fsp" / (sample["name"] + ".fsp")),
            "xlsx": str(out_dir / "02_transmission_excel" / (sample["name"] + ".xlsx")),
            "png": str(out_dir / "03_transmission_abs2_png" / (sample["name"] + ".png")),
            "elapsed_s": "0.010",
            "max_abs2": "",
            "max_wavelength_nm": "",
            "min_abs2": "",
            "min_wavelength_nm": "",
        })

    manifest_path = logs_dir / "manifest.csv"
    quality_path = logs_dir / "quality_report.csv"
    write_csv(
        manifest_path,
        [
            "index", "name", "status", "retry_count", "quality_flags", "quality_reasons",
            "solver_status", "solver_status_text", "autoshutoff_final",
            "simulation_time_fs", "auto_shutoff_min", "mesh_accuracy", "dt_stability_factor",
            "fsp", "xlsx", "png", "elapsed_s",
            "max_abs2", "max_wavelength_nm", "min_abs2", "min_wavelength_nm",
        ],
        manifest_rows,
    )
    write_csv(quality_path, ["sample", "attempt", "accepted", "flags", "runtime_profile"], quality_rows)

    summary = {
        "output_dir": str(out_dir),
        "manifest_csv": str(manifest_path),
        "retry_history_csv": str(retry_history_path),
        "quality_report_csv": str(quality_path),
        "samples": [x["name"] for x in scenarios],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
