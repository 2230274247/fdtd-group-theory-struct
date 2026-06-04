# BZF 使用说明与验收报告

生成时间：2026-05-14

## BZF 核心思想

BZF 不是简单复制一个 primitive cell。正确逻辑是：

1. 沿指定方向把 primitive period `a` 扩展为 supercell period `A = folding_order * a`。
2. `eta=0` 时是 simple-copy baseline，只能说明数学折叠关系。
3. `eta != 0` 时，A/B 子 cell 不再等价，原 primitive 平移周期被破坏，supercell period 才成为真实物理周期。

当前脚本统一使用：

```text
SCAN_PARAMETER_NAME = eta_nm
```

为了兼容网页总控，脚本仍保留：

```text
START_NM / END_NM / STEP_NM
```

但内部记录和 manifest 中按 `eta_nm` 解释。

## 双圆盘四圆盘坐标核对

双圆盘 BZF 参数：

```text
L_NM = 450.0
BASE_DELTA_NM = 180.0
DISK_RADIUS_NM = 145.0
DISK_HEIGHT_NM = 420.0
PRIMITIVE_PERIOD_X_NM = 900.0
SUPERCELL_PERIOD_X_NM = 1800.0
BZF_STRATEGY = copy_then_eta_break
```

公式：

```text
x1 = -L - (BASE_DELTA + eta)
x2 = -L + (BASE_DELTA + eta)
x3 = +L - (BASE_DELTA - eta)
x4 = +L + (BASE_DELTA - eta)
```

实测：

| eta_nm | x positions nm | primitive period preserved | physical BZF perturbation |
|---:|---|---|---|
| 0 | -630; -270; 270; 630 | True | False |
| 5 | -635; -265; 275; 625 | False | True |
| 20 | -650; -250; 290; 610 | False | True |

结论：双圆盘坐标公式符合文档要求。`eta=0` 是 simple-copy baseline；`eta!=0` 是实际 BZF 扰动。

## 源 .fsp 保护

已确认：

- 公共模块运行前计算源 `.fsp` 的 SHA256。
- 每个 run 会复制源 `.fsp` 到 `05_work_fsp/master_template.fsp`。
- 每个 run 会保存 `01_supercell_fsp/source_readonly_copy.fsp`。
- 每个扫描点基于 master copy 生成工作 FSP，不直接修改源 `.fsp`。
- 每个扫描点运行前调用 `assert_source_unchanged`。
- 出错时写入 traceback，不破坏源文件。

## 当前支持的 BZF 结构

已验收 18 个 BZF 脚本，均可调用：

```text
brillouin_zone_folding_common.py
```

并通过：

- preview
- structure-only
- manifest 写入
- geometry_validation.csv 写入

记录文件：

- `docs/bzf_preview_validation.csv`
- `docs/bzf_structure_only_validation.csv`
- `docs/bzf_validation_summary.csv`

收尾复查时间：2026-05-14 18:48 +08:00

- 18 个 BZF run 脚本编译检查通过。
- `docs/bzf_validation_summary.csv` 显示 18/18 preview 与 structure-only 通过。
- `docs/manifest_field_check.csv` 显示 18/18 manifest 字段完整。
- `docs/bzf_structure_only_validation.csv` 已回填 clean UTF-8 manifest / geometry_validation 路径。

## 如何运行

只生成扫描计划，不打开 FDTD：

```powershell
python run_fdtd_brillouin_zone_folding_sweep.py --mode preview --max-points 1
```

打开 FDTD API，生成超胞 FSP，但不运行真实仿真：

```powershell
python run_fdtd_brillouin_zone_folding_sweep.py --mode test --structure-only --max-points 1
```

真实测试前几个点：

```powershell
python run_fdtd_brillouin_zone_folding_sweep.py --mode test
```

真实全量运行：

```powershell
python run_fdtd_brillouin_zone_folding_sweep.py --mode full
```

建议 full 前先确认 preview 和 structure-only 通过。

## 输出目录

每个 BZF run 输出：

```text
00_scan_plan/scan_points.csv
01_supercell_fsp/*.fsp
02_topology_metrics/bzf_supercell_metrics.csv
03_brillouin_folding_png/*_geometry_topview.png
04_logs/manifest.csv
04_logs/geometry_validation.csv
05_work_fsp/master_template.fsp
布里渊区折叠_脚本实现说明.md
```

若运行真实仿真，还会输出：

```text
02_transmission_excel/*.xlsx
03_transmission_abs2_png/*.png
```

## 当前限制

- 双圆盘已闭环为 `copy_then_eta_break`。
- 其他母结构目前多数仍使用 `center_distance` 兼容策略，已能生成 supercell 和 geometry_validation，但是否能作为严格 physical BZF perturbation，需要按具体 motif 再做物理规则定制。
- 本次验收没有运行 full FDTD，因此不评价真实谱线收敛性。

## 后续建议

1. 优先把双圆盘作为 BZF 标准样例，用 eta=0、eta>0、eta<0 做完整物理解释。
2. 对每个母结构补充专属 A/B 子 cell 扰动规则，例如半径交替、孔偏移交替、裂缝宽度交替。
3. 对候选 BZF run 补充 k/角度扫描、E/H 场图、模式对称性和 Q 随 eta 的变化。

## 验收结论

BZF 当前版本已达到“能运行、能生成结构、能保护源文件、能输出几何验证、能复现”的交付状态。双圆盘物理逻辑已闭环；其他结构具备通用框架，但后续仍需逐结构定制 physical perturbation。
