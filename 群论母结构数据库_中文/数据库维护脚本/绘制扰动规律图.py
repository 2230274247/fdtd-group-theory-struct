# -*- coding: utf-8 -*-
"""读取样本表和光谱结果表，绘制 delta-Q、delta-FWHM、delta-T_peak 图。"""
from pathlib import Path
import openpyxl

数据库根目录 = Path(__file__).resolve().parents[1]
表格目录 = 数据库根目录 / "数据表格模板"
输出目录 = 数据库根目录 / "分析输出结果" / "规律图表"
输出目录.mkdir(parents=True, exist_ok=True)

try:
    import matplotlib.pyplot as plt
except Exception as exc:
    raise SystemExit(f"缺少 matplotlib，无法绘图：{exc}")

def 读表(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    headers = list(rows[0])
    return [dict(zip(headers, row)) for row in rows[1:] if any(row)]

样本 = {r['仿真样本编号']: r for r in 读表(表格目录 / '仿真样本参数表.xlsx')}
指标 = 读表(表格目录 / '光谱指标结果表.xlsx')
分组 = {}
for row in 指标:
    sid = row.get('仿真样本编号')
    if sid in 样本:
        分组.setdefault(样本[sid].get('母结构家族编号'), []).append((float(样本[sid].get('归一化扰动delta')), row))

for 字段, 纵轴, 文件名 in [('品质因子_Q','Q 值','扰动强度_delta_与_Q值.png'), ('半峰宽_nm','半峰宽 nm','扰动强度_delta_与_半峰宽.png'), ('峰值透过率','峰值透过率','扰动强度_delta_与_峰值透过率.png')]:
    plt.figure(figsize=(7, 5))
    for 家族, rows in 分组.items():
        xs, ys = [], []
        for delta, row in sorted(rows):
            try:
                xs.append(delta); ys.append(float(row[字段]))
            except Exception:
                pass
        if xs:
            plt.plot(xs, ys, marker='o', label=家族)
    plt.xlabel('归一化扰动强度 delta'); plt.ylabel(纵轴); plt.grid(True, alpha=0.3); plt.legend(); plt.tight_layout(); plt.savefig(输出目录 / 文件名, dpi=220); plt.close()
print(f"绘图完成，输出目录：{输出目录}")
