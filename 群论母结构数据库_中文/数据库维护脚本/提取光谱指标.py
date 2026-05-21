# -*- coding: utf-8 -*-
"""从《光谱数据归档》中的光谱文本提取指标，并写入《光谱指标结果表.xlsx》。"""
from pathlib import Path
import openpyxl

数据库根目录 = Path(__file__).resolve().parents[1]
光谱目录 = 数据库根目录 / "光谱数据归档"
输出路径 = 数据库根目录 / "数据表格模板" / "光谱指标结果表.xlsx"
表头 = ['仿真样本编号','结果编号','光谱文件编号','共振类型','共振峰波长_nm','峰值透过率','透射谷波长_nm','谷值透过率','半峰宽_nm','品质因子_Q','主峰数量','左侧边带透过率','右侧边带透过率','最大边带透过率','Fano非对称参数q','拟合均方误差','光谱质量评级','是否满足当前目标','提取方法','提取脚本版本','提取日期','备注']

def 读取光谱(path):
    数据 = []
    for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        parts = [x for x in line.strip().replace(',', ' ').replace('\t', ' ').split(' ') if x]
        if len(parts) < 2:
            continue
        try:
            数据.append((float(parts[0]), float(parts[1])))
        except ValueError:
            pass
    return sorted(数据)

def 提取指标(数据):
    if len(数据) < 5:
        return None
    峰位, 峰值 = max(数据, key=lambda x: x[1])
    谷位, 谷值 = min(数据, key=lambda x: x[1])
    基线 = min(数据[0][1], 数据[-1][1])
    半高 = 基线 + (峰值 - 基线) / 2
    峰索引 = max(range(len(数据)), key=lambda i: 数据[i][1])
    左 = 右 = None
    for i in range(峰索引, 0, -1):
        if min(数据[i-1][1], 数据[i][1]) <= 半高 <= max(数据[i-1][1], 数据[i][1]):
            左 = 数据[i][0]; break
    for i in range(峰索引, len(数据)-1):
        if min(数据[i][1], 数据[i+1][1]) <= 半高 <= max(数据[i][1], 数据[i+1][1]):
            右 = 数据[i][0]; break
    半峰宽 = abs(右 - 左) if 左 is not None and 右 is not None and 右 != 左 else ''
    Q = round(峰位 / 半峰宽, 6) if 半峰宽 else ''
    return 峰位, 峰值, 谷位, 谷值, 半峰宽, Q

wb = openpyxl.Workbook(); ws = wb.active; ws.title = '光谱指标结果表'; ws.append(表头)
数量 = 0
for path in list(光谱目录.rglob('*.txt')) + list(光谱目录.rglob('*.csv')):
    指标 = 提取指标(读取光谱(path))
    if not 指标:
        continue
    样本编号 = path.stem.replace('_T', '')
    ws.append([样本编号, f'metric_{样本编号}', path.stem, '透射峰', *指标, '', '', '', '', '', '', '待判断', '半高宽法+局部极值搜索', 'v1.0', '', f'来源文件：{path.name}'])
    数量 += 1
wb.save(输出路径)
print(f"已提取 {数量} 条光谱指标：{输出路径}")
