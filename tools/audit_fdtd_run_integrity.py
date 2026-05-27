#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


def _count_lines(csv_path: Path):
    if not csv_path.exists():
        return None
    with csv_path.open("r", encoding="utf-8-sig", errors="replace") as f:
        lines = sum(1 for _ in f)
    return max(0, lines - 1)


def _find_first_existing(base: Path, rels):
    for rel in rels:
        p = base / rel
        if p.exists():
            return p
    return None


def _list_samples(path: Path, suffix: str):
    if not path or not path.exists():
        return set()
    out = set()
    for p in path.glob(f"*{suffix}"):
        stem = p.stem
        out.add(stem.replace("_transmission_abs2", ""))
    return out


def audit_run(run_dir: Path):
    scan_csv = _find_first_existing(run_dir, ["00_scan_plan/scan_points.csv", "scan_points.csv"])
    expected_points = _count_lines(scan_csv) if scan_csv else None

    work_dir = _find_first_existing(run_dir, ["05_work_fsp", "01_work_fsp"])
    final_dir = _find_first_existing(run_dir, ["01_fsp", "01_work_fsp", "05_work_fsp"])
    excel_dir = _find_first_existing(run_dir, ["02_transmission_excel"])
    png_dir = _find_first_existing(run_dir, ["03_transmission_abs2_png", "03_transmission_png_abs2"])
    manifest_csv = _find_first_existing(run_dir, ["04_logs/manifest.csv", "05_logs/manifest.csv", "manifest.csv"])

    work_count = len(list(work_dir.glob("*.fsp"))) if work_dir and work_dir.exists() else 0
    final_count = len(list(final_dir.glob("*.fsp"))) if final_dir and final_dir.exists() else 0
    excel_count = len(list(excel_dir.glob("*.xlsx"))) if excel_dir and excel_dir.exists() else 0
    png_count = len(list(png_dir.glob("*.png"))) if png_dir and png_dir.exists() else 0
    manifest_rows = _count_lines(manifest_csv) if manifest_csv else None

    work_samples = _list_samples(work_dir, ".fsp")
    work_samples.discard("master_template")
    excel_samples = _list_samples(excel_dir, ".xlsx")
    png_samples = _list_samples(png_dir, ".png")

    first_missing_work = ""
    first_missing_excel = ""
    first_missing_png = ""
    if expected_points and scan_csv and scan_csv.exists():
        with scan_csv.open("r", encoding="utf-8-sig", errors="replace") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            sample = (row.get("name") or "").strip()
            if not sample:
                continue
            if not first_missing_work and sample not in work_samples:
                first_missing_work = sample
            if not first_missing_excel and sample not in excel_samples:
                first_missing_excel = sample
            if not first_missing_png and sample not in png_samples:
                first_missing_png = sample
            if first_missing_work and first_missing_excel and first_missing_png:
                break

    status = "OK"
    advice = "完整。"
    if "run_preview_" in run_dir.name:
        status = "PREVIEW_MODE_EXPECTED"
        advice = "preview 仅生成计划和母版，不生成逐点产物。"
        return {
            "run_dir": str(run_dir),
            "expected_points": expected_points,
            "work_fsp_count": work_count,
            "final_fsp_count": final_count,
            "excel_count": excel_count,
            "png_count": png_count,
            "manifest_rows": manifest_rows,
            "first_missing_work_fsp": first_missing_work,
            "first_missing_excel": first_missing_excel,
            "first_missing_png": first_missing_png,
            "status": status,
            "advice": advice,
        }
    if expected_points is None:
        status = "FAILED_EARLY"
        advice = "缺少 scan_points.csv，先检查子脚本是否启动成功。"
    elif "run_test_" in run_dir.name and expected_points <= 5:
        status = "TEST_MODE_EXPECTED"
        advice = "测试模式点数较少属预期。"
    elif work_count <= 1:
        status = "FAILED_EARLY"
        advice = "仅有母版 FSP；检查 controller timeout 或手工中断。"
    elif (excel_count < expected_points) or (png_count < expected_points):
        status = "PARTIAL"
        advice = "产物不完整；检查 manifest/error_stage 和子日志。"

    return {
        "run_dir": str(run_dir),
        "expected_points": expected_points,
        "work_fsp_count": work_count,
        "final_fsp_count": final_count,
        "excel_count": excel_count,
        "png_count": png_count,
        "manifest_rows": manifest_rows,
        "first_missing_work_fsp": first_missing_work,
        "first_missing_excel": first_missing_excel,
        "first_missing_png": first_missing_png,
        "status": status,
        "advice": advice,
    }


def iter_runs(root: Path):
    return sorted(
        [p for p in root.rglob("run_*") if p.is_dir() and ("run_full_" in p.name or "run_test_" in p.name or "run_preview_" in p.name)],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default="")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--all-recent", type=int, default=0)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]

    runs = []
    if args.run_dir:
        runs = [Path(args.run_dir)]
    elif args.latest:
        found = iter_runs(root)
        runs = found[:1]
    elif args.all_recent > 0:
        runs = iter_runs(root)[: args.all_recent]
    else:
        ap.error("use --run-dir / --latest / --all-recent")

    reports = [audit_run(r) for r in runs]
    print(json.dumps(reports[0] if len(reports) == 1 else reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
