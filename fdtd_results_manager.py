# -*- coding: utf-8 -*-
"""
FDTD 仿真结果整理脚本
====================

放置位置：
    H:\\FDTD outcome\\struct\\群论_struct\\fdtd_results_manager.py

用途：
    扫描本目录层级下所有母结构的 results 文件夹，识别每个扰动下的 run_* 结果目录，
    并帮助你把旧结果移动到：

        results\\某扰动\\旧文件\\test\\待考察
        results\\某扰动\\旧文件\\full\\待考察

    如果存在 preview 或无法识别类型的旧结果，为避免误删，会额外放到：

        results\\某扰动\\旧文件\\preview\\待考察
        results\\某扰动\\旧文件\\unknown\\待考察

    每次运行脚本都会清空所有：

        旧文件\\*\\无效

    但不会主动删除“良好”和“待考察”里的内容。

核心规则：
    1. 不碰任何 fsp 源文件，不碰 coding 脚本。
    2. 每个 results\\扰动 文件夹下，整理后只保留：
       - 最新的一个 run_* 当前结果文件夹；
       - 一个“旧文件”归档文件夹。
    3. 其余 run_* 默认移动到“旧文件\\类型\\待考察”。
    4. 你人工看完“待考察”后，可以手动移动到“良好”或“无效”。
    5. 下次运行本脚本时，“无效”里面的内容会被自动删除。
"""
from __future__ import print_function

import argparse
import datetime
import os
import re
import shutil
import sys
from collections import OrderedDict
from pathlib import Path


# ========================= 用户主要修改区 =========================
STRUCT_ROOT = Path(__file__).resolve().parent

# 旧结果统一放在每个 results\\扰动\\旧文件 下。
ARCHIVE_DIR_NAME = "旧文件"

# 归档分类。test/full 是你主要关心的类型；preview/unknown 用于兜底，避免误删。
MODE_DIRS = ("test", "full", "preview", "unknown")
QUALITY_DIRS = ("良好", "待考察", "无效")

# 自动整理时，每个扰动目录下保留几个最新 run_* 作为“当前结果”。
# 按你的要求默认只保留 1 个。
KEEP_LATEST_ACTIVE_RUNS = 1

# True：每次启动脚本都清空“旧文件\\*\\无效”里的内容。
AUTO_DELETE_INVALID = True

# True：整理时用“移动到待考察”作为默认保存方式；False 时只扫描，不主动移动。
DEFAULT_ARCHIVE_TO_REVIEW = True
# ================================================================


def now_stamp():
    n = datetime.datetime.now()
    return "{:04d}{:02d}{:02d}_{:02d}{:02d}{:02d}".format(
        n.year, n.month, n.day, n.hour, n.minute, n.second
    )


def safe_print(text=""):
    try:
        print(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(str(text).encode(enc, errors="replace").decode(enc, errors="replace"))


def is_run_dir(path):
    return path.is_dir() and path.name.lower().startswith("run_")


def detect_run_mode(path):
    """
    从 run 文件夹名称识别 test/full/preview。
    示例：
        run_test_2026年5月7日_xxx -> test
        run_full_2026年4月29日_xxx -> full
        run_preview_2026年5月7日_xxx -> preview
    """
    name = path.name.lower()
    if re.match(r"^run[_-]test([_-]|$)", name):
        return "test"
    if re.match(r"^run[_-]full([_-]|$)", name):
        return "full"
    if re.match(r"^run[_-]preview([_-]|$)", name):
        return "preview"

    # 某些早期脚本可能把模式放在其他位置，做一个保守兜底。
    if "test" in name:
        return "test"
    if "full" in name:
        return "full"
    if "preview" in name:
        return "preview"
    return "unknown"


def format_mtime(path):
    t = datetime.datetime.fromtimestamp(path.stat().st_mtime)
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        t.year, t.month, t.day, t.hour, t.minute, t.second
    )


def ensure_archive_tree(perturbation_results_dir):
    old_root = perturbation_results_dir / ARCHIVE_DIR_NAME
    for mode in MODE_DIRS:
        for quality in QUALITY_DIRS:
            (old_root / mode / quality).mkdir(parents=True, exist_ok=True)
    return old_root


