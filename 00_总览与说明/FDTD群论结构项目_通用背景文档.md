# FDTD 群论结构项目通用背景

## 1. 基本信息

| 项目项 | 内容 |
|---|---|
| 项目名称 | FDTD 群论结构 / FDTD 群论工作台 |
| GitHub 仓库 | `https://github.com/2230274247/fdtd-group-theory-struct` |
| 本地项目根目录 | `H:\FDTD outcome\struct\群论_struct` |
| 当前主要修改目录 | `H:\FDTD outcome\struct\群论_struct\结果查看器_html_v2` |
| 当前主要前端/服务 | `结果查看器_html_v2` |
| 本地页面入口 | 通常为 `http://127.0.0.1:8787/` |
| 主要运行环境 | Windows + Lumerical FDTD + Python |
| 重点任务类型 | FDTD 扰动扫描、结果索引、光谱浏览、运行控制、补做实验、质量审计 |

## 2. 项目目标

```text
高对称母结构
→ 施加可控扰动
→ 对称性降群
→ FDTD 仿真
→ 光谱指标提取
→ 结果浏览 / 候选筛选 / 逆向设计
```

| 主题 | 内容 |
|---|---|
| 结构体系 | C2、C3、C4、C6 旋转对称结构，以及近径向高对称结构 |
| 物理目标 | 研究对称性破缺后暗模/BIC 亮化、Q 值、FWHM、透射谱变化 |
| 数据映射 | `对称类别 + 母结构 + 扰动方式 + δ/参数 → 光谱响应` |
| 结果用途 | 高 Q、窄线宽、Fano/GMR/quasi-BIC 候选筛选 |

## 3. 顶层目录结构

```text
群论_struct/
├─ C2对称结构/
├─ C3对称结构/
├─ C4对称结构/
├─ C6对称结构/
├─ 近径向高对称结构/
├─ 群论母结构数据库_中文/
├─ 结果查看器_html/
├─ 结果查看器_html_v2/
├─ controller_logs/
├─ docs/
├─ fdtd_master_controller.py
├─ fdtd_results_manager.py
├─ brillouin_zone_folding_common.py
├─ README_总控脚本.md
├─ README_结果整理脚本.md
├─ 布里渊区折叠_使用说明.md
└─ 群论_struct目录总结.md
```

## 4. 标准母结构目录层级

适用于大部分 `C2/C3/C4/C6/近径向高对称结构` 下的母结构目录。

```text
某对称结构/
└─ 某母结构/
   ├─ scripts/                 # 母结构 FDTD 构建脚本
   ├─ docs/                    # 母结构参数与说明文档
   ├─ png/                     # 初步透射谱截图
   ├─ data/                    # 初步透射谱 CSV 数据
   ├─ results/                 # 扰动扫描结果
   ├─ fsp/                     # Lumerical .fsp 母文件
   └─ coding/                  # 扰动扫描脚本
      └─ 某扰动名称/
         ├─ README.md
         └─ run_fdtd_xxx_sweep.py
```

## 5. 扰动扫描结果目录层级

```text
某母结构/
└─ results/
   └─ 某扰动名称/
      └─ run_模式_时间戳/
         ├─ 00_scan_plan/
         │  └─ scan_points.csv
         ├─ 01_work_fsp/ 或 05_work_fsp/
         │  └─ *.fsp
         ├─ 02_transmission_excel/
         │  └─ *.xlsx
         ├─ 03_transmission_png_abs2/
         │  └─ *.png
         ├─ 04_logs/ 或 05_logs/
         │  ├─ manifest.csv
         │  └─ *.log
         ├─ job_manifest.json
         ├─ summary.csv
         └─ 结构状态说明.md
```

## 6. 总控脚本

