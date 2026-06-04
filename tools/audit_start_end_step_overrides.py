# -*- coding: utf-8 -*-
"""
Audit whether run_*.py scripts can receive generic start/end/step overrides.
This script does NOT start FDTD.
"""
from __future__ import print_function

import ast
import csv
import fnmatch
import locale
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

EXPECTED_ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIR_NAMES = set([
    "results",
    "controller_logs",
    "runtime_state",
    "_stage9_script_recovery_backup",
    "backup",
    "backups",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
])
EXCLUDE_DIR_PATTERNS = ["_stage9_*"]
REQUIRED_MARKERS = ["fdtd_master_controller.py", "近径向高对称结构"]
OPTIONAL_SYMMETRY_MARKERS = ["C2对称结构", "C3对称结构", "C4对称结构", "C6对称结构"]

UNITS = ("NM", "UM", "M", "DEG", "RAD", "")
START_WORDS = ("START", "BEGIN", "MIN")
END_WORDS = ("END", "STOP", "MAX")
STEP_WORDS = ("STEP", "DELTA", "INTERVAL")


def is_excluded_path(path):
    for part in path.parts:
        if part in EXCLUDE_DIR_NAMES:
            return True
        for pattern in EXCLUDE_DIR_PATTERNS:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def is_valid_project_root(root):
    if not root.exists() or not root.is_dir():
        return False
    for marker in REQUIRED_MARKERS:
        if not (root / marker).exists():
            return False
    if not any((root / marker).exists() for marker in OPTIONAL_SYMMETRY_MARKERS):
        return False
    return True


def candidate_roots_from_context():
    candidates = []
    here = Path(__file__).resolve()
    candidates.append(here.parent)
    candidates.append(here.parent.parent)
    cwd = Path.cwd()
    candidates.append(cwd)
    candidates.append(cwd / "群论_struct")
    candidates.append(cwd / "struct" / "群论_struct")
    candidates.append(Path(r"H:\FDTD outcome\struct\群论_struct"))
    candidates.append(EXPECTED_ROOT)
    unique = []
    seen = set()
    for item in candidates:
        try:
            resolved = item.resolve()
        except Exception:
            resolved = item
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def resolve_project_root():
    raw_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if raw_arg:
        arg_root = Path(raw_arg)
        if is_valid_project_root(arg_root):
            return arg_root.resolve()
        print("[WARN] supplied root is invalid or garbled:")
        print("       raw argv[1] repr =", repr(raw_arg))
        print("       parsed root      =", str(arg_root))
        print("       exists           =", arg_root.exists())
        print("       is_dir           =", arg_root.is_dir())
        print("[WARN] fallback to safe project-root discovery.")

    valid = []
    for candidate in candidate_roots_from_context():
        if is_valid_project_root(candidate):
            valid.append(candidate.resolve())
    unique = []
    seen = set()
    for root in valid:
        key = str(root).lower()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    if len(unique) == 1:
        return unique[0]
    if len(unique) > 1:
        print("[ERROR] multiple valid project roots found:")
        for item in unique:
            print("  -", item)
        raise SystemExit(2)
    print("[ERROR] no valid project root found.")
    print("cwd =", os.getcwd())
    print("__file__ =", __file__)
    raise SystemExit(2)


def iter_run_scripts(root):
    for coding_dir in root.rglob("coding"):
        if not coding_dir.is_dir():
            continue
        if is_excluded_path(coding_dir):
            continue
        for script in coding_dir.rglob("run_*.py"):
            if not script.is_file():
                continue
            if is_excluded_path(script):
                continue
            yield script


def print_root_diagnostics(root):
    print("[ROOT DIAGNOSTICS]")
    print("sys.getfilesystemencoding() =", sys.getfilesystemencoding())
    print("locale.getpreferredencoding(False) =", locale.getpreferredencoding(False))
    print("os.getcwd() =", os.getcwd())
    print("repr(os.getcwd()) =", repr(os.getcwd()))
    if len(sys.argv) > 1:
        print("sys.argv[1] repr =", repr(sys.argv[1]))
    else:
        print("sys.argv[1] repr = <not supplied>")
    print("final ROOT =", root)
    print("repr(str(ROOT)) =", repr(str(root)))
    print("ROOT.exists() =", root.exists())
    print("ROOT.is_dir() =", root.is_dir())