def unique_destination(dst):
    if not dst.exists():
        return dst
    suffix = "_archived_" + now_stamp()
    candidate = dst.with_name(dst.name + suffix)
    index = 2
    while candidate.exists():
        candidate = dst.with_name(dst.name + suffix + "_{:02d}".format(index))
        index += 1
    return candidate


def remove_children(folder, dry_run=False):
    if not folder.exists():
        return 0
    count = 0
    for item in list(folder.iterdir()):
        if not dry_run:
            if item.is_dir():
                shutil.rmtree(str(item))
            else:
                item.unlink()
        count += 1
    return count


def clean_invalid_in(old_root, dry_run=False):
    deleted = 0
    for mode in MODE_DIRS:
        invalid = old_root / mode / "无效"
        if not dry_run:
            invalid.mkdir(parents=True, exist_ok=True)
        deleted += remove_children(invalid, dry_run=dry_run)
    return deleted


def discover_perturbation_result_dirs(root):
    """
    返回所有 results\\扰动 目录。
    判定方式：
        - 目录名叫 results；
        - 它的直接子目录是某个扰动名；
        - 该扰动目录下存在 run_* 或旧文件。
    """
    found = []
    for results_dir in root.rglob("results"):
        if not results_dir.is_dir():
            continue
        # 跳过归档目录内部偶然出现的 results 字样。
        if ARCHIVE_DIR_NAME in results_dir.parts:
            continue
        for child in results_dir.iterdir():
            if not child.is_dir():
                continue
            if child.name == ARCHIVE_DIR_NAME:
                continue
            has_run = any(is_run_dir(p) for p in child.iterdir() if p.is_dir())
            has_old = (child / ARCHIVE_DIR_NAME).exists()
            if has_run or has_old:
                found.append(child)
    return sorted(found, key=lambda p: str(p))


def describe_context(perturbation_dir):
    """
    把路径拆成：对称结构 / 母结构 / 扰动名。
    典型路径：
        root\\C4对称结构\\四孔方块\\results\\单孔偏移扰动
    """
    try:
        rel = perturbation_dir.relative_to(STRUCT_ROOT)
        parts = rel.parts
    except ValueError:
        parts = perturbation_dir.parts
    if "results" in parts:
        idx = parts.index("results")
        symmetry = parts[0] if idx >= 2 else ""
        mother = parts[idx - 1] if idx >= 1 else ""
        perturbation = parts[idx + 1] if idx + 1 < len(parts) else perturbation_dir.name
        return symmetry, mother, perturbation
    return "", "", perturbation_dir.name


def build_record(index, perturbation_dir):
    run_dirs = [p for p in perturbation_dir.iterdir() if is_run_dir(p)]
    run_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    modes = OrderedDict((m, 0) for m in MODE_DIRS)
    for p in run_dirs:
        modes[detect_run_mode(p)] += 1
    symmetry, mother, perturbation = describe_context(perturbation_dir)
    latest = run_dirs[0] if run_dirs else None
    return {
        "index": index,
        "dir": perturbation_dir,
        "symmetry": symmetry,
        "mother": mother,
        "perturbation": perturbation,
        "runs": run_dirs,
        "latest": latest,
        "modes": modes,
    }


def scan_records():
    dirs = discover_perturbation_result_dirs(STRUCT_ROOT)
    return [build_record(i + 1, d) for i, d in enumerate(dirs)]


def print_records(records):
    safe_print("\n发现 results 扰动目录 {} 个。".format(len(records)))
    safe_print("说明：当前目录只统计 results\\扰动 下尚未归档的 run_*；旧文件里的历史结果不会算作当前结果。")
    safe_print("=" * 120)
    for r in records:
        latest = r["latest"]
        latest_text = "无当前 run_*"
        if latest is not None:
            latest_text = "{} | {} | {}".format(
                latest.name, detect_run_mode(latest), format_mtime(latest)
            )
        mode_text = "test:{} full:{} preview:{} unknown:{}".format(
            r["modes"]["test"], r["modes"]["full"], r["modes"]["preview"], r["modes"]["unknown"]
        )
        safe_print("[{:03d}] {} / {} / {}".format(r["index"], r["symmetry"], r["mother"], r["perturbation"]))
        safe_print("      当前 run 数：{}；类型统计：{}；最新：{}".format(len(r["runs"]), mode_text, latest_text))
        safe_print("      路径：{}".format(r["dir"]))
    safe_print("=" * 120)


