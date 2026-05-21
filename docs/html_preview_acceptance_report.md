# HTML 预览页面验收报告

生成时间：2026-05-14

## 验收范围

本次验收对象为：

- `结果查看器_html/index.html`
- `结果查看器_html/server.py`
- `结果查看器_html/assets/app.css`
- `结果查看器_html/assets/bzf.js`
- `结果查看器_html/topology_transition_analysis.html`
- `结果查看器_html/assets/vendor/plotly-2.35.2.min.js`

目标是收尾，不做大范围重构，重点保证页面稳定、可读、可复现。

## 已完成内容

1. 视觉与结构

- 已将主要 CSS 拆分到 `assets/app.css`。
- 已保留绿色主色，并增加 `--ok / --warn / --bad / --info / --violet` 等语义色。
- 已增加紧凑模式按钮。
- 已优化 Dashboard、run 页面、BZF 卡片、文件卡片、标签和归档建议区域的基础样式。

2. Dashboard

- 已增加“高价值候选”。
- 已增加“风险提醒”。
- 已增加“最近运行 / 最近查看”。
- 已保留原有有效 run、谱线、不收敛、扰动覆盖、网页总控、结果管理、拓扑分析入口。

3. run 详情页

- 已增加 tab：谱图、全部曲线、挑选趋势、趋势、指标表、异常点、BZF分析、文件、结构说明。
- 曲线图支持 eta=0 / delta=0 基线黑色加粗。
- 不收敛曲线使用红色虚线。
- 当前选中曲线使用主色高亮。
- 已增加扫描点缩略矩阵。
- 已增加文件 tab，便于打开 run 文件夹、manifest、scan_points、PNG、XLSX、FSP。

4. BZF 分析

- 已新增 `assets/bzf.js`。
- 可自动识别 BZF / Brillouin / folding / supercell / eta / 布里渊 / 折叠 / 超胞关键词。
- 已显示 primitive period、supercell period、folding order、eta、simple-copy baseline、physical perturbation、span checklist。
- 已绘制简化超胞 SVG。

5. 标签与摘要

- 已增加 run 标签：值得复跑、可用于报告、疑似不收敛、需要加密扫描、无价值。
- 标签保存到 `view_state.json`，不修改原始 results。
- 已增加“复制 Markdown 摘要”按钮。

6. 结果管理

- 已增加“生成归档建议”，只提示，不移动、不删除。
- 已增加批量标签功能，可给选中扰动的最新 run 打标签。

## 修复的问题

- 已全局搜索并修复 `index.html`、`topology_transition_analysis.html`、`assets/bzf.js` 中的可见乱码文案。
- 已补 `server.py` 对 `/assets/...` 的静态资源路由。
- 已补 `/favicon.ico` 204 响应，避免浏览器控制台产生无意义 404。
- 已加入 Plotly 本地 vendor：`assets/vendor/plotly-2.35.2.min.js`。
- 若 Plotly 本地和 CDN 都失败，页面仍使用内置 SVG 曲线 fallback，不会整体崩溃。

## T / FWHM / Q 指标说明

拓扑分析页的指标已调整为更清楚的表头：

- `T_feature`：主导特征处的透射值。
- 若 `type=dip`，`T_feature` 是谷底透射，即 `T_min`。
- 若 `type=peak`，`T_feature` 是峰顶透射。
- `baseline`：谱线两端的稳健中位数基线。
- `contrast`：特征相对基线的粗略对比度。
- `FWHM rough`：按半深或半高估计的粗略宽度。
- `Q rough = lambda / FWHM rough`。

因此截图中 `T=0.00008` 这类很小的数值不是“峰值很小”，而是该扫描点在共振谷处透射接近 0，说明存在很强的透射抑制。它可以作为候选强共振/强耦合点，但不能单独证明拓扑相变。

## 验证记录

已执行：

```powershell
node --check index_inline_js
node --check topology_inline_js
node --check assets/bzf.js
python -c "compile(server.py)"
Invoke-WebRequest http://127.0.0.1:8787/
Invoke-WebRequest http://127.0.0.1:8787/assets/app.css
Invoke-WebRequest http://127.0.0.1:8787/assets/bzf.js
Invoke-WebRequest http://127.0.0.1:8787/assets/vendor/plotly-2.35.2.min.js
```

2026-05-14 18:48 收尾复查：

- `index.html` 与 `topology_transition_analysis.html` 内联 JavaScript 语法检查通过。
- `assets/bzf.js` 语法检查通过。
- `server.py` Python 编译检查通过。
- HTTP 冒烟检查通过：首页、CSS、BZF JS、本地 Plotly、拓扑分析页和关键 API 均返回 200。

无头 Edge 验证：

- 首页可打开。
- Plotly 本地加载成功。
- Dashboard 正常显示。
- run 详情页可切换新增 tab。
- 拓扑分析页可生成热图、特征表和趋势图。
- 未发现 pageerror 或 console error。

## 仍存在的小问题

- `topology_transition_analysis.html` 仍为单文件页面，未拆 CSS/JS。当前保留是为了避免扩大重构。
- FWHM/Q 仍为粗估，不等价于正式谱线拟合。
- HTML 的高价值候选会优先使用已有字段；若历史结果没有 FWHM/Q，则按 minT/maxT/完整谱线保守排序。

## 如何启动

```powershell
cd "H:\FDTD outcome\struct\群论_struct\结果查看器_html"
python server.py
```

浏览器打开：

```text
http://127.0.0.1:8787/
```

## 验收结论

HTML 预览页面已达到当前阶段可交付状态：能运行、能看结果、能进入拓扑分析、能管理标签与归档建议、Plotly 有本地备用、缺字段时不会崩溃。