def canon(key):
    text = str(key).strip()
    text = re.sub(r"[^0-9A-Za-z]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text.upper()


def lit(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def collect(path):
    try:
        text = path.read_text(encoding="utf-8-sig")
    except Exception:
        text = path.read_text(encoding="utf-8", errors="ignore")

    settings = OrderedDict()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return settings, "SYNTAX_ERROR", text

    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue

        name = target.id
        value = lit(node.value)
        if isinstance(value, (int, float, str, bool)) or value is None:
            settings[name] = {
                "key": name,
                "canon": canon(name),
                "value": value,
                "source": "assignment",
            }

        if name == "CONFIG":
            cfg = lit(node.value)
            if isinstance(cfg, dict):
                for k, v in cfg.items():
                    if isinstance(v, (int, float, str, bool)) or v is None:
                        raw = str(k)
                        settings[raw] = {
                            "key": raw,
                            "canon": canon(raw),
                            "value": v,
                            "source": "config",
                        }
            elif isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "dict":
                for kw in node.value.keywords:
                    if kw.arg is None:
                        continue
                    kw_val = lit(kw.value)
                    if isinstance(kw_val, (int, float, str, bool)) or kw_val is None:
                        raw = str(kw.arg)
                        settings[raw] = {
                            "key": raw,
                            "canon": canon(raw),
                            "value": kw_val,
                            "source": "config",
                        }
    return settings, "OK", text


def _has_dynamic_end_signal(settings, text):
    canon_keys = [item["canon"] for item in settings.values()]
    for key in canon_keys:
        if key == "MAX_CENTER_OFFSET_M":
            return True
        if key == "MAX_OFFSET_M":
            return True
        if key.startswith("MAX_") and key.endswith("_OFFSET_M"):
            return True
    if re.search(r"(compute|get|calculate)_[A-Za-z0-9_]*end", text, re.I):
        return True
    if re.search(r"safe_[A-Za-z0-9_]*offset", text, re.I):
        return True
    if re.search(r"geometry[_ ]*limit", text, re.I):
        return True
    if re.search(r"dynamic[_ ]*end", text, re.I):
        return True
    return False


def detect(settings, text):
    entries = OrderedDict((item["canon"], item) for item in settings.values())
    groups = []
    seen = set()

    for canon_key, item in entries.items():
        parts = canon_key.split("_")
        start_word = None
        for word in START_WORDS:
            if word in parts:
                start_word = word
                break
        if not start_word:
            continue

        idx = parts.index(start_word)
        prefix = "_".join(parts[:idx])
        unit = parts[-1] if parts and parts[-1] in UNITS else ""

        end = None
        step = None
        for ew in END_WORDS:
            cand = "_".join([x for x in (prefix, ew, unit) if x])
            if cand in entries:
                end = cand
                break
        for sw in STEP_WORDS:
            cand = "_".join([x for x in (prefix, sw, unit) if x])
            if cand in entries:
                step = cand
                break

        if step and end:
            key = (item["key"], entries[end]["key"], entries[step]["key"])
            if key in seen:
                continue
            seen.add(key)
            group_type = "STATIC_SCAN_GROUP"
            if entries[end]["value"] is None and _has_dynamic_end_signal(settings, text):
                group_type = "DYNAMIC_END_SCAN_GROUP"
            groups.append({
                "unit": unit or "RAW",
                "start_key": item["key"],
                "end_key": entries[end]["key"],
                "step_key": entries[step]["key"],
                "start": item["value"],
                "end": entries[end]["value"],
                "step": entries[step]["value"],
                "start_source": item.get("source", ""),
                "end_source": entries[end].get("source", ""),
                "step_source": entries[step].get("source", ""),
                "group_type": group_type,
            })
        elif step and not end:
            if _has_dynamic_end_signal(settings, text):
                key = (item["key"], "__DYNAMIC_END__", entries[step]["key"])
                if key in seen:
                    continue
                seen.add(key)
                groups.append({
                    "unit": unit or "RAW",
                    "start_key": item["key"],
                    "end_key": item["key"].replace("START", "END", 1),
                    "step_key": entries[step]["key"],
                    "start": item["value"],
                    "end": None,
                    "step": entries[step]["value"],
                    "start_source": item.get("source", ""),
                    "end_source": "dynamic",
                    "step_source": entries[step].get("source", ""),
                    "group_type": "DYNAMIC_END_SCAN_GROUP",
                })
    return groups


def classify(parse_status, groups):
    if parse_status != "OK":
        return "FAIL_NO_SCAN_GROUP"
    if not groups:
        return "FAIL_NO_SCAN_GROUP"
    if len(groups) == 1:
        return "PASS_ONE_GROUP"
    return "WARN_MULTIPLE_GROUPS"


def main():
    root = resolve_project_root()
    print_root_diagnostics(root)
    if root.resolve() != EXPECTED_ROOT:
        print("[ERROR] final ROOT is not expected project root.")
        print("expected =", EXPECTED_ROOT)
        print("actual   =", root.resolve())
        raise SystemExit(2)

    scripts = sorted(iter_run_scripts(root))
    print("[AUDIT] included run_*.py count =", len(scripts))
    out = root / "controller_logs" / "start_end_step_override_audit.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for idx, path in enumerate(scripts, 1):
        settings, parse_status, text = collect(path)
        groups = detect(settings, text) if parse_status == "OK" else []
        status = classify(parse_status, groups)
        rows.append({
            "index": idx,
            "status": status,
            "parse_status": parse_status,
            "relative_path": str(path.relative_to(root)),
            "group_count": len(groups),
            "groups": repr(groups),
        })

    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["index", "status", "parse_status", "relative_path", "group_count", "groups"],
        )
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    pass_one = sum(1 for r in rows if r["status"] == "PASS_ONE_GROUP")
    warn_multi = sum(1 for r in rows if r["status"] == "WARN_MULTIPLE_GROUPS")
    fail_none = sum(1 for r in rows if r["status"] == "FAIL_NO_SCAN_GROUP")

    print("scripts:", total)
    print("audit_csv:", out)
    print("PASS_ONE_GROUP", pass_one)
    print("WARN_MULTIPLE_GROUPS", warn_multi)
    print("FAIL_NO_SCAN_GROUP", fail_none)


if __name__ == "__main__":
    main()