def archive_run_dir(run_dir, perturbation_dir, reason="待考察", dry_run=False):
    old_root = perturbation_dir / ARCHIVE_DIR_NAME if dry_run else ensure_archive_tree(perturbation_dir)
    mode = detect_run_mode(run_dir)
    target_dir = old_root / mode / reason
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
    dst = unique_destination(target_dir / run_dir.name)
    if not dry_run:
        shutil.move(str(run_dir), str(dst))
    return dst


def normalize_one(record, keep_latest=KEEP_LATEST_ACTIVE_RUNS, delete_instead=False, dry_run=False):
    """
    整理单个扰动目录：
        - 创建旧文件目录树；
        - 清空无效；
        - 保留最新 keep_latest 个 run_*；
        - 其余 run_* 移到待考察，或按用户选择直接删除。
    """
    perturbation_dir = record["dir"]
    old_root = perturbation_dir / ARCHIVE_DIR_NAME if dry_run else ensure_archive_tree(perturbation_dir)
    deleted_invalid = clean_invalid_in(old_root, dry_run=dry_run) if AUTO_DELETE_INVALID else 0

    runs = [p for p in perturbation_dir.iterdir() if is_run_dir(p)]
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    keep_latest = max(0, int(keep_latest))
    keep = set(runs[:keep_latest])
    archive_or_delete = [p for p in runs if p not in keep]

    moved = []
    deleted = []
    for run_dir in archive_or_delete:
        if delete_instead:
            if not dry_run:
                shutil.rmtree(str(run_dir))
            deleted.append(run_dir.name)
        else:
            dst = archive_run_dir(run_dir, perturbation_dir, "待考察", dry_run=dry_run)
            moved.append((run_dir.name, dst))
    return {
        "deleted_invalid": deleted_invalid,
        "moved": moved,
        "deleted": deleted,
        "kept": [p.name for p in runs[:keep_latest]],
    }


def archive_all_current_runs(record, dry_run=False):
    perturbation_dir = record["dir"]
    old_root = perturbation_dir / ARCHIVE_DIR_NAME if dry_run else ensure_archive_tree(perturbation_dir)
    deleted_invalid = clean_invalid_in(old_root, dry_run=dry_run) if AUTO_DELETE_INVALID else 0
    runs = [p for p in perturbation_dir.iterdir() if is_run_dir(p)]
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    moved = []
    for run_dir in runs:
        dst = archive_run_dir(run_dir, perturbation_dir, "待考察", dry_run=dry_run)
        moved.append((run_dir.name, dst))
    return {"deleted_invalid": deleted_invalid, "moved": moved, "deleted": [], "kept": []}


def clean_all_invalid(records, dry_run=False):
    total = 0
    for r in records:
        old_root = r["dir"] / ARCHIVE_DIR_NAME if dry_run else ensure_archive_tree(r["dir"])
        total += clean_invalid_in(old_root, dry_run=dry_run)
    return total


def parse_indices(text, max_index):
    """
    支持输入：
        1,3,5-8
    """
    result = set()
    for part in text.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            if start > end:
                start, end = end, start
            for i in range(start, end + 1):
                if 1 <= i <= max_index:
                    result.add(i)
        else:
            i = int(part)
            if 1 <= i <= max_index:
                result.add(i)
    return sorted(result)


def print_action_result(record, result, dry_run=False):
    if dry_run:
        safe_print("  [DRY-RUN] 以上为计划操作，未移动/删除任何文件。")
    safe_print("\n[{:03d}] {} / {} / {}".format(
        record["index"], record["symmetry"], record["mother"], record["perturbation"]
    ))
    safe_print("  保留当前 run：{}".format("；".join(result["kept"]) if result["kept"] else "无"))
    safe_print("  移入待考察：{} 个".format(len(result["moved"])))
    for old_name, dst in result["moved"]:
        safe_print("    {} -> {}".format(old_name, dst))
    safe_print("  直接删除旧 run：{} 个".format(len(result["deleted"])))
    for name in result["deleted"]:
        safe_print("    {}".format(name))
    safe_print("  清空无效内容：{} 项".format(result["deleted_invalid"]))


def confirm_danger(prompt, word="YES"):
    answer = input("{} 输入 {} 确认：".format(prompt, word)).strip()
    return answer == word


