# -*- coding: utf-8 -*-
"""
四裂缝环 FDTD 自动化扫描公共模块
================================

本模块供五个扰动脚本共用。它保证：
- fsp 文件夹内的源 .fsp 只读不写；
- 每轮先复制源 .fsp 到 results 下作为工作母版；
- 每个扫描点再从母版复制独立 work_*.fsp，之后只修改该副本；
- 每个点保存 .fsp、透射谱 abs^2 图片、Excel 源数据；
- 每个点结束后实时输出最大/最小 |T|^2 及对应波长；
- 结果目录包含模式标识：run_preview/run_test/run_full。
"""

import argparse
import csv
import hashlib
import importlib.util
import os
import shutil
import sys
import time
import warnings
import zipfile
from datetime import datetime
from math import cos, radians, sin
from pathlib import Path
from xml.sax.saxutils import escape

warnings.filterwarnings("ignore", category=UserWarning, module=r"numpy\._distributor_init")
warnings.filterwarnings("ignore", message=r".*deprecated.*", module=r"matplotlib.*")
warnings.filterwarnings("ignore", message=r".*loaded more than 1 DLL.*")
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:
    plt = None


SLIT_INDEX_LABELS = {
    1: "deg000_right",
    2: "deg090_top",
    3: "deg180_left",
    4: "deg270_bottom",
}


def nm(value_m):
    arr = np.asarray(value_m)
    if arr.shape == ():
        return float(arr) * 1e9
    return arr * 1e9


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def chinese_timestamp():
    now = datetime.now()
    return "{}年{}月{}日_{:02d}时{:02d}分{:02d}秒".format(now.year, now.month, now.day, now.hour, now.minute, now.second)


def safe_token(text):
    chars = []
    for ch in str(text):
        if ch.isalnum() or ch in ("_", "-", "."):
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars).strip("_") or "point"


def format_duration(seconds):
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return "{:.1f} s".format(seconds)
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    if minutes < 60:
        return "{} min {} s".format(minutes, sec)
    return "{} h {} min {} s".format(minutes // 60, minutes % 60, sec)


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_source_unchanged(source_fsp, expected_hash):
    if file_sha256(source_fsp) != expected_hash:
        raise RuntimeError("安全保护触发：源 FSP 文件发生变化，脚本已停止。请检查：{}".format(source_fsp))


def frange(start, stop, step, include_stop=True):
    if step <= 0:
        raise ValueError("扫描步长必须大于 0。")
    values = []
    value = float(start)
    guard = 0
    while value <= float(stop) + 1e-15:
        values.append(value)
        value += float(step)
        guard += 1
        if guard > 10000:
            raise RuntimeError("扫描点数超过 10000，请检查范围和步长。")
    if include_stop and values and abs(values[-1] - stop) > max(1e-15, abs(step) * 1e-6):
        values.append(float(stop))
    return values


def auto_step(start, stop, manual_step, auto_enabled, target_points, step_min, step_max):
    if not auto_enabled:
        if manual_step <= 0:
            raise ValueError("手动步长必须大于 0。")
        return manual_step
    span = abs(stop - start)
    if span <= 0:
        return manual_step if manual_step > 0 else step_min
    return clamp(span / float(max(1, int(target_points) - 1)), step_min, step_max)


def import_lumapi(lumerical_root):
    api_dir = Path(lumerical_root) / "api" / "python"
    bin_dir = Path(lumerical_root) / "bin"
    for path in (api_dir, bin_dir):
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(path))
        os.environ["PATH"] = str(path) + os.pathsep + os.environ.get("PATH", "")
    lumapi_file = api_dir / "lumapi.py"
    spec = importlib.util.spec_from_file_location("lumapi", str(lumapi_file))
    if spec is None or spec.loader is None:
        raise RuntimeError("无法导入 lumapi：{}".format(lumapi_file))
    lumapi = importlib.util.module_from_spec(spec)
    sys.modules["lumapi"] = lumapi
    spec.loader.exec_module(lumapi)
    return lumapi


def find_source_fsp(structure_root):
    files = sorted((Path(structure_root) / "fsp").glob("*.fsp"))
    if len(files) != 1:
        raise RuntimeError("期望找到 1 个 .fsp，实际找到 {} 个。".format(len(files)))
    return files[0]


