# -*- coding: utf-8 -*-
"""
FDTD 扰动脚本总控入口
====================

放置位置：H:\\FDTD outcome\\struct\\群论_struct\\fdtd_master_controller.py

核心能力：
1. 自动扫描本目录下所有母结构的 coding 文件夹，发现新增 run_*.py 脚本。
2. 按“对称类别 / 母结构 / 扰动名”分类展示，并显示最近 test/full 结果。
3. 运行前用中文解释每个脚本顶部“用户主要修改区”的含义。
4. 可在总控里临时覆盖小脚本的 start / end / step，不修改原脚本。
5. 依次或并行运行小脚本，并实时转发子脚本输出。
6. Ctrl+C 时同时结束总控、子脚本和子脚本启动的 FDTD 进程树。
"""
from __future__ import print_function

import argparse
import ast
import csv
import json
import datetime
import locale
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import OrderedDict
from pathlib import Path


# ========================= 用户主要修改区 =========================
STRUCT_ROOT = Path(__file__).resolve().parent
SCRIPT_PREFIXES = ("run_",)
EXCLUDE_NAME_PARTS = ("common", "__pycache__", ".bak", ".tmp")
DEFAULT_CHILD_MODE = "ask"       # ask / preview / test / full
DEFAULT_RUN_STYLE = "ask"        # ask / sequential / parallel
DEFAULT_MAX_PARALLEL = 2
CONTROLLER_LOG_ROOT = STRUCT_ROOT / "controller_logs"
PYTHON_EXE = sys.executable
ENABLE_COLOR_OUTPUT = True
CHILD_OUTPUT_ENCODING = getattr(sys.stdout, "encoding", None) or locale.getpreferredencoding(False) or "utf-8"
FDTD_RUNTIME_KEYS = (
    "SIMULATION_TIME_FS",
    "AUTO_SHUTOFF_MIN",
    "MESH_ACCURACY",
    "DT_STABILITY_FACTOR",
    "AUTO_RETRY_ENABLED",
    "AUTO_RETRY_MODE",
    "AUTO_RETRY_MAX",
    "AUTO_RETRY_HARD_CAP",
    "AUTO_RETRY_PATIENCE",
    "AUTO_RETRY_MIN_IMPROVE",
    "AUTO_RETRY_WEAK_IMPROVE",
    "AUTO_RETRY_TIME_BUDGET_S",
    "AUTO_RETRY_MAX_SINGLE_RUN_S",
    "QUALITY_T_LIMIT",
    "QUALITY_RIPPLE_LIMIT",
    "QUALITY_MIN_POINTS",
)
LEGACY_FDTD_RUNTIME_KEYS = ("SIMULATION_TIME_S",)

# 总控认为“明显危险”的临时输入；超过后会二次确认。
SOFT_LENGTH_LIMIT_UM = 0.90
SOFT_ANGLE_LIMIT_DEG = 360.0

# 定期清理 controller_logs 下的旧总控运行目录。只清理由本总控创建的
# controller_run_* 文件夹，不会清理任何结构 results 目录。
AUTO_CLEAN_OLD_CONTROLLER_RUNS = True
KEEP_CONTROLLER_RUN_DAYS = 14
# ================================================================


class SkipCurrentTask(Exception):
    def __init__(self, record):
        Exception.__init__(self, "skip current task")
        self.record = record


class StopController(Exception):
    def __init__(self, record=None):
        Exception.__init__(self, "stop controller")
        self.record = record


class ChildScriptError(Exception):
    def __init__(self, record):
        Exception.__init__(self, "child script failed")
        self.record = record


INTERRUPTED_TASKS = []
INTERRUPTED_LOCK = threading.Lock()
FAILED_TASKS = []
FAILED_LOCK = threading.Lock()
STDIN_COMMANDS = queue.Queue()
STDIN_LISTENER_STARTED = False
STDIN_LISTENER_LOCK = threading.Lock()


def now_stamp():
    n = datetime.datetime.now()
    return "{}年{}月{}日_{:02d}时{:02d}分{:02d}秒".format(n.year, n.month, n.day, n.hour, n.minute, n.second)


def safe_token(text):
    out = []
    for ch in str(text):
        out.append(ch if (ch.isalnum() or ch in "_-.") else "_")
    return "".join(out).strip("_") or "item"


def safe_console_print(text, end=""):
    """Print child-process output without crashing on legacy console encodings."""
    try:
        print(text, end=end)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_text, end=end)