def interactive_main(records):
    while True:
        print_records(records)
        safe_print("\n请选择操作：")
        safe_print("  1 = 只查看扫描结果，不移动、不删除")
        safe_print("  2 = 批量整理全部：每个扰动只保留最新 1 个 run，其余移动到 旧文件/type/待考察")
        safe_print("  3 = 选择编号整理：每个被选扰动只保留最新 1 个 run，其余移动到待考察")
        safe_print("  4 = 批量删除旧 run：每个扰动只保留最新 1 个 run，其余直接删除")
        safe_print("  5 = 只清空所有 旧文件/type/无效")
        safe_print("  6 = 把选中扰动的所有当前 run_* 全部移到待考察，不保留当前 run")
        safe_print("  0 = 退出")
        choice = input("请输入 0/1/2/3/4/5/6：").strip()

        if choice == "0":
            return
        if choice == "1":
            return
        if choice == "2":
            if not confirm_danger("将整理全部扰动目录。"):
                continue
            for r in records:
                result = normalize_one(r, keep_latest=KEEP_LATEST_ACTIVE_RUNS, delete_instead=False)
                print_action_result(r, result)
            records = scan_records()
            continue
        if choice == "3":
            text = input("请输入编号，例如 1,3,5-8；输入 0 返回：").strip()
            if text == "0":
                continue
            indices = parse_indices(text, len(records))
            for i in indices:
                r = records[i - 1]
                result = normalize_one(r, keep_latest=KEEP_LATEST_ACTIVE_RUNS, delete_instead=False)
                print_action_result(r, result)
            records = scan_records()
            continue
        if choice == "4":
            if not confirm_danger("危险操作：将直接删除所有扰动目录里的旧 run，只保留最新 1 个。", "DELETE"):
                continue
            for r in records:
                result = normalize_one(r, keep_latest=KEEP_LATEST_ACTIVE_RUNS, delete_instead=True)
                print_action_result(r, result)
            records = scan_records()
            continue
        if choice == "5":
            deleted = clean_all_invalid(records)
            safe_print("已清空所有“无效”内容，共删除 {} 项。".format(deleted))
            records = scan_records()
            continue
        if choice == "6":
            text = input("请输入编号，例如 1,3,5-8；输入 0 返回：").strip()
            if text == "0":
                continue
            indices = parse_indices(text, len(records))
            if not confirm_danger("将把选中扰动的所有当前 run_* 全部移入待考察。"):
                continue
            for i in indices:
                r = records[i - 1]
                result = archive_all_current_runs(r)
                print_action_result(r, result)
            records = scan_records()
            continue
        safe_print("输入无效，请重新选择。")


def main():
    parser = argparse.ArgumentParser(description="整理 FDTD results 旧结果。")
    parser.add_argument("--scan", action="store_true", help="只扫描并输出状态。")
    parser.add_argument("--normalize-all", action="store_true", help="整理全部：保留每个扰动最新 run，其余移到待考察。")
    parser.add_argument("--clean-invalid", action="store_true", help="只清空所有旧文件/type/无效。")
    parser.add_argument("--dry-run", action="store_true", help="只输出将要移动/删除的计划，不实际改动文件。")
    parser.add_argument("--keep-latest", type=int, default=KEEP_LATEST_ACTIVE_RUNS, help="每个扰动保留最新 N 个当前 run。")
    args = parser.parse_args()

    records = scan_records()

    if AUTO_DELETE_INVALID and not args.scan:
        deleted = clean_all_invalid(records, dry_run=args.dry_run)
        if deleted:
            safe_print("启动时已自动清空“无效”内容，共删除 {} 项。".format(deleted))

    if args.scan:
        print_records(records)
        return

    if args.clean_invalid:
        deleted = clean_all_invalid(records, dry_run=args.dry_run)
        if args.dry_run:
            safe_print("[DRY-RUN] 以下仅为计划，不会实际删除。")
        safe_print("已清空所有“无效”内容，共删除 {} 项。".format(deleted))
        return

    if args.normalize_all:
        for r in records:
            result = normalize_one(r, keep_latest=args.keep_latest, delete_instead=False, dry_run=args.dry_run)
            print_action_result(r, result, dry_run=args.dry_run)
        return

    interactive_main(records)


if __name__ == "__main__":
    main()