def prepare_output_root(structure_root, perturbation_name, run_mode, resume=False, explicit_run_dir=None):
    root = Path(structure_root) / "results" / perturbation_name
    root.mkdir(parents=True, exist_ok=True)
    if explicit_run_dir:
        run_dir = Path(explicit_run_dir)
        if not run_dir.is_absolute():
            run_dir = root / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
    if resume:
        runs = sorted([p for p in root.glob("run_*") if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
        if not runs:
            raise RuntimeError("指定 --resume，但没有可继续的 run_* 目录。")
        return runs[0]
    run_dir = root / ("run_{}_{}".format(run_mode, chinese_timestamp()))
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def ensure_folders(run_dir):
    folders = {
        "plan": run_dir / "00_scan_plan",
        "fsp": run_dir / "01_fsp",
        "excel": run_dir / "02_transmission_excel",
        "png": run_dir / "03_transmission_abs2_png",
        "logs": run_dir / "04_logs",
        "work": run_dir / "05_work_fsp",
    }
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def ascii_work_root(run_dir):
    root = Path(r"H:\FDTD_CodeX\fdtd_ascii_work\four_slit_ring") / safe_token(run_dir.name)
    root.mkdir(parents=True, exist_ok=True)
    return root


def copy_master_templates(source_fsp, folders, run_dir):
    result_master = folders["work"] / "master_template.fsp"
    shutil.copy2(str(source_fsp), str(result_master))
    ascii_root = ascii_work_root(run_dir)
    ascii_master = ascii_root / "master_template.fsp"
    shutil.copy2(str(source_fsp), str(ascii_master))
    return result_master, ascii_master, ascii_root


def getnamed(fdtd, name, prop, index=None):
    return fdtd.getnamed(name, prop) if index is None else fdtd.getnamed(name, prop, int(index))


def setnamed(fdtd, name, prop, value, index=None):
    if index is None:
        fdtd.setnamed(name, prop, value)
    else:
        fdtd.setnamed(name, prop, value, int(index))


def read_geometry(fdtd, config):
    slit_name = config["slit_object_name"]
    slit_count = int(fdtd.getnamednumber(slit_name))
    slits = []
    for index in range(1, slit_count + 1):
        x = float(getnamed(fdtd, slit_name, "x", index))
        y = float(getnamed(fdtd, slit_name, "y", index))
        slits.append({
            "index": index,
            "label": SLIT_INDEX_LABELS.get(index, "slit{}".format(index)),
            "x": x,
            "y": y,
            "center_radius": (x * x + y * y) ** 0.5,
            "x_span": float(getnamed(fdtd, slit_name, "x span", index)),
            "y_span": float(getnamed(fdtd, slit_name, "y span", index)),
            "rotation": float(getnamed(fdtd, slit_name, "rotation 1", index)),
            "z_min": float(getnamed(fdtd, slit_name, "z min", index)),
            "z_max": float(getnamed(fdtd, slit_name, "z max", index)),
        })
    outer_name = config["outer_ring_object_name"]
    inner_name = config["inner_ring_object_name"]
    sub_name = config["substrate_object_name"]
    return {
        "outer_radius": float(getnamed(fdtd, outer_name, "radius")),
        "inner_radius": float(getnamed(fdtd, inner_name, "radius")),
        "ring_z_min": float(getnamed(fdtd, outer_name, "z min")),
        "ring_z_max": float(getnamed(fdtd, outer_name, "z max")),
        "substrate_x_span": float(getnamed(fdtd, sub_name, "x span")),
        "substrate_y_span": float(getnamed(fdtd, sub_name, "y span")),
        "substrate_z_min": float(getnamed(fdtd, sub_name, "z min")),
        "substrate_z_max": float(getnamed(fdtd, sub_name, "z max")),
        "base_slit_width": slits[0]["x_span"],
        "base_slit_length": slits[0]["y_span"],
        "base_slit_center_radius": slits[0]["center_radius"],
        "slits": slits,
    }


def slit_by_index(geom, index):
    for slit in geom["slits"]:
        if slit["index"] == index:
            return slit
    raise KeyError("找不到 air_slit 索引 {}".format(index))


def safe_width_limits(geom, config):
    lower = config["min_slit_width_m"]
    upper = min(config["max_slit_width_m"], geom["outer_radius"] - geom["inner_radius"] - config["radial_clearance_m"])
    return lower, max(lower, upper)


def safe_length_limits(geom, config):
    lower = config["min_slit_length_m"]
    upper = min(config["max_slit_length_m"], 2.0 * geom["outer_radius"])
    return lower, max(lower, upper)


def build_points(config, geom):
    kind = config["kind"]
    if kind in ("single_width", "opposite_pair_width", "all_width"):
        low, high = safe_width_limits(geom, config)
        start = max(low, config["width_start_m"])
        stop = min(high, config["width_stop_m"])
        step = auto_step(start, stop, config["width_step_m"], config["auto_step"], config["target_points"], config["step_min_m"], config["step_max_m"])
        return [{"index": i, "label": config["point_label"], "values": {"width": v}, "width_m": v} for i, v in enumerate(frange(start, stop, step, config["include_exact_stop"]))]
    if kind == "single_angle":
        step = auto_step(config["angle_start_deg"], config["angle_stop_deg"], config["angle_step_deg"], config["auto_step"], config["target_points"], config["angle_step_min_deg"], config["angle_step_max_deg"])
        return [{"index": i, "label": config["point_label"], "values": {"angle_deg": v}, "angle_delta_deg": v} for i, v in enumerate(frange(config["angle_start_deg"], config["angle_stop_deg"], step, config["include_exact_stop"]))]
    if kind == "single_length":
        low, high = safe_length_limits(geom, config)
        start = max(low, config["length_start_m"])
        stop = min(high, config["length_stop_m"])
        step = auto_step(start, stop, config["length_step_m"], config["auto_step"], config["target_points"], config["step_min_m"], config["step_max_m"])
        return [{"index": i, "label": config["point_label"], "values": {"length": v}, "length_m": v} for i, v in enumerate(frange(start, stop, step, config["include_exact_stop"]))]
    raise ValueError("未知扰动类型：{}".format(kind))


def apply_perturbation(fdtd, config, point, geom):
    name = config["slit_object_name"]
    kind = config["kind"]
    if kind == "single_width":
        setnamed(fdtd, name, "x span", point["width_m"], config["single_slit_index"])
    elif kind == "opposite_pair_width":
        for index in config["opposite_pair_indices"]:
            setnamed(fdtd, name, "x span", point["width_m"], index)
    elif kind == "all_width":
        for index in range(1, int(fdtd.getnamednumber(name)) + 1):
            setnamed(fdtd, name, "x span", point["width_m"], index)
    elif kind == "single_length":
        setnamed(fdtd, name, "y span", point["length_m"], config["single_slit_index"])
    elif kind == "single_angle":
        index = config["single_slit_index"]
        base = slit_by_index(geom, index)
        new_angle = base["rotation"] + point["angle_delta_deg"]
        r = base["center_radius"]
        setnamed(fdtd, name, "x", r * cos(radians(new_angle)), index)
        setnamed(fdtd, name, "y", r * sin(radians(new_angle)), index)
        setnamed(fdtd, name, "first axis", "z", index)
        setnamed(fdtd, name, "rotation 1", new_angle, index)
    else:
        raise ValueError("未知扰动类型：{}".format(kind))


def describe_point(config, point):
    if "width_m" in point:
        return "slit_width={:.3f} nm".format(nm(point["width_m"]))
    if "length_m" in point:
        return "slit_length={:.3f} nm".format(nm(point["length_m"]))
    if "angle_delta_deg" in point:
        return "angle_delta={:.3f} deg".format(point["angle_delta_deg"])
    return str(point)


def point_stem(config, point):
    return safe_token("{:04d}_{}_{}".format(point["index"], point["label"], describe_point(config, point)))


def read_transmission(fdtd, monitor_name):
    result = fdtd.getresult(monitor_name, "T")
    wavelength = np.ravel(result["lambda"])
    frequency = np.ravel(result.get("f", np.zeros_like(wavelength)))
    transmission = np.ravel(result["T"])
    order = np.argsort(wavelength)
    return wavelength[order], frequency[order], transmission[order]


def spectrum_summary(wavelength_m, transmission):
    abs2 = np.abs(transmission) ** 2
    imax = int(np.nanargmax(abs2))
    imin = int(np.nanargmin(abs2))
    return {
        "max_abs2": float(abs2[imax]),
        "max_wavelength_nm": float(nm(wavelength_m[imax])),
        "min_abs2": float(abs2[imin]),
        "min_wavelength_nm": float(nm(wavelength_m[imin])),
    }


def xlsx_cell(value):
    if value is None:
        return "<c/>"
    if isinstance(value, (int, float, np.integer, np.floating)):
        return "<c><v>{}</v></c>".format(float(value))
    return '<c t="inlineStr"><is><t>{}</t></is></c>'.format(escape(str(value)))


def xlsx_sheet_xml(rows):
    out = []
    for ridx, row in enumerate(rows, start=1):
        out.append('<row r="{}">{}</row>'.format(ridx, "".join(xlsx_cell(v) for v in row)))
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{}</sheetData></worksheet>'.format("".join(out))


def save_xlsx(xlsx_path, sheets):
    workbook_sheets, relationships, overrides = [], [], []
    for idx, sheet in enumerate(sheets, start=1):
        workbook_sheets.append('<sheet name="{}" sheetId="{}" r:id="rId{}"/>'.format(escape(sheet[0]), idx, idx))
        relationships.append('<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{}.xml"/>'.format(idx, idx))
        overrides.append('<Override PartName="/xl/worksheets/sheet{}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.format(idx))
    workbook_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{}</sheets></workbook>'.format("".join(workbook_sheets))
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{}</Relationships>'.format("".join(relationships))
    root_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>{}</Types>'.format("".join(overrides))
    with zipfile.ZipFile(str(xlsx_path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        for idx, sheet in enumerate(sheets, start=1):
            zf.writestr("xl/worksheets/sheet{}.xml".format(idx), xlsx_sheet_xml(sheet[1]))


def save_transmission_excel(xlsx_path, config, point, geom, wavelength_m, frequency_hz, transmission, summary):
    abs2 = np.abs(transmission) ** 2
    rows = [["wavelength_m", "wavelength_nm", "frequency_Hz", "T_real", "T_imag", "T_abs2"]]
    for wl, fr, val, a2 in zip(wavelength_m, frequency_hz, transmission, abs2):
        rows.append([float(wl), float(nm(wl)), float(fr), float(np.real(val)), float(np.imag(val)), float(a2)])
    meta = [
        ["item", "value"],
        ["perturbation", config["perturbation_name"]],
        ["group_path", config["group_path"]],
        ["point", describe_point(config, point)],
        ["outer_radius_nm", nm(geom["outer_radius"])],
        ["inner_radius_nm", nm(geom["inner_radius"])],
        ["ring_thickness_nm", nm(geom["ring_z_max"] - geom["ring_z_min"])],
        ["base_slit_width_nm", nm(geom["base_slit_width"])],
        ["base_slit_length_nm", nm(geom["base_slit_length"])],
        ["base_slit_center_radius_nm", nm(geom["base_slit_center_radius"])],
        ["max_abs2", summary["max_abs2"]],
        ["max_wavelength_nm", summary["max_wavelength_nm"]],
        ["min_abs2", summary["min_abs2"]],
        ["min_wavelength_nm", summary["min_wavelength_nm"]],
    ]
    save_xlsx(xlsx_path, [("transmission_abs2", rows), ("metadata", meta)])


def save_abs2_plot(png_path, config, point, wavelength_m, transmission):
    abs2 = np.abs(transmission) ** 2
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(8.0, 5.0), dpi=160)
    ax.plot(nm(wavelength_m), abs2, color="#1f77b4", linewidth=1.8)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("|T|^2")
    ax.set_title("{}: {}".format(config["perturbation_name"], describe_point(config, point)))
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(str(png_path))
    plt.close(fig)


def write_scan_plan(plan_dir, config, points, geom):
    csv_path = plan_dir / "scan_points.csv"
    keys = sorted(points[0]["values"].keys()) if points else []
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "label"] + [k for k in keys] + ["description"])
        for point in points:
            writer.writerow([point["index"], point["label"]] + [point["values"][k] for k in keys] + [describe_point(config, point)])
    summary = [
        "四裂缝环 {} 自动扫描配置摘要".format(config["perturbation_name"]),
        "外环半径: {:.3f} nm".format(nm(geom["outer_radius"])),
        "内环半径: {:.3f} nm".format(nm(geom["inner_radius"])),
        "环厚度: {:.3f} nm".format(nm(geom["ring_z_max"] - geom["ring_z_min"])),
        "裂缝宽度/长度: {:.3f} / {:.3f} nm".format(nm(geom["base_slit_width"]), nm(geom["base_slit_length"])),
        "裂缝中心半径: {:.3f} nm".format(nm(geom["base_slit_center_radius"])),
        "降群路径: {}".format(config["group_path"]),
        "计划点数: {}".format(len(points)),
    ]
    (plan_dir / "scan_summary.txt").write_text("\n".join(summary), encoding="utf-8-sig")
    return csv_path


def write_structure_overview(run_dir, source_fsp, config, points, geom, result_master, ascii_root):
    doc = run_dir / "结构状态说明.md"
    lines = [
        "# 四裂缝环 {} 结构状态说明".format(config["perturbation_name"]),
        "",
        "## 母结构参数",
        "- 母版 FSP：`{}`".format(source_fsp),
        "- 外环对象：`{}`，半径 {:.6f} nm".format(config["outer_ring_object_name"], nm(geom["outer_radius"])),
        "- 内孔对象：`{}`，半径 {:.6f} nm".format(config["inner_ring_object_name"], nm(geom["inner_radius"])),
        "- 裂缝对象：`{}`，共 4 条，同名对象按索引 1-4 区分".format(config["slit_object_name"]),
        "- 裂缝宽度 x span：{:.6f} nm".format(nm(geom["base_slit_width"])),
        "- 裂缝长度 y span：{:.6f} nm".format(nm(geom["base_slit_length"])),
        "- 裂缝中心半径：{:.6f} nm".format(nm(geom["base_slit_center_radius"])),
        "- Si 厚度：{:.6f} nm".format(nm(geom["ring_z_max"] - geom["ring_z_min"])),
        "- 衬底尺寸：{:.6f} nm x {:.6f} nm".format(nm(geom["substrate_x_span"]), nm(geom["substrate_y_span"])),
        "- 衬底厚度：{:.6f} nm".format(nm(geom["substrate_z_max"] - geom["substrate_z_min"])),
        "",
        "## 本批次扰动",
        "- 扰动名称：{}".format(config["perturbation_name"]),
        "- 改变参数：{}".format(config["changed_parameter"]),
        "- 降群路径：{}".format(config["group_path"]),
        "- 预期影响：{}".format(config["expected_effect"]),
        "- 起点：{}".format(describe_point(config, points[0]) if points else "无"),
        "- 终点：{}".format(describe_point(config, points[-1]) if points else "无"),
        "- 计划点数：{}".format(len(points)),
        "",
        "## 路径说明",
        "- results 工作母版：`{}`".format(result_master),
        "- Lumerical 英文镜像目录：`{}`".format(ascii_root),
        "- 源 .fsp 只读不写，运行前后会检查 SHA256 指纹。",
    ]
    doc.write_text("\n".join(lines), encoding="utf-8-sig")
    return doc


def write_manifest_header(path):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow(["index", "description", "fsp", "xlsx", "png", "max_abs2", "max_wavelength_nm", "min_abs2", "min_wavelength_nm", "elapsed_s", "status"])


def append_manifest(path, point, description, paths, summary, elapsed, status):
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow([point["index"], description, paths["fsp"], paths["xlsx"], paths["png"], summary.get("max_abs2"), summary.get("max_wavelength_nm"), summary.get("min_abs2"), summary.get("min_wavelength_nm"), "{:.3f}".format(elapsed), status])


def parse_args(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--preview", action="store_true", help="只生成扫描计划，不仿真。")
    parser.add_argument("--test-run", action="store_true", help="只真实仿真 TEST_POINT_COUNT 个点。")
    parser.add_argument("--full-run", action="store_true", help="完整真实仿真。")
    parser.add_argument("--resume", action="store_true", help="继续最近一个 run_* 批次。")
    parser.add_argument("--run-dir", default=None, help="指定输出批次目录。")
    parser.add_argument("--max-points", type=int, default=None, help="最多运行/预览前 N 个点。")
    parser.add_argument("--show-gui", action="store_true", help="显示 FDTD GUI。")
    return parser.parse_args()


def apply_run_mode(args, config):
    args.prompted_mode = False
    explicit = args.preview or args.test_run or args.full_run or args.resume or args.max_points is not None or args.run_dir is not None
    mode = config["run_mode"].strip().lower()
    if args.preview:
        mode = "preview"
    elif args.test_run:
        mode = "test"
    elif args.full_run:
        mode = "full"
    elif not explicit and mode == "ask":
        args.prompted_mode = True
        print("")
        print("请选择四裂缝环 {} 脚本运行模式：".format(config["perturbation_name"]))
        print("  1 = 测试模式：真实仿真前 {} 个点".format(config["test_point_count"]))
        print("  2 = 完整真实仿真")
        print("  3 = 预览模式：只生成扫描计划，不仿真")
        choice = input("请输入 1/2/3 后按回车：").strip()
        if choice == "1":
            mode = "test"
        elif choice == "2":
            mode = "full"
        elif choice == "3":
            mode = "preview"
        else:
            raise RuntimeError("无效输入：{}".format(choice))
    if mode not in ("test", "full", "preview"):
        raise RuntimeError('RUN_MODE 只能是 "ask"、"test"、"full" 或 "preview"。')
    args.preview = (mode == "preview")
    return mode


def maybe_ask_fdtd_runtime_overrides(config):
    print("")
    print("当前 FDTD 参数：simulation time = {} fs；auto shutoff min = {}；mesh accuracy = {}；dt stability factor = {}".format(
        config.get("simulation_time_fs", float(config.get("simulation_time_s", 0.0)) * 1e15),
        config.get("auto_shutoff_min"),
        config.get("mesh_accuracy"),
        config.get("dt_stability_factor"),
    ))
    if input("是否修改本次 FDTD 参数？y/N：").strip().lower() != "y":
        return
    prompts = (
        ("simulation_time_fs", "simulation time (fs)"),
        ("auto_shutoff_min", "auto shutoff min"),
        ("mesh_accuracy", "mesh accuracy"),
        ("dt_stability_factor", "dt stability factor"),
    )
    for key, label in prompts:
        current = config.get(key, float(config.get("simulation_time_s", 0.0)) * 1e15 if key == "simulation_time_fs" else "")
        raw = input("{}，空白表示不改，当前 {}：".format(label, current)).strip()
        if not raw:
            continue
        value = float(raw)
        if value <= 0:
            print("{} 必须大于 0，已忽略。".format(label))
            continue
        config[key] = int(value) if key == "mesh_accuracy" else value
    if config.get("simulation_time_fs") is not None:
        config["simulation_time_s"] = float(config["simulation_time_fs"]) * 1e-15


def run(config):
    script_dir = Path(config["script_file"]).resolve().parent
    structure_root = script_dir.parent.parent
    args = parse_args("四裂缝环 {} FDTD 自动化扫描".format(config["perturbation_name"]))
    mode = apply_run_mode(args, config)
    if mode in ("test", "full") and getattr(args, "prompted_mode", False):
        maybe_ask_fdtd_runtime_overrides(config)

    source_fsp = find_source_fsp(structure_root)
    source_hash = file_sha256(source_fsp)
    run_dir = prepare_output_root(structure_root, config["perturbation_name"], mode, args.resume, args.run_dir)
    folders = ensure_folders(run_dir)
    result_master, ascii_master, ascii_root = copy_master_templates(source_fsp, folders, run_dir)
    manifest_path = folders["logs"] / "manifest.csv"
    log_path = folders["logs"] / "automation_run.log"

    lumapi = import_lumapi(config["lumerical_root"])
    fdtd = lumapi.FDTD(hide=True)
    try:
        fdtd.load(str(ascii_master))
        geom = read_geometry(fdtd, config)
    finally:
        try:
            fdtd.close()
        except Exception:
            pass

    points = build_points(config, geom)
    if args.max_points is not None:
        points = points[:max(0, args.max_points)]
    if mode == "test":
        points = points[:config["test_point_count"]]

    plan_csv = write_scan_plan(folders["plan"], config, points, geom)
    overview_doc = write_structure_overview(run_dir, source_fsp, config, points, geom, result_master, ascii_root)

    print("源 FSP: {}".format(source_fsp))
    print("results 工作母版 FSP: {}".format(result_master))
    print("Lumerical 英文镜像母版 FSP: {}".format(ascii_master))
    print("输出批次目录: {}".format(run_dir))
    print("外环/内孔半径: {:.3f} / {:.3f} nm".format(nm(geom["outer_radius"]), nm(geom["inner_radius"])))
    print("裂缝宽度/长度: {:.3f} / {:.3f} nm".format(nm(geom["base_slit_width"]), nm(geom["base_slit_length"])))
    print("裂缝中心半径: {:.3f} nm；Si 厚度: {:.3f} nm".format(nm(geom["base_slit_center_radius"]), nm(geom["ring_z_max"] - geom["ring_z_min"])))
    print("扰动: {}；降群路径: {}".format(config["perturbation_name"], config["group_path"]))
    print("计划仿真点数: {}".format(len(points)))
    print("扫描计划已保存: {}".format(plan_csv))
    print("结构说明已保存: {}".format(overview_doc))

    if args.preview:
        print("当前为 preview 模式：只生成计划，不运行 FDTD。扫描点如下：")
        for point in points:
            print("  #{:04d}: {}".format(point["index"], describe_point(config, point)))
        assert_source_unchanged(source_fsp, source_hash)
        return

    if not args.resume or not manifest_path.exists():
        write_manifest_header(manifest_path)

    run_started = time.time()
    with log_path.open("a", encoding="utf-8-sig") as log:
        log.write("\n==== Run started at {} ====\n".format(datetime.now().isoformat(timespec="seconds")))
        for ordinal, point in enumerate(points, start=1):
            stem = point_stem(config, point)
            paths = {
                "fsp": folders["fsp"] / (stem + ".fsp"),
                "xlsx": folders["excel"] / (stem + ".xlsx"),
                "png": folders["png"] / (stem + ".png"),
            }
            description = describe_point(config, point)
            if args.resume and paths["fsp"].exists() and paths["xlsx"].exists() and paths["png"].exists():
                print("[{}/{}] 已存在，跳过：{}".format(ordinal, len(points), stem))
                continue
            print("[{}/{}] 开始仿真：{}".format(ordinal, len(points), stem))
            print("    当前参数: {}；剩余组数(含当前): {}/{}".format(description, len(points) - ordinal + 1, len(points)))
            start = time.time()
            try:
                work_fsp = ascii_root / ("work_{}.fsp".format(stem))
                shutil.copy2(str(ascii_master), str(work_fsp))
                with lumapi.FDTD(hide=not args.show_gui) as fdtd:
                    fdtd.load(str(work_fsp))
                    fdtd.switchtolayout()
                    fdtd.setnamed(config["fdtd_object_name"], "simulation time", config["simulation_time_s"])
                    fdtd.setnamed(config["fdtd_object_name"], "auto shutoff min", config["auto_shutoff_min"])
                    if config.get("mesh_accuracy") is not None:
                        fdtd.setnamed(config["fdtd_object_name"], "mesh accuracy", int(float(config["mesh_accuracy"])))
                    if config.get("dt_stability_factor") is not None:
                        fdtd.setnamed(config["fdtd_object_name"], "dt stability factor", float(config["dt_stability_factor"]))
                    apply_perturbation(fdtd, config, point, geom)
                    fdtd.save(str(work_fsp))
                    fdtd.run()
                    wavelength_m, frequency_hz, transmission = read_transmission(fdtd, config["transmission_monitor_name"])
                    fdtd.save(str(work_fsp))
                summary = spectrum_summary(wavelength_m, transmission)
                shutil.copy2(str(work_fsp), str(paths["fsp"]))
                save_transmission_excel(paths["xlsx"], config, point, geom, wavelength_m, frequency_hz, transmission, summary)
                save_abs2_plot(paths["png"], config, point, wavelength_m, transmission)
                elapsed = time.time() - start
                append_manifest(manifest_path, point, description, paths, summary, elapsed, "ok")
                remain = max(0, len(points) - ordinal)
                avg = (time.time() - run_started) / float(max(1, ordinal))
                msg = (
                    "    完成并保存，用时 {}；max |T|^2={:.6g} @ {:.3f} nm；"
                    "min |T|^2={:.6g} @ {:.3f} nm；还剩 {} 组；预计还需要 {}"
                ).format(
                    format_duration(elapsed),
                    summary["max_abs2"],
                    summary["max_wavelength_nm"],
                    summary["min_abs2"],
                    summary["min_wavelength_nm"],
                    remain,
                    format_duration(avg * remain),
                )
                print(msg)
                log.write(msg + "\n")
            except Exception as exc:
                elapsed = time.time() - start
                append_manifest(manifest_path, point, description, paths, {}, elapsed, "failed: {}".format(exc))
                log.write("失败：{}\n".format(exc))
                raise
    assert_source_unchanged(source_fsp, source_hash)
    print("全部完成。结果目录: {}".format(run_dir))