| 项目项 | 内容 |
|---|---|
| 总控脚本 | `H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py` |
| 扫描对象 | `H:\FDTD outcome\struct\群论_struct\**\coding\**\run_*.py` |
| 脚本识别规则 | 文件名以 `run_` 开头，扩展名为 `.py` |
| 输出层级 | `对称类别 / 母结构 / 扰动名称 / 脚本编号` |
| 总控日志目录 | `H:\FDTD outcome\struct\群论_struct\controller_logs\master_run_时间戳\` |

### 运行模式

| 模式 | 含义 |
|---|---|
| `preview` | 只生成扫描计划，不运行真实仿真 |
| `test` | 每个脚本只真实仿真前几个测试点 |
| `full` | 完整真实仿真 |
| `ask` | 交给子脚本自己询问 |

### 执行策略

| 策略 | 含义 |
|---|---|
| `sequential` | 顺序执行，适合真实 FDTD 仿真 |
| `parallel` | 并行执行，更适合 preview，不建议大量真实仿真并行 |

### 典型命令

```bat
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --list

"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --ids 1-5 --mode preview --style sequential

"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --all --mode test --style sequential
```

## 7. 结果查看器 html_v2

当前主要修改对象：

```text
结果查看器_html_v2/
├─ index.html
├─ server_v2.py
├─ README_Codex_Build.md
├─ assets/
│  ├─ css/
│  └─ js/
│     ├─ api.js
│     ├─ pages/
│     │  ├─ run-control.js
│     │  ├─ result-browser.js
│     │  ├─ spectrum-diagnosis.js
│     │  ├─ mode-coupling.js
│     │  ├─ quality-audit.js
│     │  ├─ patch-experiment.js
│     │  └─ resources.js
│     └─ ...
└─ templates/
   ├─ patch_points.template.csv
   └─ patch_request.template.json
