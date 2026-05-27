# -*- coding: utf-8 -*-
"""
四孔方块 FDTD 自动化扫描公共模块
================================

五个扰动脚本共享本文件。每个子脚本只保留“用户主要修改区”，本文件统一负责：
- 自动寻找 fsp/*.fsp 母版；
- 读取 .fsp 中的真实几何参数；
- 每个扫描点从母版复制独立工作副本；
- 修改孔半径/孔位置并运行 FDTD；
- 保存本点 .fsp、透射谱 abs^2 图片、Excel 原始数据；
- 结果统一放入 results/扰动名/run_模式_时间戳/；
- 实时输出当前参数、剩余组数、单次仿真时间和预计剩余时间。

注意：Lumerical 对中文路径加载 .fsp 有时会失败。因此脚本会把工作副本镜像到
H:/FDTD_CodeX/fdtd_ascii_work/four_hole_square/ 下运行；最终结果仍保存回本结构的
results 目录。
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
from pathlib import Path
from xml.sax.saxutils import escape

warnings.filterwarnings("ignore", category=UserWarning, module=r"numpy\._distributor_init")
warnings.filterwarnings("ignore", message=r".*deprecated.*", module=r"matplotlib.*")
warnings.filterwarnings("ignore", message=r".*loaded more than 1 DLL.*")
import numpy as np

C4_ROOT = Path(__file__).resolve().parents[3]
if str(C4_ROOT) not in sys.path:
    sys.path.insert(0, str(C4_ROOT))
from c4_runtime_common import chinese_timestamp, format_duration, print_runtime_progress


try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:
    plt = None


NM = 1e-9

HOLE_INDEX_LABELS = {
    1: "left_bottom",   # 左下 (-x, -y)
    2: "right_bottom",  # 右下 (+x, -y)
    3: "left_top",      # 左上 (-x, +y)
    4: "right_top",     # 右上 (+x, +y)
}


def nm(value_m):
    """把米转换为纳米；同时支持单个数值和 numpy 数组。"""
    arr = np.asarray(value_m)
    if arr.shape == ():
        return float(arr) * 1e9
    return arr * 1e9


def clamp(value, lower, upper):
    return max(lower, min(upper, value))



def safe_token(text):
    chars = []
    for ch in str(text):
        if ch.isalnum() or ch in ("_", "-", "."):
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars).strip("_") or "point"



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
            raise RuntimeError("扫描点数超过 10000，请检查起止值和步长。")
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
    if not lumapi_file.exists():
        raise FileNotFoundError("找不到 lumapi.py：{}".format(lumapi_file))
    spec = importlib.util.spec_from_file_location("lumapi", str(lumapi_file))
    if spec is None or spec.loader is None:
        raise RuntimeError("无法导入 lumapi：{}".format(lumapi_file))
    lumapi = importlib.util.module_from_spec(spec)
    sys.modules["lumapi"] = lumapi
    spec.loader.exec_module(lumapi)
    return lumapi


def find_source_fsp(structure_root):
    fsp_dir = Path(structure_root) / "fsp"
    files = sorted(fsp_dir.glob("*.fsp"))
    if len(files) != 1:
        raise RuntimeError("期望在 {} 中找到 1 个 .fsp，实际找到 {} 个。".format(fsp_dir, len(files)))
    return files[0]


def file_sha256(path):
    """计算文件指纹，用于确认源 .fsp 在自动化过程中没有被改动。"""
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_source_unchanged(source_fsp, expected_hash):
    """源文件保护：如果 fsp 文件夹内的母版被改动，立即停止并报错。"""
    current_hash = file_sha256(source_fsp)
    if current_hash != expected_hash:
        raise RuntimeError(
            "安全保护触发：源 FSP 文件发生了变化，脚本已停止。请检查：{}".format(source_fsp)
        )


def prepare_output_root(structure_root, perturbation_name, run_mode, resume=False, explicit_run_dir=None):
    result_root = Path(structure_root) / "results" / perturbation_name
    result_root.mkdir(parents=True, exist_ok=True)
    if explicit_run_dir:
        run_dir = Path(explicit_run_dir)
        if not run_dir.is_absolute():
            run_dir = result_root / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
    if resume:
        candidates = sorted(
            [p for p in result_root.glob("run_*") if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise RuntimeError("指定了 --resume，但 {} 中没有可继续的 run_* 批次。".format(result_root))
        return candidates[0]
    run_dir = result_root / ("run_{}_{}".format(run_mode, chinese_timestamp()))
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
    for path in folders.values():
        path.mkdir(parents=True, exist_ok=True)
    return folders


def ascii_work_root(run_dir):
    root = Path(r"H:\FDTD_CodeX\fdtd_ascii_work\four_hole_square") / safe_token(run_dir.name)
    root.mkdir(parents=True, exist_ok=True)
    return root


def copy_master_templates(source_fsp, folders, run_dir):
    result_master = folders["work"] / "master_template.fsp"
    shutil.copy2(str(source_fsp), str(result_master))
    ascii_root = ascii_work_root(run_dir)
    ascii_master = ascii_root / "master_template.fsp"
    shutil.copy2(str(source_fsp), str(ascii_master))
    return result_master, ascii_master, ascii_root


def getnamed_value(fdtd, name, prop, index=None):
    if index is None:
        return fdtd.getnamed(name, prop)
    return fdtd.getnamed(name, prop, int(index))


def setnamed_value(fdtd, name, prop, value, index=None):
    if index is None:
        fdtd.setnamed(name, prop, value)
    else:
        fdtd.setnamed(name, prop, value, int(index))


def read_geometry(fdtd, config):
    hole_name = config["hole_object_name"]
    host_name = config["host_object_name"]
    substrate_name = config["substrate_object_name"]
    hole_count = int(fdtd.getnamednumber(hole_name))
    holes = []
    for index in range(1, hole_count + 1):
        holes.append({
            "index": index,
            "label": HOLE_INDEX_LABELS.get(index, "hole{}".format(index)),
            "x": float(getnamed_value(fdtd, hole_name, "x", index)),
            "y": float(getnamed_value(fdtd, hole_name, "y", index)),
            "radius": float(getnamed_value(fdtd, hole_name, "radius", index)),
            "z_min": float(getnamed_value(fdtd, hole_name, "z min", index)),
            "z_max": float(getnamed_value(fdtd, hole_name, "z max", index)),
        })
    geom = {
        "host_x_span": float(getnamed_value(fdtd, host_name, "x span")),
        "host_y_span": float(getnamed_value(fdtd, host_name, "y span")),
        "host_z_min": float(getnamed_value(fdtd, host_name, "z min")),
        "host_z_max": float(getnamed_value(fdtd, host_name, "z max")),
        "substrate_x_span": float(getnamed_value(fdtd, substrate_name, "x span")),
        "substrate_y_span": float(getnamed_value(fdtd, substrate_name, "y span")),
        "substrate_z_min": float(getnamed_value(fdtd, substrate_name, "z min")),
        "substrate_z_max": float(getnamed_value(fdtd, substrate_name, "z max")),
        "holes": holes,
    }
    geom["base_radius"] = holes[0]["radius"]
    geom["base_half_pitch"] = max(abs(h["x"]) for h in holes)
    return geom


def hole_by_index(geom, index):
    for hole in geom["holes"]:
        if hole["index"] == index:
            return hole
    raise KeyError("找不到 air_hole 索引 {}".format(index))


def safe_radius_limits(geom, config):
    base_a = geom["base_half_pitch"]
    host_half = min(geom["host_x_span"], geom["host_y_span"]) / 2.0
    clearance = config["edge_clearance_m"]
    max_by_edge = host_half - base_a - clearance
    max_by_neighbor = base_a - clearance
    lower = config["min_hole_radius_m"]
    upper = min(config["max_hole_radius_m"], max_by_edge, max_by_neighbor)
    return lower, max(lower, upper)


def safe_offset_stop(geom, config):
    target = hole_by_index(geom, config.get("offset_hole_index", 4))
    host_half = min(geom["host_x_span"], geom["host_y_span"]) / 2.0
    radius = target["radius"]
    clearance = config["edge_clearance_m"]
    dx, dy = config.get("offset_direction", (1.0, 0.0))
    norm = (dx * dx + dy * dy) ** 0.5 or 1.0
    dx, dy = dx / norm, dy / norm
    limits = []
    if dx > 0:
        limits.append((host_half - clearance - radius - target["x"]) / dx)
    elif dx < 0:
        limits.append((-host_half + clearance + radius - target["x"]) / dx)
    if dy > 0:
        limits.append((host_half - clearance - radius - target["y"]) / dy)
    elif dy < 0:
        limits.append((-host_half + clearance + radius - target["y"]) / dy)
    allowed = min([v for v in limits if v >= 0] or [0.0])
    return max(0.0, min(config["offset_stop_m"], allowed))


def safe_pitch_limits(geom, config):
    host_half = min(geom["host_x_span"], geom["host_y_span"]) / 2.0
    radius = geom["base_radius"]
    clearance = config["edge_clearance_m"]
    lower = max(config["pitch_start_m"], radius + clearance)
    upper = min(config["pitch_stop_m"], host_half - radius - clearance)
    if lower > upper:
        raise ValueError("孔距扫描范围无效：{:.3f} nm > {:.3f} nm".format(nm(lower), nm(upper)))
    return lower, upper


def build_points(config, geom):
    kind = config["kind"]
    points = []
    if kind in ("single_radius", "diagonal_pair_radius", "all_radius"):
        low, high = safe_radius_limits(geom, config)
        start = max(low, config["radius_start_m"])
        stop = min(high, config["radius_stop_m"])
        step = auto_step(start, stop, config["radius_step_m"], config["auto_step"], config["target_points"], config["step_min_m"], config["step_max_m"])
        values = frange(start, stop, step, config["include_exact_stop"])
        for index, radius in enumerate(values):
            points.append({"index": index, "label": config["point_label"], "values": {"radius": radius}, "radius_m": radius})
    elif kind == "single_offset":
        start = config["offset_start_m"]
        stop = safe_offset_stop(geom, config)
        step = auto_step(start, stop, config["offset_step_m"], config["auto_step"], config["target_points"], config["step_min_m"], config["step_max_m"])
        values = frange(start, stop, step, config["include_exact_stop"])
        for index, offset in enumerate(values):
            points.append({"index": index, "label": config["point_label"], "values": {"offset": offset}, "offset_m": offset})
    elif kind == "pitch_scan":
        start, stop = safe_pitch_limits(geom, config)
        step = auto_step(start, stop, config["pitch_step_m"], config["auto_step"], config["target_points"], config["step_min_m"], config["step_max_m"])
        values = frange(start, stop, step, config["include_exact_stop"])
        for index, half_pitch in enumerate(values):
            points.append({"index": index, "label": config["point_label"], "values": {"half_pitch": half_pitch}, "half_pitch_m": half_pitch})
    else:
        raise ValueError("未知扰动类型：{}".format(kind))
    return points


def apply_perturbation(fdtd, config, point, geom):
    name = config["hole_object_name"]
    kind = config["kind"]
    if kind == "single_radius":
        setnamed_value(fdtd, name, "radius", point["radius_m"], config["single_hole_index"])
    elif kind == "diagonal_pair_radius":
        for index in config["diagonal_pair_indices"]:
            setnamed_value(fdtd, name, "radius", point["radius_m"], index)
    elif kind == "all_radius":
        for index in range(1, int(fdtd.getnamednumber(name)) + 1):
            setnamed_value(fdtd, name, "radius", point["radius_m"], index)
    elif kind == "single_offset":
        index = config["offset_hole_index"]
        hole = hole_by_index(geom, index)
        dx, dy = config.get("offset_direction", (1.0, 0.0))
        norm = (dx * dx + dy * dy) ** 0.5 or 1.0
        distance = point["offset_m"]
        setnamed_value(fdtd, name, "x", hole["x"] + distance * dx / norm, index)
        setnamed_value(fdtd, name, "y", hole["y"] + distance * dy / norm, index)
    elif kind == "pitch_scan":
        a = point["half_pitch_m"]
        positions = {1: (-a, -a), 2: (a, -a), 3: (-a, a), 4: (a, a)}
        for index, xy in positions.items():
            setnamed_value(fdtd, name, "x", xy[0], index)
            setnamed_value(fdtd, name, "y", xy[1], index)
    else:
        raise ValueError("未知扰动类型：{}".format(kind))


def describe_point(config, point):
    if config["kind"] in ("single_radius", "diagonal_pair_radius", "all_radius"):
        return "radius={:.3f} nm".format(nm(point["radius_m"]))
    if config["kind"] == "single_offset":
        return "offset={:.3f} nm".format(nm(point["offset_m"]))
    if config["kind"] == "pitch_scan":
        return "half_pitch={:.3f} nm, spacing={:.3f} nm".format(nm(point["half_pitch_m"]), nm(2 * point["half_pitch_m"]))
    return str(point)


def point_stem(config, point):
    return safe_token("{:04d}_{}_{}".format(point["index"], point["label"], describe_point(config, point)))


def point_paths(folders, config, point):
    stem = point_stem(config, point)
    return {
        "stem": stem,
        "fsp": folders["fsp"] / (stem + ".fsp"),
        "xlsx": folders["excel"] / (stem + ".xlsx"),
        "png": folders["png"] / (stem + ".png"),
    }


def read_transmission(fdtd, monitor_name):
    result = fdtd.getresult(monitor_name, "T")
    wavelength = np.ravel(result["lambda"])
    frequency = np.ravel(result.get("f", np.zeros_like(wavelength)))
    transmission = np.ravel(result["T"])
    order = np.argsort(wavelength)
    return wavelength[order], frequency[order], transmission[order]


def xlsx_cell(value):
    if value is None:
        return "<c/>"
    if isinstance(value, (int, float, np.integer, np.floating)):
        return "<c><v>{}</v></c>".format(float(value))
    return '<c t="inlineStr"><is><t>{}</t></is></c>'.format(escape(str(value)))


def xlsx_sheet_xml(rows):
    sheet_rows = []
    for ridx, row in enumerate(rows, start=1):
        cells = "".join(xlsx_cell(v) for v in row)
        sheet_rows.append('<row r="{}">{}</row>'.format(ridx, cells))
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{}</sheetData></worksheet>'.format("".join(sheet_rows))


def save_xlsx(xlsx_path, sheets):
    workbook_sheets, relationships, content_overrides = [], [], []
    for idx, sheet in enumerate(sheets, start=1):
        name = escape(sheet[0])
        workbook_sheets.append('<sheet name="{}" sheetId="{}" r:id="rId{}"/>'.format(name, idx, idx))
        relationships.append('<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{}.xml"/>'.format(idx, idx))
        content_overrides.append('<Override PartName="/xl/worksheets/sheet{}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.format(idx))
    workbook_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{}</sheets></workbook>'.format("".join(workbook_sheets))
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{}</Relationships>'.format("".join(relationships))
    root_rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    content_types_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>{}</Types>'.format("".join(content_overrides))
    with zipfile.ZipFile(str(xlsx_path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        for idx, sheet in enumerate(sheets, start=1):
            zf.writestr("xl/worksheets/sheet{}.xml".format(idx), xlsx_sheet_xml(sheet[1]))


def save_transmission_excel(xlsx_path, config, point, geom, wavelength_m, frequency_hz, transmission):
    t_abs2 = np.abs(transmission) ** 2
    data_rows = [["wavelength_m", "wavelength_nm", "frequency_Hz", "T_real", "T_imag", "T_abs2"]]
    for wl, fr, t, abs2 in zip(wavelength_m, frequency_hz, transmission, t_abs2):
        data_rows.append([float(wl), float(nm(wl)), float(fr), float(np.real(t)), float(np.imag(t)), float(abs2)])
    meta_rows = [
        ["item", "value"],
        ["perturbation", config["perturbation_name"]],
        ["kind", config["kind"]],
        ["changed_parameter", config["changed_parameter"]],
        ["group_path", config["group_path"]],
        ["point", describe_point(config, point)],
        ["host_x_span_nm", nm(geom["host_x_span"])],
        ["host_y_span_nm", nm(geom["host_y_span"])],
        ["si_thickness_nm", nm(geom["host_z_max"] - geom["host_z_min"])],
        ["base_hole_radius_nm", nm(geom["base_radius"])],
        ["base_half_pitch_nm", nm(geom["base_half_pitch"])],
        ["substrate_x_span_nm", nm(geom["substrate_x_span"])],
        ["substrate_y_span_nm", nm(geom["substrate_y_span"])],
        ["substrate_thickness_nm", nm(geom["substrate_z_max"] - geom["substrate_z_min"])],
    ]
    save_xlsx(xlsx_path, [("transmission_abs2", data_rows), ("metadata", meta_rows)])


def save_abs2_plot(png_path, config, point, wavelength_m, transmission):
    t_abs2 = np.abs(transmission) ** 2
    if plt is None:
        with png_path.with_suffix(".plot_fallback.csv").open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["wavelength_nm", "T_abs2"])
            for wl, value in zip(wavelength_m, t_abs2):
                writer.writerow([nm(wl), float(value)])
        return
    fig, ax = plt.subplots(figsize=(8.0, 5.0), dpi=160)
    ax.plot(nm(wavelength_m), t_abs2, color="#1f77b4", linewidth=1.8)
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
        writer.writerow(["index", "label"] + [k + "_nm" for k in keys] + ["description"])
        for point in points:
            writer.writerow([point["index"], point["label"]] + ["{:.6f}".format(nm(point["values"][k])) for k in keys] + [describe_point(config, point)])
    lines = [
        "四孔方块 {} 自动扫描配置摘要".format(config["perturbation_name"]),
        "=" * 42,
        "扰动名称: {}".format(config["perturbation_name"]),
        "改变参数: {}".format(config["changed_parameter"]),
        "降群路径: {}".format(config["group_path"]),
        "Si 方块尺寸: {:.3f} nm x {:.3f} nm".format(nm(geom["host_x_span"]), nm(geom["host_y_span"])),
        "Si 厚度: {:.3f} nm".format(nm(geom["host_z_max"] - geom["host_z_min"])),
        "衬底尺寸: {:.3f} nm x {:.3f} nm".format(nm(geom["substrate_x_span"]), nm(geom["substrate_y_span"])),
        "衬底厚度: {:.3f} nm".format(nm(geom["substrate_z_max"] - geom["substrate_z_min"])),
        "母版孔半径: {:.3f} nm".format(nm(geom["base_radius"])),
        "母版半孔距: {:.3f} nm".format(nm(geom["base_half_pitch"])),
        "计划点数: {}".format(len(points)),
    ]
    (plan_dir / "scan_summary.txt").write_text("\n".join(lines), encoding="utf-8-sig")
    return csv_path


def write_structure_overview(run_dir, source_fsp, config, points, geom, result_master, ascii_root):
    doc = run_dir / "结构状态说明.md"
    lines = [
        "# 四孔方块 {} 结构状态说明".format(config["perturbation_name"]),
        "",
        "## 母结构",
        "- 母版 FSP：`{}`".format(source_fsp),
        "- 结构类型：C4对称结构 / 四孔方块",
        "- Si 方块对象：`{}`".format(config["host_object_name"]),
        "- 空气孔对象：`{}`，共 {} 个；同名对象按索引 1-4 区分。".format(config["hole_object_name"], len(geom["holes"])),
        "- Si 方块 x/y span：{:.6f} / {:.6f} nm".format(nm(geom["host_x_span"]), nm(geom["host_y_span"])),
        "- Si 厚度：{:.6f} nm".format(nm(geom["host_z_max"] - geom["host_z_min"])),
        "- SiO2 衬底 x/y span：{:.6f} / {:.6f} nm".format(nm(geom["substrate_x_span"]), nm(geom["substrate_y_span"])),
        "- SiO2 衬底厚度：{:.6f} nm".format(nm(geom["substrate_z_max"] - geom["substrate_z_min"])),
        "- 母版孔半径：{:.6f} nm".format(nm(geom["base_radius"])),
        "- 母版半孔距：{:.6f} nm".format(nm(geom["base_half_pitch"])),
        "",
        "## 本批次扰动",
        "- 扰动名称：{}".format(config["perturbation_name"]),
        "- 改变参数：{}".format(config["changed_parameter"]),
        "- 降群路径：{}".format(config["group_path"]),
        "- 预期影响：{}".format(config["expected_effect"]),
        "- 计划点数：{}".format(len(points)),
        "- 起点：{}".format(describe_point(config, points[0]) if points else "无"),
        "- 终点：{}".format(describe_point(config, points[-1]) if points else "无"),
        "",
        "## 路径说明",
        "- results 工作母版：`{}`".format(result_master),
        "- Lumerical 英文镜像目录：`{}`".format(ascii_root),
        "- 每个扫描点的最终 .fsp、Excel、abs^2 图片均保存于本 run 目录下。",
    ]
    doc.write_text("\n".join(lines), encoding="utf-8-sig")
    return doc


def write_manifest_header(path):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow(["index", "description", "fsp", "xlsx", "png", "elapsed_s", "status"])


def append_manifest(path, point, description, paths, elapsed, status):
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow([point["index"], description, paths["fsp"], paths["xlsx"], paths["png"], "{:.3f}".format(elapsed), status])


def parse_args(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--preview", action="store_true", help="只生成扫描计划和说明文档，不运行 FDTD。")
    parser.add_argument("--test-run", action="store_true", help="真实仿真测试模式，只跑 TEST_POINT_COUNT 个点。")
    parser.add_argument("--full-run", action="store_true", help="完整真实仿真模式，跑完全部扫描点。")
    parser.add_argument("--resume", action="store_true", help="继续最近一个 run_* 批次。")
    parser.add_argument("--run-dir", default=None, help="指定输出批次目录。相对路径会放在 results/扰动名 下。")
    parser.add_argument("--max-points", type=int, default=None, help="额外限制最多运行/预览前 N 个点。")
    parser.add_argument("--show-gui", action="store_true", help="显示 FDTD GUI，默认隐藏运行。")
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
        print("请选择四孔方块 {} 脚本运行模式：".format(config["perturbation_name"]))
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
    args = parse_args("四孔方块 {} FDTD 自动化扫描".format(config["perturbation_name"]))
    mode = apply_run_mode(args, config)
    if mode in ("test", "full") and getattr(args, "prompted_mode", False):
        maybe_ask_fdtd_runtime_overrides(config)

    source_fsp = find_source_fsp(structure_root)
    source_hash_before = file_sha256(source_fsp)
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
    print("Si 方块尺寸: {:.3f} nm x {:.3f} nm, 厚度 {:.3f} nm".format(nm(geom["host_x_span"]), nm(geom["host_y_span"]), nm(geom["host_z_max"] - geom["host_z_min"])))
    print("衬底尺寸: {:.3f} nm x {:.3f} nm, 厚度 {:.3f} nm".format(nm(geom["substrate_x_span"]), nm(geom["substrate_y_span"]), nm(geom["substrate_z_max"] - geom["substrate_z_min"])))
    print("母版孔半径: {:.3f} nm；母版半孔距: {:.3f} nm".format(nm(geom["base_radius"]), nm(geom["base_half_pitch"])))
    print("扰动: {}；降群路径: {}".format(config["perturbation_name"], config["group_path"]))
    print("计划仿真点数: {}".format(len(points)))
    print("扫描计划已保存: {}".format(plan_csv))
    print("结构说明已保存: {}".format(overview_doc))

    if args.preview:
        print("当前为 preview 模式：只生成计划，不运行 FDTD。扫描点如下：")
        for point in points:
            print("  #{:04d}: {}".format(point["index"], describe_point(config, point)))
        assert_source_unchanged(source_fsp, source_hash_before)
        return

    if not args.resume or not manifest_path.exists():
        write_manifest_header(manifest_path)

    run_started = time.time()
    with log_path.open("a", encoding="utf-8-sig") as log:
        log.write("\n==== Run started at {} ====\n".format(datetime.now().isoformat(timespec="seconds")))
        for ordinal, point in enumerate(points, start=1):
            paths = point_paths(folders, config, point)
            description = describe_point(config, point)
            if args.resume and paths["fsp"].exists() and paths["xlsx"].exists() and paths["png"].exists():
                message = "[{}/{}] 已存在，跳过：{}".format(ordinal, len(points), paths["stem"])
                print(message)
                log.write(message + "\n")
                continue
            message = "[{}/{}] 开始仿真：{}".format(ordinal, len(points), paths["stem"])
            print(message)
            log.write(message + "\n")
            param_message = "    当前参数: {}；剩余组数(含当前): {}/{}".format(description, len(points) - ordinal + 1, len(points))
            print(param_message)
            log.write(param_message + "\n")
            start = time.time()
            try:
                work_fsp = ascii_root / ("work_{}.fsp".format(paths["stem"]))
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
                shutil.copy2(str(work_fsp), str(paths["fsp"]))
                save_transmission_excel(paths["xlsx"], config, point, geom, wavelength_m, frequency_hz, transmission)
                save_abs2_plot(paths["png"], config, point, wavelength_m, transmission)
                elapsed = time.time() - start
                append_manifest(manifest_path, point, description, paths, elapsed, "ok")
                remain = max(0, len(points) - ordinal)
                avg = (time.time() - run_started) / float(max(1, ordinal))
                done_message = "    完成并保存，用时 {}；已完成 {}/{}；还剩 {} 组；预计还需要 {}".format(format_duration(elapsed), ordinal, len(points), remain, format_duration(avg * remain))
                print(done_message)
                log.write(done_message + "\n")
            except Exception as exc:
                elapsed = time.time() - start
                append_manifest(manifest_path, point, description, paths, elapsed, "failed: {}".format(exc))
                log.write("    失败，用时 {}：{}\n".format(format_duration(elapsed), exc))
                raise
    assert_source_unchanged(source_fsp, source_hash_before)
    print("全部完成。结果目录: {}".format(run_dir))
