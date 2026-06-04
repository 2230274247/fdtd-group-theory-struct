# 最终交付总索引

生成时间：2026-05-14

## 已完成内容

### HTML 预览美化

- CSS 拆分到 `assets/app.css`。
- Plotly 本地 vendor 已加入。
- Dashboard 增加高价值候选、风险提醒、最近运行/最近查看。
- run 页面增加趋势、异常点、BZF分析、文件、标签、Markdown 摘要。
- 拓扑分析页修正 T/FWHM/Q 表达，明确 `T_feature` 是主导峰/谷处的透射值。
- 归档建议与批量标签已加入，且不自动删除文件。

### FDTD 代码优化

- 总控支持 `--child-timeout-s`。
- 结果整理支持 `--dry-run` 与 `--keep-latest N`。
- 总控 preview 全量验收 91 个脚本通过。
- BZF structure-only 验收 18 个脚本通过。
- manifest 字段一致性检查 18/18 通过。

### BZF 指导与代码实现

- 公共模块：`brillouin_zone_folding_common.py`
- 支持策略：`simple_copy`、`center_distance`、`copy_then_eta_break`、`custom_positions`
- 双圆盘 `copy_then_eta_break` 已按文档公式核对。
- 已输出 `geometry_validation.csv` 和 top-view geometry PNG。
- 源 `.fsp` 保护逻辑已确认。

## 关键文件路径

| 类型 | 路径 |
|---|---|
| HTML 主页面 | `H:\FDTD outcome\struct\群论_struct\结果查看器_html\index.html` |
| HTML server | `H:\FDTD outcome\struct\群论_struct\结果查看器_html\server.py` |
| CSS | `H:\FDTD outcome\struct\群论_struct\结果查看器_html\assets\app.css` |
| BZF 前端模块 | `H:\FDTD outcome\struct\群论_struct\结果查看器_html\assets\bzf.js` |
| Plotly 本地 vendor | `H:\FDTD outcome\struct\群论_struct\结果查看器_html\assets\vendor\plotly-2.35.2.min.js` |
| 拓扑分析页 | `H:\FDTD outcome\struct\群论_struct\结果查看器_html\topology_transition_analysis.html` |
| 总控脚本 | `H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py` |
| 结果整理脚本 | `H:\FDTD outcome\struct\群论_struct\fdtd_results_manager.py` |
| BZF 公共模块 | `H:\FDTD outcome\struct\群论_struct\brillouin_zone_folding_common.py` |
| BZF 验收汇总 | `H:\FDTD outcome\struct\群论_struct\docs\bzf_validation_summary.csv` |
| manifest 字段检查 | `H:\FDTD outcome\struct\群论_struct\docs\manifest_field_check.csv` |
| HTML 验收报告 | `H:\FDTD outcome\struct\群论_struct\docs\html_preview_acceptance_report.md` |
| FDTD 验收报告 | `H:\FDTD outcome\struct\群论_struct\docs\fdtd_optimization_acceptance_report.md` |
| BZF 使用与验收报告 | `H:\FDTD outcome\struct\群论_struct\docs\bzf_usage_and_acceptance_report.md` |

## 验收状态

| 模块 | 状态 | 是否可运行 | 是否有测试报告 | 剩余问题 |
|---|---|---|---|---|
| HTML 预览美化 | 已交付 | 是 | 是 | FWHM/Q 仍为粗估 |
| FDTD 总控 preview | 已交付 | 是 | 是 | 未做 full 仿真 |
| 结果整理 dry-run | 已交付 | 是 | 是 | 真实整理前仍建议先 dry-run |
| BZF 双圆盘 | 已闭环 | 是 | 是 | 需要后续 full 谱线验证 |
| BZF 其他结构 | 框架可用 | 是 | 是 | 物理扰动规则需逐结构定制 |

## 最终收尾复查

复查时间：2026-05-14 18:48 +08:00

已复查：

- `index.html` 与 `topology_transition_analysis.html` 内联 JavaScript 语法检查通过。
- `assets/bzf.js` 语法检查通过。
- `server.py`、`brillouin_zone_folding_common.py`、`fdtd_master_controller.py`、`fdtd_results_manager.py` Python 编译检查通过。
- 18 个 `run_fdtd_brillouin_zone_folding_sweep.py` Python 编译检查通过。
- `manifest_field_check.csv` 显示 18/18 通过。
- `bzf_validation_summary.csv` 显示 18/18 preview 与 structure-only 通过。
- HTTP 冒烟检查通过：`/`、`/assets/app.css`、`/assets/bzf.js`、`/assets/vendor/plotly-2.35.2.min.js`、`/topology_transition_analysis.html`、`/api/scan?cache_only=1`、`/api/controller-params`、`/api/results-manager` 均返回 200。
- 已将 `bzf_structure_only_validation.csv` 中旧控制台编码造成的路径乱码，回填为 clean UTF-8 路径。

## 最短使用说明

打开 HTML 预览：

```powershell
cd "H:\FDTD outcome\struct\群论_struct\结果查看器_html"
python server.py
```

访问：

```text
http://127.0.0.1:8787/
```

总控 preview 全量检查：

```powershell
cd "H:\FDTD outcome\struct\群论_struct"
python fdtd_master_controller.py --mode preview --style sequential --all --child-timeout-s 60 --yes
```

结果整理 dry-run：

```powershell
cd "H:\FDTD outcome\struct\群论_struct"
$env:PYTHONIOENCODING="utf-8"
python fdtd_results_manager.py --normalize-all --dry-run --keep-latest 2
```

BZF structure-only：

```powershell
cd "H:\FDTD outcome\struct\群论_struct\C2对称结构\双圆盘\coding\布里渊区折叠"
python run_fdtd_brillouin_zone_folding_sweep.py --mode test --structure-only --max-points 2
```

BZF full sweep：

```powershell
cd "H:\FDTD outcome\struct\群论_struct\C2对称结构\双圆盘\coding\布里渊区折叠"
python run_fdtd_brillouin_zone_folding_sweep.py --mode full
```

查看日志和结果：

```text
results\布里渊区折叠\run_*\04_logs\manifest.csv
results\布里渊区折叠\run_*\04_logs\geometry_validation.csv
results\布里渊区折叠\run_*\01_supercell_fsp
results\布里渊区折叠\run_*\03_brillouin_folding_png
```

## 总结

当前版本已经能运行、能验收、能复现，并且保护源 `.fsp`。不要把当前 BZF 结果直接作为最终拓扑相变证明；它已经适合作为下一步 full sweep、场图导出、角度/k 扫描和正式谱线拟合的稳定工作底座。