```

### html_v2 主要页面

| 页面/模块 | 作用 |
|---|---|
| 研究总览 | 项目总体统计、候选概览、最近活跃 run |
| 运行控制 | 调用总控脚本，选择结构/扰动/脚本，查看运行日志 |
| 结果浏览 | 浏览 run、样本、输出文件、透射谱、指标 |
| 光谱诊断 | 查看异常、峰型、收敛、谱图质量 |
| 模式接力 / 拓扑候选 | 分析特殊光谱演化和候选结构 |
| 质量审计 | 检查结果完整性、异常、缺失文件 |
| 补做实验 | 针对缺失或异常样本进行补做、覆盖或继承结果 |
| 资源浏览 | 浏览项目文件、脚本、结果资源 |

## 8. 关键文件定位

| 类型 | 路径 |
|---|---|
| Web 服务后端 | `结果查看器_html_v2/server_v2.py` |
| 主页面入口 | `结果查看器_html_v2/index.html` |
| 前端 API 封装 | `结果查看器_html_v2/assets/js/api.js` |
| 运行控制页面 | `结果查看器_html_v2/assets/js/pages/run-control.js` |
| 结果浏览页面 | `结果查看器_html_v2/assets/js/pages/result-browser.js` |
| 光谱诊断页面 | `结果查看器_html_v2/assets/js/pages/spectrum-diagnosis.js` |
| 质量审计页面 | `结果查看器_html_v2/assets/js/pages/quality-audit.js` |
| 补做实验页面 | `结果查看器_html_v2/assets/js/pages/patch-experiment.js` |
| 总控执行入口 | `fdtd_master_controller.py` |
| 结果整理入口 | `fdtd_results_manager.py` |
| C2 公共扫描模块 | `C2对称结构/c2_sweep_common.py` |
| C3 公共扫描模块 | `C3对称结构/c3_sweep_common.py` |
| C6 公共扫描模块 | `C6对称结构/c6_sweep_common.py` |
| C4 专用公共模块 | `C4对称结构/*/coding/*_common.py` |
| 数据库文档目录 | `群论母结构数据库_中文/` |
| 总控日志目录 | `controller_logs/` |

## 9. 数据与文件规则

| 规则项 | 内容 |
|---|---|
| 扰动脚本命名 | `run_fdtd_xxx_sweep.py` |
| 运行结果命名 | `run_preview_时间戳`、`run_test_时间戳`、`run_full_时间戳` |
| 样本编号 | 一般为扰动扫描中的序号或结构化 sample id |
| 谱图数据 | 通常来自 `02_transmission_excel/*.xlsx` |
| 谱图图片 | 通常来自 `03_transmission_png_abs2/*.png` |
| FDTD 工作文件 | 通常来自 `01_work_fsp/` 或 `05_work_fsp/` |
| 运行记录 | `manifest.csv`、`job_manifest.json`、`summary.csv`、`*.log` |
| 母文件 | 通常位于母结构目录的 `fsp/` 下 |
| 补做实验原则 | 优先基于对应母文件或 run 内工作 `.fsp` 复制后修改，不直接破坏原始母文件 |

## 10. 常见修改注意事项

| 注意项 | 要求 |
|---|---|
| 路径处理 | 必须兼容 Windows 路径、中文目录、空格路径 |
| 文件扫描 | 不要硬编码单一结构；应递归扫描 `C2/C3/C4/C6/近径向高对称结构` |
| 日志输出 | 长任务应支持实时日志流或增量读取，避免结束后一次性输出 |
| 缓存策略 | 旧 run 不变时尽量复用缓存，新 run 只做增量扫描 |
| 图像加载 | 浏览器不能直接访问本地绝对路径，应通过后端静态路由或文件代理返回 |
| 单位显示 | 几何参数应优先显示为 `nm` 或 `um`，避免直接显示科学计数法 |
| 收敛判断 | 不应只看 `T > 1`；还应考虑连续震荡、非物理尖峰、缺失数据、导出失败等 |
| 结果覆盖 | 补做单个样本时需要明确覆盖策略、备份策略、manifest 更新策略 |
| 源文件安全 | 禁止直接修改母版 `.fsp`，除非用户明确要求 |
| 浏览器验收 | 修改 html_v2 后应启动本地服务并用浏览器实际检查 UI、交互、日志、谱图、按钮 |

## 11. 当前重点工作方向

| 优先级 | 内容 |
|---|---|
| 高 | 运行控制页实时日志输出 |
| 高 | 结果浏览页透射谱图片正常显示 |
| 高 | 不收敛/异常结果判断逻辑修正 |
| 中 | `δ / 参数` 从科学计数法改为带单位显示 |
| 中 | `操作` 栏指标准确性与可手动修正 |
| 中 | 单个异常样本补做实验接口 |
| 中 | 一键打开 run 文件夹 |
| 中 | 一键打开单次仿真的 `.fsp` 文件 |
| 低 | 页面缓存、增量扫描、视图状态保存 |

## 12. 给其他 AI 的固定开场信息

```text
这是一个 Windows 本地 FDTD 群论结构项目。

GitHub 仓库：
https://github.com/2230274247/fdtd-group-theory-struct

本地项目根目录：
H:\FDTD outcome\struct\群论_struct

当前主要修改对象：
H:\FDTD outcome\struct\群论_struct\结果查看器_html_v2

项目核心链路：
高对称母结构 → 扰动降群 → FDTD 仿真 → 透射谱/指标提取 → html_v2 结果浏览与运行控制。

请优先围绕 html_v2 修改：
server_v2.py、index.html、assets/js/api.js、assets/js/pages/*.js、assets/css/*.css。

仿真脚本主要位于：
C2/C3/C4/C6/近径向高对称结构 下各母结构的 coding/扰动名称/run_fdtd_xxx_sweep.py。

运行结果主要位于：
某母结构/results/某扰动名称/run_模式_时间戳/

总控脚本：
fdtd_master_controller.py

注意：
路径包含中文和空格，必须兼容 Windows 路径。
不要擅自移动大目录。
不要直接破坏母版 .fsp。
修改后需要用浏览器打开本地页面实际验收。
```

## 13. 建议 AI 先确认的文件

```text
结果查看器_html_v2/server_v2.py
结果查看器_html_v2/index.html
结果查看器_html_v2/assets/js/api.js
结果查看器_html_v2/assets/js/pages/run-control.js
结果查看器_html_v2/assets/js/pages/result-browser.js
fdtd_master_controller.py
README_总控脚本.md
群论_struct目录总结.md
```

## 14. 资料来源

```text
GitHub 仓库：
https://github.com/2230274247/fdtd-group-theory-struct

用户提供本地路径：
H:\FDTD outcome\struct\群论_struct

用户指定当前主要修改目录：
H:\FDTD outcome\struct\群论_struct\结果查看器_html_v2
```
