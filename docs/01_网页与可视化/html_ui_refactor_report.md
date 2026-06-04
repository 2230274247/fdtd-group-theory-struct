# HTML UI 重构验收记录

生成时间：2026-05-14

## 改造目标

本次改造将结果查看器从临时调试面板提升为“科研数据分析仪表盘 + 本地 FDTD 控制台”。改造保持现有 `server.py` API 与 FDTD 脚本逻辑兼容，不删除已有功能。

## 修改文件

- `结果查看器_html/index.html`
- `结果查看器_html/topology_transition_analysis.html`
- `结果查看器_html/assets/app.css`
- `结果查看器_html/assets/ui-refactor.css`
- `docs/html_ui_refactor_report.md`

## 新增文件

- `结果查看器_html/assets/ui-refactor.css`

## 主要改造内容

### 主页面布局

- 顶部导航改为本地 FDTD 控制台风格，增加导航激活态。
- 左侧侧边栏增加“结构数据库”标题和说明。
- run 树增加状态点、风险标记、run 类型标签、简化行内操作。
- 保留原有搜索、统计、run 选择、打开文件夹、拓扑热图入口。

### Run 详情页

- Run Header 拆为结构信息、状态标签、分析 tab、文件/管理/危险操作。
- 谱图页将表格指标改为 KPI 卡片：状态、扫描参数、最大 T、最小 T、耗时、XLSX/参数。
- 扫描点列表增加状态点，不收敛点统一红色风险提示。
- 保留谱图、全部曲线、挑选趋势、趋势、指标表、异常点、BZF 分析、文件、结构说明等原功能。

### 网页总控

- 保留三步向导：选择结构、调整参数、启动观察。
- 强化脚本选择、缺结果筛选、单脚本参数覆盖、不收敛 runtime 字段红色提示。
- 运行终端继续使用深色控制台风格，保留实时日志和最新谱图。
- 验证时只启动 `preview` 模式单脚本任务，未运行真实 full 仿真。

### 结果管理

- 结果管理改为“扫描状态 → 推荐操作 → 危险操作 → 目录分组”的流程。
- 推荐操作和危险操作视觉上分离。
- 保留 0-6 选项映射、归档建议、批量标签、移动不收敛、整理当前扰动等功能。

### 拓扑分析页

- 标题和主要文案改为中文科研场景。
- 引入同一套 `ui-refactor.css`，与主页面保持视觉统一。
- 保留热图、BZF 检查、特征趋势、代表谱线叠加、Todo 清单。

## 验证记录

已完成：

- HTML 旧乱码 / 异常字符检查通过。
- `index.html` 内联 JS 语法检查通过。
- `topology_transition_analysis.html` 内联 JS 语法检查通过。
- `server.py` 编译检查通过。
- HTTP 冒烟通过：`/`、`/assets/ui-refactor.css`、`/topology_transition_analysis.html`、`/api/scan?cache_only=1`、`/api/controller-params`、`/api/results-manager`。
- 浏览器自动化验证通过：
  - 首页能打开；
  - UI 覆盖 CSS 已加载；
  - 网页总控抽屉能打开；
  - 脚本选择器能显示 91 个扰动脚本；
  - `preview` 单脚本启动链路成功，returncode=0；
  - 结果管理能打开，显示 95 个扰动目录；
  - 结果管理推荐操作 4 项、危险操作 4 项；
  - 拓扑分析弹窗能打开，显示 11 个可分析扰动；
  - run 详情页可进入，谱图、指标卡、扫描点列表、指标表可用；
  - 拓扑分析页可打开，6 个分析 section 正常显示。

## 未执行的操作

- 未运行真实 full FDTD 仿真。
- 未执行删除 run、移动不收敛、批量整理旧文件等会改变结果目录的危险操作。

## 后续建议

- 后续可继续拆分 `index.html` 中的 JS 为 `dashboard.js`、`controller.js`、`manager.js`、`run-detail.js`。
- 可为危险操作增加统一二次确认弹窗，而不是浏览器默认 `confirm`。
- 可增加真正的列表虚拟滚动，以提升上百 run 同时展示时的性能。