def ensure_numpy_available(python_exe):
    """Ensure numpy exists in the same interpreter used to launch child scripts."""
    probe_cmd = [str(python_exe), "-c", "import numpy; print(numpy.__version__)"]
    try:
        out = subprocess.check_output(probe_cmd, stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf-8", errors="replace")
        ver = (out or "").strip().splitlines()[-1] if out else "unknown"
        print("依赖检查：numpy 已可用（{}）".format(ver))
        return
    except Exception as exc:
        print("依赖检查：当前解释器缺少 numpy，准备自动安装。")
        print("  解释器：{}".format(python_exe))
        print("  探测错误：{}".format(exc))
    install_cmd = [str(python_exe), "-m", "pip", "install", "numpy"]
    print("执行安装命令：{}".format(" ".join(install_cmd)))
    rc = subprocess.call(install_cmd)
    if rc != 0:
        raise RuntimeError("numpy 安装失败（exit={}），请手动在该解释器安装后重试。".format(rc))
    out = subprocess.check_output(probe_cmd, stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf-8", errors="replace")
    ver = (out or "").strip().splitlines()[-1] if out else "unknown"
    print("依赖检查：numpy 安装完成（{}）".format(ver))


def is_candidate_script(path):
    if path.suffix.lower() != ".py":
        return False
    if not any(path.name.startswith(p) for p in SCRIPT_PREFIXES):
        return False
    low = path.name.lower()
    return not any(part.lower() in low for part in EXCLUDE_NAME_PARTS)


def classify_script(root, script_path):
    rel_parts = script_path.relative_to(root).parts
    if "coding" not in [p.lower() for p in rel_parts]:
        return None
    coding_idx = [p.lower() for p in rel_parts].index("coding")
    if coding_idx < 1:
        return None
    symmetry = rel_parts[0]
    mother = rel_parts[coding_idx - 1]
    perturbation = rel_parts[coding_idx + 1] if len(rel_parts) > coding_idx + 2 else script_path.stem
    structure_root = root / Path(*rel_parts[:coding_idx])
    return {
        "symmetry": symmetry,
        "mother": mother,
        "perturbation": perturbation,
        "script": script_path,
        "relative": str(script_path.relative_to(root)),
        "structure_root": structure_root,
    }


def discover_scripts(root):
    records = []
    for coding_dir in root.rglob("coding"):
        for path in coding_dir.rglob("*.py"):
            if is_candidate_script(path):
                item = classify_script(root, path)
                if item:
                    records.append(item)
    records.sort(key=lambda x: (x["symmetry"], x["mother"], x["perturbation"], x["script"].name))
    for i, item in enumerate(records, 1):
        item["id"] = i
    return records


def cleanup_old_controller_runs():
    if not AUTO_CLEAN_OLD_CONTROLLER_RUNS or not CONTROLLER_LOG_ROOT.exists():
        return
    cutoff = time.time() - float(KEEP_CONTROLLER_RUN_DAYS) * 24 * 3600
    removed = 0
    for p in CONTROLLER_LOG_ROOT.glob("controller_run_*"):
        if not p.is_dir():
            continue
        try:
            if p.stat().st_mtime < cutoff:
                shutil.rmtree(str(p), ignore_errors=True)
                removed += 1
        except Exception:
            pass
    if removed:
        print("已自动清理 {} 个超过 {} 天的旧总控临时目录。".format(removed, KEEP_CONTROLLER_RUN_DAYS))


def newest_run_dir(structure_root, perturbation, mode):
    root = Path(structure_root) / "results" / perturbation
    if not root.exists():
        return None
    candidates = [p for p in root.glob("run_{}_*".format(mode)) if p.is_dir()]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def useful_run_result_count(run_dir):
    if run_dir is None or not Path(run_dir).exists():
        return 0
    run_dir = Path(run_dir)
    count = 0
    for name in ("03_transmission_abs2_png", "png"):
        folder = run_dir / name
        if folder.exists():
            count += len(list(folder.glob("*.png")))
    for name in ("02_transmission_excel", "excel", "xlsx"):
        folder = run_dir / name
        if folder.exists():
            count += len(list(folder.glob("*.xlsx")))
    if (run_dir / "04_logs" / "manifest.csv").exists():
        count += 1
    return count


def has_latest_result(item, mode):
    run_dir = newest_run_dir(item["structure_root"], item["perturbation"], mode)
    return useful_run_result_count(run_dir) > 0


def count_csv_rows(path):
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as f:
            return max(0, sum(1 for _ in f) - 1)
    except Exception:
        return None


def latest_result_text(item, mode):
    rd = newest_run_dir(item["structure_root"], item["perturbation"], mode)
    if rd is None:
        return "无"
    done = count_csv_rows(rd / "04_logs" / "manifest.csv")
    plan = count_csv_rows(rd / "00_scan_plan" / "scan_points.csv")
    extra = []
    if done is not None:
        extra.append("完成{}点".format(done))
    if plan is not None:
        extra.append("计划{}点".format(plan))
    return rd.name + (" ({})".format("，".join(extra)) if extra else "")


def latest_result_brief(item, mode):
    rd = newest_run_dir(item["structure_root"], item["perturbation"], mode)
    if rd is None:
        return "无"
    done = count_csv_rows(rd / "04_logs" / "manifest.csv")
    plan = count_csv_rows(rd / "00_scan_plan" / "scan_points.csv")
    parts = []
    if done is not None:
        parts.append("完成{}点".format(done))
    if plan is not None:
        parts.append("计划{}点".format(plan))
    return "{}{}".format(rd.name, "（{}）".format("，".join(parts)) if parts else "")


def supports_color():
    if not ENABLE_COLOR_OUTPUT:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


USE_COLOR = supports_color()


def color(text, code):
    if not USE_COLOR:
        return text
    return "\033[{}m{}\033[0m".format(code, text)


def run_state(item):
    has_test = newest_run_dir(item["structure_root"], item["perturbation"], "test") is not None
    has_full = newest_run_dir(item["structure_root"], item["perturbation"], "full") is not None
    if has_full:
        return "full", "FULL完整已跑", "32"   # green
    if has_test:
        return "test", "TEST仅测试", "33"       # yellow
    return "none", "TODO未跑", "90"          # gray


def collection_state(items):
    counts = {"full": 0, "test": 0, "none": 0}
    for item in items:
        state, _, _ = run_state(item)
        counts[state] += 1
    if counts["full"] and counts["full"] == len(items):
        summary = "FULL完整 {}/{} | TEST仅测试 0 | TODO未跑 0".format(counts["full"], len(items))
        code = "32"
    elif counts["full"]:
        summary = "FULL完整 {} | TEST仅测试 {} | TODO未跑 {}".format(counts["full"], counts["test"], counts["none"])
        code = "32"
    elif counts["test"]:
        summary = "FULL完整 0 | TEST仅测试 {} | TODO未跑 {}".format(counts["test"], counts["none"])
        code = "33"
    else:
        summary = "FULL完整 0 | TEST仅测试 0 | TODO未跑 {}".format(counts["none"])
        code = "90"
    return color("[{}]".format(summary), code)


def print_catalog(records):
    print("\n发现可运行脚本 {} 个：".format(len(records)))
    print("状态说明：FULL完整已跑 = 已跑过完整 full；TEST仅测试 = 只跑过 test 但未 full；TODO未跑 = test/full 都没有。")
    if USE_COLOR:
        print("颜色辅助：{} / {} / {}。".format(color("绿色=FULL", "32"), color("黄色=TEST", "33"), color("灰色=TODO", "90")))
    print("=" * 120)
    last_sym = last_mother = None
    for item in records:
        if item["symmetry"] != last_sym:
            print("[{}]".format(item["symmetry"]))
            last_sym = item["symmetry"]
            last_mother = None
        if item["mother"] != last_mother:
            print("  - {}".format(item["mother"]))
            last_mother = item["mother"]
        _, state_text, state_color = run_state(item)
        state_badge = color("状态={}".format(state_text), state_color)
        line = "      [{:03d}] {:<18} {:<44} {:<18} 最近test: {} | 最近full: {}".format(
            item["id"], item["perturbation"], item["script"].name, state_badge,
            latest_result_brief(item, "test"), latest_result_brief(item, "full")
        )
        print(line)
    print("=" * 120)


def parse_literal_assignments(script_path):
    text = Path(script_path).read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return OrderedDict(), text
    values = OrderedDict()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name == "CONFIG":
                break
            if not name.isupper():
                continue
            try:
                values[name] = ast.literal_eval(node.value)
            except Exception:
                pass
    return values, text


def fmt_um_from_nm(v):
    return "{:.4f} um".format(float(v) / 1000.0).rstrip("0").rstrip(".") + (" um" if "." not in "{:.4f}".format(float(v) / 1000.0).rstrip("0").rstrip(".") else "")


def fmt_value_by_key(key, value):
    if key.endswith("_NM"):
        return "{:.4f} um".format(float(value) / 1000.0)
    if key.endswith("_DEG"):
        return "{:.3f} deg".format(float(value))
    if key.endswith("_FS"):
        return "{:.3f} fs".format(float(value))
    if key.endswith("_S"):
        return "{:.3f} ps".format(float(value) * 1e12)
    return str(value)


def scan_groups(values):
    groups = []
    seen = set()

    def add_group(prefix, unit, start_key, end_key, step_key):
        key = (start_key, end_key, step_key)
        if key in seen:
            return
        if start_key in values and end_key in values and step_key in values:
            seen.add(key)
            groups.append({
                "prefix": prefix,
                "unit": unit,
                "start_key": start_key,
                "end_key": end_key,
                "step_key": step_key,
                "start": values[start_key],
                "end": values[end_key],
                "step": values[step_key],
            })

    for unit in ("NM", "M", "DEG"):
        add_group("SCAN", unit, "START_{}".format(unit), "END_{}".format(unit), "STEP_{}".format(unit))
    add_group("SCAN", "RAW", "START", "END", "STEP")

    # Support legacy names such as RADIUS_START_NM / DELTA_STOP_NM / ANGLE_STEP_DEG.
    for key in values:
        m = re.match(r"(.+)_START_(NM|M|DEG)$", key)
        if not m:
            continue
        prefix, unit = m.group(1), m.group(2)
        add_group(prefix, unit, key, "{}_STOP_{}".format(prefix, unit), "{}_STEP_{}".format(prefix, unit))
    return groups


def runtime_groups(values):
    groups = []
    for key in FDTD_RUNTIME_KEYS:
        if key in values:
            groups.append({"key": key, "value": values[key]})
    if "SIMULATION_TIME_FS" not in values:
        for key in LEGACY_FDTD_RUNTIME_KEYS:
            if key in values:
                groups.append({"key": key, "value": values[key]})
    return groups


def explain_script(item):
    values, _ = parse_literal_assignments(item["script"])
    groups = scan_groups(values)
    lines = []
    lines.append("[{:03d}] {} / {} / {}".format(item["id"], item["symmetry"], item["mother"], item["perturbation"]))
    lines.append("脚本：{}".format(item["script"].name))
    for g in groups:
        if g["unit"] == "NM":
            lines.append("  扫描范围：{} 从 {} 到 {}，步长 {}。".format(
                g["prefix"], fmt_value_by_key(g["start_key"], g["start"]),
                fmt_value_by_key(g["end_key"], g["end"]), fmt_value_by_key(g["step_key"], g["step"])
            ))
        else:
            lines.append("  扫描范围：{} 从 {} 到 {}，步长 {}。".format(
                g["prefix"], fmt_value_by_key(g["start_key"], g["start"]),
                fmt_value_by_key(g["end_key"], g["end"]), fmt_value_by_key(g["step_key"], g["step"])
            ))
    runtime_keys = FDTD_RUNTIME_KEYS if "SIMULATION_TIME_FS" in values else FDTD_RUNTIME_KEYS + LEGACY_FDTD_RUNTIME_KEYS
    for key in ("RUN_MODE_DEFAULT", "TEST_POINT_COUNT") + runtime_keys:
        if key in values:
            lines.append("  {}：{}".format(key, fmt_value_by_key(key, values[key])))
    if not groups:
        lines.append("  未识别到标准 start/end/step 组；仍可由原脚本自身控制。")
    return "\n".join(lines)


def select_records(records):
    while True:
        print("\n请选择运行范围：")
        print("  1 = 单个脚本")
        print("  2 = 多个脚本编号，例如 1,3,5-8")
        print("  3 = 某个母结构下全部脚本")
        print("  4 = 全部脚本")
        print("  5 = 只查看列表，不运行")
        print("  0 = 退出总控")
        choice = input("请输入 0/1/2/3/4/5：").strip()
        if choice in ("0", "5"):
            return []
        if choice == "1":
            raw = input("脚本编号，输入 0 返回上一级：").strip()
            if raw == "0":
                continue
            idx = int(raw)
            return [records[idx - 1]]
        if choice == "2":
            raw = input("脚本编号列表，输入 0 返回上一级：").replace("，", ",").strip()
            if raw == "0":
                continue
            ids = []
            for part in raw.split(","):
                part = part.strip()
                if not part:
                    continue
                if "-" in part:
                    a, b = [int(x.strip()) for x in part.split("-", 1)]
                    ids.extend(range(min(a, b), max(a, b) + 1))
                else:
                    ids.append(int(part))
            by_id = {x["id"]: x for x in records}
            return [by_id[i] for i in ids]
        if choice == "3":
            pairs = []
            seen = set()
            for item in records:
                key = (item["symmetry"], item["mother"])
                if key not in seen:
                    seen.add(key)
                    pairs.append(key)
            print("\n请选择母结构：")
            print("  [00] 返回上一级")
            for i, (sym, mother) in enumerate(pairs, 1):
                items = [x for x in records if x["symmetry"] == sym and x["mother"] == mother]
                print("  [{:02d}] {} / {} ({} 个脚本) {}".format(i, sym, mother, len(items), collection_state(items)))
            raw = input("母结构编号：").strip()
            if raw in ("0", "00"):
                continue
            idx = int(raw)
            sym, mother = pairs[idx - 1]
            return [x for x in records if x["symmetry"] == sym and x["mother"] == mother]
        if choice == "4":
            return list(records)
        print("只能输入 0/1/2/3/4/5，请重新选择。")


def choose_child_mode(default_mode):
    if default_mode != "ask":
        return default_mode
    while True:
        print("\n请选择传给子脚本的模式：")
        print("  1 = preview：只生成计划，不仿真")
        print("  2 = test：每个脚本只跑测试点")
        print("  3 = full：完整仿真")
        print("说明：PyCharm 运行窗口不能稳定把输入继续传给子脚本，所以总控不再使用 child ask。")
        choice = input("请输入 1/2/3：").strip()
        if choice in ("1", "2", "3"):
            return {"1": "preview", "2": "test", "3": "full"}[choice]
        print("只能输入 1/2/3，请重新选择。")


def choose_run_style(default_style, child_mode):
    if child_mode == "ask":
        return "sequential"
    if default_style != "ask":
        return default_style
    print("\n请选择运行方式：")
    print("  1 = 依次运行，最稳")
    print("  2 = 并行运行，适合 preview；真实仿真请谨慎")
    style = {"1": "sequential", "2": "parallel"}[input("请输入 1/2：").strip()]
    if style == "parallel" and child_mode == "full":
        if input("full 并行很占资源，输入 YES 确认：").strip() != "YES":
            return "sequential"
    return style


def suspicious_override(unit, start, end, step):
    if step is not None and float(step) <= 0:
        return "step 必须大于 0"
    if unit == "NM":
        biggest = max(abs(float(start or 0)), abs(float(end or 0)), abs(float(step or 0)))
        if biggest > SOFT_LENGTH_LIMIT_UM * 1000.0:
            return "长度参数超过 {:.3f} um 的软限制".format(SOFT_LENGTH_LIMIT_UM)
    if unit == "DEG":
        biggest = max(abs(float(start or 0)), abs(float(end or 0)), abs(float(step or 0)))
        if biggest > SOFT_ANGLE_LIMIT_DEG:
            return "角度参数超过 {:.1f} deg 的软限制".format(SOFT_ANGLE_LIMIT_DEG)
    return None


def ask_overrides(selected):
    print("\n是否在总控中临时覆盖 start/end/step 和 FDTD 运行参数？")
    print("FDTD 参数包括：simulation time (fs)、auto shutoff min、mesh accuracy、dt stability factor。")
    print("说明：这是临时覆盖，会生成临时脚本副本运行，不修改原脚本。")
    if input("输入 y 开始设置，其他键跳过：").strip().lower() != "y":
        return {}

    overrides = {}
    for item in selected:
        values, _ = parse_literal_assignments(item["script"])
        groups = scan_groups(values)
        runtime = runtime_groups(values)
        if not groups and not runtime:
            continue
        print("\n" + explain_script(item))
        repl = {}

        if groups:
            if len(groups) == 1:
                group = groups[0]
            else:
                print("该脚本有多个扫描组：")
                for i, g in enumerate(groups, 1):
                    print("  [{}] {} ({})".format(i, g["prefix"], g["unit"]))
                group = groups[int(input("请选择要覆盖的扫描组编号：").strip()) - 1]
            if input("是否覆盖这个脚本的 {} start/end/step？y/N：".format(group["prefix"])).strip().lower() == "y":
                raw_start = input("start，空白表示不改，当前 {}：".format(fmt_value_by_key(group["start_key"], group["start"]))).strip()
                raw_end = input("end，空白表示不改，当前 {}：".format(fmt_value_by_key(group["end_key"], group["end"]))).strip()
                raw_step = input("step，空白表示不改，当前 {}：".format(fmt_value_by_key(group["step_key"], group["step"]))).strip()
                start = float(raw_start) if raw_start else None
                end = float(raw_end) if raw_end else None
                step = float(raw_step) if raw_step else None
                warn = suspicious_override(group["unit"], start, end, step)
                if warn:
                    ans = input("警告：{}。是否仍继续？输入 YES 继续：".format(warn)).strip()
                    if ans != "YES":
                        start = end = step = None
                if start is not None:
                    repl[group["start_key"]] = start
                if end is not None:
                    repl[group["end_key"]] = end
                if step is not None:
                    repl[group["step_key"]] = step

        if runtime and input("是否覆盖这个脚本的 FDTD 运行参数？y/N：").strip().lower() == "y":
            for group in runtime:
                key = group["key"]
                raw = input("{}，空白表示不改，当前 {}：".format(key, fmt_value_by_key(key, values.get(key)))).strip()
                if not raw:
                    continue
                value = float(raw)
                if value <= 0:
                    print("{} 必须大于 0，已忽略。".format(key))
                    continue
                repl[key] = value

        if repl:
            overrides[str(item["script"])] = repl
    return overrides


def parse_overrides_json(raw):
    if not raw:
        return {}
    path = Path(raw)
    if path.exists():
        raw = path.read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    overrides = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                key_text = str(key)
                if key_text != "*":
                    try:
                        key_text = str(Path(key_text).resolve())
                    except Exception:
                        pass
                overrides[key_text] = {str(k): v for k, v in value.items() if v not in (None, "")}
    return overrides


def select_records_noninteractive(records, ids_raw, run_all=False):
    if run_all:
        return list(records)
    if not ids_raw:
        return None
    ids = []
    for part in str(ids_raw).replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = [int(x.strip()) for x in part.split("-", 1)]
            ids.extend(range(min(a, b), max(a, b) + 1))
        else:
            ids.append(int(part))
    by_id = {x["id"]: x for x in records}
    return [by_id[i] for i in ids if i in by_id]


def filter_missing_results(records, mode):
    return [item for item in records if not has_latest_result(item, mode)]


def replace_assignments(text, replacements):
    if "SIMULATION_TIME_FS" in replacements and "SIMULATION_TIME_S" not in replacements:
        try:
            replacements = dict(replacements)
            replacements["SIMULATION_TIME_S"] = float(replacements["SIMULATION_TIME_FS"]) * 1e-15
        except (TypeError, ValueError):
            pass
    config_key_aliases = {
        "SIMULATION_TIME_FS": ("simulation_time_fs", "SIMULATION_TIME_FS"),
        "SIMULATION_TIME_S": ("simulation_time_s", "SIMULATION_TIME_S"),
        "AUTO_SHUTOFF_MIN": ("auto_shutoff_min", "AUTO_SHUTOFF_MIN"),
        "MESH_ACCURACY": ("mesh_accuracy", "MESH_ACCURACY"),
        "DT_STABILITY_FACTOR": ("dt_stability_factor", "DT_STABILITY_FACTOR"),
        "AUTO_RETRY_ENABLED": ("auto_retry_enabled", "AUTO_RETRY_ENABLED", "autoretryenabled"),
        "AUTO_RETRY_MODE": ("auto_retry_mode", "AUTO_RETRY_MODE", "autoretrymode"),
        "AUTO_RETRY_MAX": ("auto_retry_max", "AUTO_RETRY_MAX", "autoretrymax"),
        "AUTO_RETRY_HARD_CAP": ("auto_retry_hard_cap", "AUTO_RETRY_HARD_CAP", "autoretryhardcap"),
        "AUTO_RETRY_PATIENCE": ("auto_retry_patience", "AUTO_RETRY_PATIENCE", "autoretrypatience"),
        "AUTO_RETRY_MIN_IMPROVE": ("auto_retry_min_improve", "AUTO_RETRY_MIN_IMPROVE", "autoretryminimprove"),
        "AUTO_RETRY_WEAK_IMPROVE": ("auto_retry_weak_improve", "AUTO_RETRY_WEAK_IMPROVE", "autoretryweakimprove"),
        "AUTO_RETRY_TIME_BUDGET_S": ("auto_retry_time_budget_s", "AUTO_RETRY_TIME_BUDGET_S", "autoretrytimebudgets"),
        "AUTO_RETRY_MAX_SINGLE_RUN_S": ("auto_retry_max_single_run_s", "AUTO_RETRY_MAX_SINGLE_RUN_S", "autoretrymaxsingleruns"),
        "QUALITY_T_LIMIT": ("quality_t_limit", "QUALITY_T_LIMIT", "qualitytlimit"),
        "QUALITY_RIPPLE_LIMIT": ("quality_ripple_limit", "QUALITY_RIPPLE_LIMIT", "qualityripplelimit"),
        "QUALITY_MIN_POINTS": ("quality_min_points", "QUALITY_MIN_POINTS", "qualityminpoints"),
    }
    pending_config_updates = {}
    for name, value in replacements.items():
        if value in (None, ""):
            continue
        literal = repr(value)
        applied = 0

        # Replace top-level assignments such as AUTO_SHUTOFF_MIN = 1e-12.
        pattern = re.compile(r"^({}\s*=\s*)(.+?)\s*$".format(re.escape(name)), re.M)
        text, n = pattern.subn(r"\g<1>{}".format(literal), text, count=1)
        applied += n

        # Replace CONFIG = dict(AUTO_SHUTOFF_MIN=...) keyword entries.
        kw_pattern = re.compile(r"(\b{}\s*=\s*)([^,\n\)]+)".format(re.escape(name)))
        text, n = kw_pattern.subn(r"\g<1>{}".format(literal), text, count=1)
        applied += n

        # Replace older CONFIG {"auto_shutoff_min": ...} entries.
        config_keys = config_key_aliases.get(name, ())
        for config_key in config_keys:
            dict_pattern = re.compile(r"((?:['\"]{}['\"])\s*:\s*)([^,\n\}}]+)".format(re.escape(config_key)))
            text, n = dict_pattern.subn(r"\g<1>{}".format(literal), text, count=1)
            applied += n
            pending_config_updates[config_key] = value

        if applied:
            print("override applied: {} = {}".format(name, value))
        elif config_key_aliases.get(name):
            print("override queued for CONFIG injection: {} = {}".format(name, value))
        else:
            print("warning: override target not found in script: {}".format(name))

    if pending_config_updates and "CONFIG" in text:
        payload = ", ".join("{!r}: {!r}".format(k, v) for k, v in pending_config_updates.items())
        injection = "\n# Runtime overrides injected by fdtd_master_controller.py\nCONFIG.update({%s})\n" % payload
        marker = 'if __name__ == "__main__":'
        if marker in text:
            text = text.replace(marker, injection + "\n" + marker, 1)
        else:
            text += injection
    return text

def prepare_script_for_run(item, run_root, overrides):
    script_path = Path(item["script"])
    try:
        rel_script = str(script_path.resolve().relative_to(STRUCT_ROOT.resolve()))
    except Exception:
        rel_script = str(script_path)
    repl = (
        overrides.get(str(item["script"]))
        or overrides.get(str(script_path))
        or overrides.get(str(script_path.resolve()))
        or overrides.get(rel_script)
        or overrides.get("*")
    )
    if not repl:
        return item["script"]
    _, text = parse_literal_assignments(item["script"])
    text = replace_assignments(text, repl)
    # Keep temporary scripts beside the original script so sibling *_common.py imports work.
    temp_script = item["script"].parent / ("_controller_temp_{}_{}".format(int(time.time() * 1000), item["script"].name))
    temp_script.write_text(text, encoding="utf-8")
    return temp_script


def cleanup_temp_script(script, original_script):
    try:
        script = Path(script)
        original_script = Path(original_script)
        if script != original_script and script.name.startswith("_controller_temp_") and script.parent == original_script.parent:
            script.unlink()
    except Exception:
        pass


def script_cli_style(script):
    """Return the command-line style supported by a child script."""
    try:
        text = script.read_text(encoding="utf-8", errors="replace")
    except Exception:
        text = ""

    # Many generated scripts delegate argparse to a sibling *_common.py module.
    for module_name in re.findall(r"from\s+([A-Za-z_][A-Za-z0-9_]*_common)\s+import\s+run", text):
        common_candidates = [
            script.parent / (module_name + ".py"),
            script.parent.parent / (module_name + ".py"),
            script.parent.parent.parent / (module_name + ".py"),
            script.parent.parent.parent.parent / (module_name + ".py"),
            STRUCT_ROOT / (module_name + ".py"),
        ]
        for common_path in common_candidates:
            if common_path.exists():
                try:
                    text += "\n" + common_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass
                break

    if '"--mode"' in text or "'--mode'" in text:
        return "mode"
    if '"--test-run"' in text or "'--test-run'" in text or '"--full-run"' in text or "'--full-run'" in text:
        return "legacy_run"
    if '"--test"' in text or "'--test'" in text or '"--full"' in text or "'--full'" in text:
        return "short_flags"
    return "interactive_only"


def command_for(script, child_mode):
    cmd = [str(PYTHON_EXE), str(script)]
    if child_mode != "ask":
        style = script_cli_style(script)
        if style == "mode":
            cmd += ["--mode", child_mode]
        elif style == "legacy_run":
            cmd += {"preview": ["--preview"], "test": ["--test-run"], "full": ["--full-run"]}[child_mode]
        elif style == "short_flags":
            cmd += {"preview": ["--preview"], "test": ["--test"], "full": ["--full"]}[child_mode]
        else:
            print("提示：{} 未检测到命令行模式参数，将按脚本默认交互/默认模式运行。".format(script.name))
    return cmd


def kill_process_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.call(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        proc.kill()


def read_hotkey_nonblocking():
    """Windows 控制台非阻塞读按键。没有按键时返回 None。"""
    if os.name != "nt":
        return None
    try:
        import msvcrt
        if not msvcrt.kbhit():
            return None
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0") and msvcrt.kbhit():
            ch = msvcrt.getwch()
        return ch.lower()
    except Exception:
        return None


def start_stdin_command_listener():
    """PyCharm 运行窗口通常不支持 msvcrt 热键；这里改用 输入字母+回车。"""
    global STDIN_LISTENER_STARTED
    with STDIN_LISTENER_LOCK:
        if STDIN_LISTENER_STARTED:
            return
        STDIN_LISTENER_STARTED = True

        def listen():
            while True:
                try:
                    line = sys.stdin.readline()
                except Exception:
                    break
                if not line:
                    break
                command = line.strip().lower()
                if command:
                    STDIN_COMMANDS.put(command)

        thread = threading.Thread(target=listen)
        thread.daemon = True
        thread.start()


def read_stdin_command_nonblocking():
    try:
        return STDIN_COMMANDS.get_nowait()
    except queue.Empty:
        return None


def make_interrupt_record(item, script, action, current):
    return {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "id": item["id"],
        "symmetry": item["symmetry"],
        "mother": item["mother"],
        "perturbation": item["perturbation"],
        "script": str(script),
        "current_point": current.get("point") or "未捕获到当前扫描点输出",
        "current_param": current.get("param") or "未捕获到当前参数输出",
    }


def make_failure_record(item, script, code, current, stdout_path, stderr_path):
    return {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "子脚本异常退出",
        "id": item["id"],
        "symmetry": item["symmetry"],
        "mother": item["mother"],
        "perturbation": item["perturbation"],
        "script": str(script),
        "exit_code": code,
        "current_point": current.get("point") or "未捕获到当前扫描点输出",
        "current_param": current.get("param") or "未捕获到当前参数输出",
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
    }


def remember_interrupt(record):
    if not record:
        return
    with INTERRUPTED_LOCK:
        INTERRUPTED_TASKS.append(record)


def remember_failure(record):
    if not record:
        return
    with FAILED_LOCK:
        FAILED_TASKS.append(record)


def print_interrupt_summary(run_root=None):
    if not INTERRUPTED_TASKS:
        return
    print("\n中断/跳过记录汇总：")
    print("=" * 96)
    for i, rec in enumerate(INTERRUPTED_TASKS, 1):
        print("[{}] {} | {} / {} / {} | {}".format(
            i, rec["action"], rec["symmetry"], rec["mother"], rec["perturbation"], rec["time"]
        ))
        print("    脚本：{}".format(rec["script"]))
        print("    当前仿真：{}".format(rec["current_point"]))
        print("    当前参数：{}".format(rec["current_param"]))
    print("=" * 96)
    if run_root is not None:
        out = Path(run_root) / "interrupted_tasks.csv"
        try:
            with out.open("w", newline="", encoding="utf-8-sig") as f:
                fields = ["time", "action", "id", "symmetry", "mother", "perturbation", "script", "current_point", "current_param"]
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for rec in INTERRUPTED_TASKS:
                    writer.writerow(rec)
            print("中断记录已保存：{}".format(out))
        except Exception as e:
            print("中断记录保存失败：{}".format(e))


def print_failure_summary(run_root=None):
    if not FAILED_TASKS:
        return
    print("\n失败脚本汇总：")
    print("=" * 96)
    for i, rec in enumerate(FAILED_TASKS, 1):
        print("[{}] 退出码 {} | [{:03d}] {} / {} / {} | {}".format(
            i, rec["exit_code"], rec["id"], rec["symmetry"], rec["mother"], rec["perturbation"], rec["time"]
        ))
        print("    脚本：{}".format(rec["script"]))
        print("    当前仿真：{}".format(rec["current_point"]))
        print("    当前参数：{}".format(rec["current_param"]))
        print("    stderr 日志：{}".format(rec["stderr_log"]))
    print("=" * 96)
    if run_root is not None:
        out = Path(run_root) / "failed_tasks.csv"
        try:
            with out.open("w", newline="", encoding="utf-8-sig") as f:
                fields = [
                    "time", "action", "id", "symmetry", "mother", "perturbation",
                    "script", "exit_code", "current_point", "current_param",
                    "stdout_log", "stderr_log",
                ]
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for rec in FAILED_TASKS:
                    writer.writerow(rec)
            print("失败记录已保存：{}".format(out))
        except Exception as e:
            print("失败记录保存失败：{}".format(e))


def stream_process(item, script, child_mode, log_dir, child_timeout_s=None):
    cmd = command_for(script, child_mode)
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / (safe_token(item["mother"] + "_" + item["perturbation"]) + "_stdout.log")
    stderr_path = log_dir / (safe_token(item["mother"] + "_" + item["perturbation"]) + "_stderr.log")
    print("\n启动 [{:03d}] {} / {}：{}".format(item["id"], item["mother"], item["perturbation"], " ".join(cmd)))
    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "{}:replace".format(CHILD_OUTPUT_ENCODING)
    with stdout_path.open("w", encoding="utf-8", errors="replace") as out, stderr_path.open("w", encoding="utf-8", errors="replace") as err:
        # Lumerical v202 自带的是 Python 3.6；subprocess.Popen 的 text=True
        # 是 Python 3.7+ 的别名。这里使用 universal_newlines=True 保持兼容。
        proc = subprocess.Popen(
            cmd,
            cwd=str(script.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=sys.stdin if child_mode == "ask" else subprocess.DEVNULL,
            universal_newlines=True,
            encoding=CHILD_OUTPUT_ENCODING,
            errors="replace",
            env=child_env,
        )

        current = {"point": "", "param": ""}
        started_at = time.time()
        child_timeout_s = float(child_timeout_s or 0)

        def capture_current(line):
            text = line.strip()
            if "开始仿真" in text:
                current["point"] = text
            if "当前参数" in text:
                current["param"] = text

        def pump(src, file_obj, prefix):
            for line in iter(src.readline, ""):
                file_obj.write(line)
                file_obj.flush()
                capture_current(line)
                safe_console_print(prefix + line, end="")
        t1 = threading.Thread(target=pump, args=(proc.stdout, out, "[{:03d} OUT] ".format(item["id"])))
        t2 = threading.Thread(target=pump, args=(proc.stderr, err, "[{:03d} ERR] ".format(item["id"])))
        t1.daemon = True
        t2.daemon = True
        t1.start()
        t2.start()
        if child_mode != "ask":
            start_stdin_command_listener()
        print("[总控中断命令] 标准终端可直接按 s/n/q；PyCharm 请在运行窗口输入 s 或 n 后回车=跳过当前仿真，输入 q 后回车=结束当前仿真并退出总控。")
        try:
            while True:
                code = proc.poll()
                if code is not None:
                    break
                if child_timeout_s > 0 and (time.time() - started_at) > child_timeout_s:
                    print("\nChild timeout: killing [{:03d}] after {:.0f}s. Increase --child-timeout-s if this point is expected to run longer.".format(item["id"], child_timeout_s))
                    kill_process_tree(proc)
                    record = make_failure_record(item, script, "timeout_{}s".format(int(child_timeout_s)), current, stdout_path, stderr_path)
                    remember_failure(record)
                    raise ChildScriptError(record)
                key = read_hotkey_nonblocking()
                command = read_stdin_command_nonblocking()
                action = command or key
                if action in ("q", "quit", "exit", "\x1b"):
                    print("\n收到 q：正在结束当前子脚本和 FDTD 进程树，并退出总控...")
                    kill_process_tree(proc)
                    record = make_interrupt_record(item, script, "退出总控", current)
                    remember_interrupt(record)
                    raise StopController(record)
                if action in ("s", "n", "skip", "next"):
                    print("\n收到 s/n：正在结束当前子脚本和 FDTD 进程树，并跳过当前任务...")
                    kill_process_tree(proc)
                    record = make_interrupt_record(item, script, "跳过当前仿真并继续", current)
                    remember_interrupt(record)
                    raise SkipCurrentTask(record)
                if action == "p":
                    print("\n提示：为了避免破坏 FDTD 内部状态，总控没有外部暂停/恢复正在运行仿真的功能。可按 s 跳过或 q 退出。")
                time.sleep(0.25)
        except KeyboardInterrupt:
            print("\n收到 Ctrl+C，正在结束子脚本和它启动的 FDTD 进程树...")
            kill_process_tree(proc)
            record = make_interrupt_record(item, script, "Ctrl+C 中断", current)
            remember_interrupt(record)
            raise
        t1.join(timeout=2)
        t2.join(timeout=2)
        if code != 0:
            record = make_failure_record(item, script, code, current, stdout_path, stderr_path)
            remember_failure(record)
            raise ChildScriptError(record)
    return 0


def run_sequential(selected, child_mode, run_root, overrides, child_timeout_s=None):
    log_dir = run_root / "logs"
    for item in selected:
        script = prepare_script_for_run(item, run_root, overrides)
        try:
            stream_process(item, script, child_mode, log_dir, child_timeout_s)
        except SkipCurrentTask as e:
            print("已跳过 [{:03d}] {} / {}，继续下一个任务。".format(item["id"], item["mother"], item["perturbation"]))
            print("    被跳过的当前仿真：{}".format(e.record.get("current_point")))
            print("    被跳过的当前参数：{}".format(e.record.get("current_param")))
            continue
        except ChildScriptError as e:
            print("警告：[{:03d}] {} / {} 子脚本异常退出，退出码 {}。总控将继续下一个任务。".format(
                item["id"], item["mother"], item["perturbation"], e.record.get("exit_code")
            ))
            print("    当前仿真：{}".format(e.record.get("current_point")))
            print("    当前参数：{}".format(e.record.get("current_param")))
            print("    错误日志：{}".format(e.record.get("stderr_log")))
            continue
        except StopController:
            raise
        finally:
            cleanup_temp_script(script, item["script"])


def run_parallel(selected, child_mode, run_root, overrides, max_parallel, child_timeout_s=None):
    # 简洁稳定的并行：每批最多 max_parallel 个；每个线程内部实时转发输出。
    remaining = list(selected)
    while remaining:
        batch = remaining[:max_parallel]
        remaining = remaining[max_parallel:]
        errors = []
        threads = []
        def worker(item):
            script = item["script"]
            try:
                script = prepare_script_for_run(item, run_root, overrides)
                stream_process(item, script, child_mode, run_root / "logs", child_timeout_s)
            except ChildScriptError as e:
                print("警告：[{:03d}] {} / {} 子脚本异常退出，退出码 {}。".format(
                    item["id"], item["mother"], item["perturbation"], e.record.get("exit_code")
                ))
            except Exception as e:
                errors.append(e)
            finally:
                cleanup_temp_script(script, item["script"])
        for item in batch:
            t = threading.Thread(target=worker, args=(item,))
            t.start()
            threads.append(t)
        try:
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            print("\n收到 Ctrl+C。并行任务的子进程会由各线程清理；如仍有 FDTD 窗口残留，请在任务管理器检查。")
            raise
        if errors:
            raise errors[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["ask", "preview", "test", "full"], default=DEFAULT_CHILD_MODE)
    parser.add_argument("--style", choices=["ask", "sequential", "parallel"], default=DEFAULT_RUN_STYLE)
    parser.add_argument("--max-parallel", type=int, default=DEFAULT_MAX_PARALLEL)
    parser.add_argument("--ids", default="", help="Non-interactive script ids, e.g. 1,3,5-8")
    parser.add_argument("--all", action="store_true", help="Run all discovered child scripts non-interactively")
    parser.add_argument("--missing-only", action="store_true", help="Run only scripts without a usable latest result for the selected mode")
    parser.add_argument("--overrides-json", default="", help="JSON string or JSON file path for temporary assignment overrides")
    parser.add_argument("--auto-retry-max", default=None, help="Global AUTO_RETRY_MAX override: adaptive | 0 | positive integer")
    parser.add_argument("--auto-retry-mode", choices=["fixed", "adaptive"], default=None, help="Global AUTO_RETRY_MODE override")
    parser.add_argument("--auto-retry-hard-cap", type=int, default=None, help="Global AUTO_RETRY_HARD_CAP override")
    parser.add_argument("--auto-retry-patience", type=int, default=None, help="Global AUTO_RETRY_PATIENCE override")
    parser.add_argument("--auto-retry-min-improve", type=float, default=None, help="Global AUTO_RETRY_MIN_IMPROVE override")
    parser.add_argument("--auto-retry-time-budget-s", type=float, default=None, help="Global AUTO_RETRY_TIME_BUDGET_S override")
    parser.add_argument("--auto-retry-max-single-run-s", type=float, default=None, help="Global AUTO_RETRY_MAX_SINGLE_RUN_S override")
    parser.add_argument("--quality-t-limit", type=float, default=None, help="Global QUALITY_T_LIMIT override for selected scripts")
    parser.add_argument("--quality-ripple-limit", type=float, default=None, help="Global QUALITY_RIPPLE_LIMIT override for selected scripts")
    parser.add_argument("--quality-min-points", type=int, default=None, help="Global QUALITY_MIN_POINTS override for selected scripts")
    parser.add_argument("--disable-auto-retry", action="store_true", help="Global AUTO_RETRY_ENABLED=False override for selected scripts")
    parser.add_argument("--child-timeout-s", type=float, default=3600.0, help="Kill a child script and its FDTD process tree after this many seconds; 0 disables")
    parser.add_argument("--yes", action="store_true", help="Skip final confirmation for non-interactive/web runs")
    args = parser.parse_args()
    ensure_numpy_available(PYTHON_EXE)

    cleanup_old_controller_runs()
    records = discover_scripts(STRUCT_ROOT)
    print_catalog(records)
    selected = select_records_noninteractive(records, args.ids, args.all or args.missing_only)
    noninteractive = selected is not None
    if selected is None:
        selected = select_records(records)
    if not selected:
        print("未选择运行脚本，总控结束。")
        return

    child_mode = args.mode if noninteractive and args.mode != "ask" else choose_child_mode(args.mode)
    run_style = args.style if noninteractive and args.style != "ask" else choose_run_style(args.style, child_mode)
    if run_style == "ask":
        run_style = "sequential"

    if args.missing_only:
        before_count = len(selected)
        selected = filter_missing_results(selected, child_mode)
        print("\n--missing-only: {} -> {} scripts without latest {} results.".format(before_count, len(selected), child_mode))
        if not selected:
            print("No scripts need to run for mode '{}'.".format(child_mode))
            return

    print("\n运行前检查：")
    print("=" * 96)
    for item in selected:
        print(explain_script(item))
    print("=" * 96)

    overrides = parse_overrides_json(args.overrides_json) if args.overrides_json else ({} if noninteractive else ask_overrides(selected))
    controller_extra_overrides = {}
    if args.auto_retry_max is not None:
        text = str(args.auto_retry_max).strip().lower()
        if text == "adaptive":
            controller_extra_overrides["AUTO_RETRY_MODE"] = "adaptive"
            controller_extra_overrides["AUTO_RETRY_MAX"] = "adaptive"
        else:
            try:
                v = int(float(args.auto_retry_max))
            except ValueError:
                raise ValueError("--auto-retry-max must be adaptive or a number")
            controller_extra_overrides["AUTO_RETRY_MODE"] = "fixed"
            controller_extra_overrides["AUTO_RETRY_MAX"] = max(0, v)
    if args.auto_retry_mode is not None:
        controller_extra_overrides["AUTO_RETRY_MODE"] = str(args.auto_retry_mode)
    if args.auto_retry_hard_cap is not None:
        controller_extra_overrides["AUTO_RETRY_HARD_CAP"] = int(args.auto_retry_hard_cap)
    if args.auto_retry_patience is not None:
        controller_extra_overrides["AUTO_RETRY_PATIENCE"] = int(args.auto_retry_patience)
    if args.auto_retry_min_improve is not None:
        controller_extra_overrides["AUTO_RETRY_MIN_IMPROVE"] = float(args.auto_retry_min_improve)
    if args.auto_retry_time_budget_s is not None:
        controller_extra_overrides["AUTO_RETRY_TIME_BUDGET_S"] = float(args.auto_retry_time_budget_s)
    if args.auto_retry_max_single_run_s is not None:
        controller_extra_overrides["AUTO_RETRY_MAX_SINGLE_RUN_S"] = float(args.auto_retry_max_single_run_s)
    if args.quality_t_limit is not None:
        controller_extra_overrides["QUALITY_T_LIMIT"] = float(args.quality_t_limit)
    if args.quality_ripple_limit is not None:
        controller_extra_overrides["QUALITY_RIPPLE_LIMIT"] = float(args.quality_ripple_limit)
    if args.quality_min_points is not None:
        controller_extra_overrides["QUALITY_MIN_POINTS"] = int(args.quality_min_points)
    if args.disable_auto_retry:
        controller_extra_overrides["AUTO_RETRY_ENABLED"] = False

    if "*" in overrides:
        wildcard = overrides.pop("*")
        for item in selected:
            existing = dict(overrides.get(str(item["script"]), {}))
            merged = dict(wildcard)
            merged.update(existing)
            overrides[str(item["script"])] = merged
    if controller_extra_overrides:
        for item in selected:
            key = str(item["script"])
            existing = dict(overrides.get(key, {}))
            existing.update(controller_extra_overrides)
            overrides[key] = existing
    print("\n最终将运行 {} 个脚本；模式：{}；方式：{}。".format(len(selected), child_mode, run_style))
    if overrides:
        print("已设置临时参数覆盖：")
        for path, repl in overrides.items():
            print("  {} -> {}".format(Path(path).name, repl))
    if not args.yes:
        if input("\u786e\u8ba4\u5f00\u59cb\uff1f\u8f93\u5165 YES\uff1a").strip() != "YES":
            print("\u5df2\u53d6\u6d88\u3002")
            return
    else:
        print("\u5df2\u901a\u8fc7 --yes \u8df3\u8fc7\u6700\u7ec8\u786e\u8ba4\u3002")

    run_root = CONTROLLER_LOG_ROOT / ("controller_run_" + now_stamp())
    run_root.mkdir(parents=True, exist_ok=True)
    try:
        if run_style == "parallel":
            run_parallel(selected, child_mode, run_root, overrides, max(1, args.max_parallel), args.child_timeout_s)
        else:
            run_sequential(selected, child_mode, run_root, overrides, args.child_timeout_s)
    except StopController:
        print("\n总控已按你的指令退出。")
        print_interrupt_summary(run_root)
        print_failure_summary(run_root)
        return
    except KeyboardInterrupt:
        print("\n总控已收到中断并尝试结束当前子进程树。")
        print_interrupt_summary(run_root)
        print_failure_summary(run_root)
        return
    print_interrupt_summary(run_root)
    print_failure_summary(run_root)
    print("\n全部任务结束。总控日志目录：{}".format(run_root))


if __name__ == "__main__":
    main()
