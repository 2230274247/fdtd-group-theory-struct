# -*- coding: utf-8 -*-
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_path = Path(manifest.get("run_path") or "")
    sample_id = str(manifest.get("sample_id") or "")
    backup_dir = manifest.get("backup_dir") or ""

    print("[rerun] manifest=%s" % manifest_path, flush=True)
    print("[rerun] run_path=%s" % run_path, flush=True)
    print("[rerun] sample_id=%s" % sample_id, flush=True)
    print("[rerun] backup_dir=%s" % backup_dir, flush=True)

    fsp_candidates = []
    work_dir = run_path / "05_work_fsp"
    if work_dir.exists():
        fsp_candidates.extend(sorted(work_dir.glob("*%s*.fsp" % sample_id)))
    if not fsp_candidates and run_path.exists():
        fsp_candidates.extend(sorted(run_path.rglob("*%s*.fsp" % sample_id)))
    if fsp_candidates:
        print("[rerun] found_fsp=%s" % fsp_candidates[0], flush=True)
    else:
        print("[rerun] found_fsp=<none>", flush=True)

    print("[rerun] skeleton created; need to implement common.run_single_sample_from_manifest", flush=True)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
