# FDTD 代码优化验收报告

生成时间：2026-05-14

## 验收范围

本次验收覆盖：

- `fdtd_master_controller.py`
- `fdtd_results_manager.py`
- `brillouin_zone_folding_common.py`
- 所有网页总控发现的 `run_fdtd_*.py`
- 所有 `coding/布里渊区折叠/run_fdtd_brillouin_zone_folding_sweep.py`

本次只做 preview / structure-only / dry-run，不做 full FDTD 仿真。

## 已完成的优化项

1. 总控稳定性

- `fdtd_master_controller.py` 已支持 `--child-timeout-s`。
- 网页端启动总控时已传入 `child_timeout_s`。
- 总控 preview 全量验收已完成。

2. 结果管理

- `fdtd_results_manager.py` 已支持 `--dry-run`。
- `fdtd_results_manager.py` 已支持 `--keep-latest N`。
- 已验证 `--normalize-all --dry-run --keep-latest 2` 可执行，退出码为 0。
- 验证日志：`docs/validation_logs/results_manager_normalize_dry_run_utf8.log`

3. BZF 公共模块

- `brillouin_zone_folding_common.py` 已支持 `BZF_STRATEGY`。
- 当前支持：`simple_copy`、`center_distance`、`copy_then_eta_break`、`custom_positions`。
- 已增加 `geometry_validation.csv`。
- 每个 scan point 已 try/except，失败不会中断整个扫描。
- manifest 中已补齐验收字段。

## 总控 preview 验收

命令：

```powershell
python fdtd_master_controller.py --mode preview --style sequential --all --child-timeout-s 60 --yes
```

结果：

- 启动脚本数：91
- 状态：全部完成
- 未发现 Traceback、失败、异常、timeout。
- 验证日志：`docs/validation_logs/master_controller_preview_all.log`

## BZF structure-only 验收

命令模式：

```powershell
python run_fdtd_brillouin_zone_folding_sweep.py --mode test --structure-only --max-points 1
```

结果：

| 项目 | 数量 |
|---|---:|
| BZF 脚本总数 | 18 |
| preview 通过 | 18 |
| structure-only 通过 | 18 |
| timeout | 0 |
| failed | 0 |

记录文件：

- `docs/bzf_preview_validation.csv`
- `docs/bzf_structure_only_validation.csv`
- `docs/bzf_validation_summary.csv`
- `docs/validation_logs/bzf_structure_only_*.log`

## manifest 字段检查

要求字段：

- `structure_name`
- `run_id`
- `strategy`
- `bzf_strategy`
- `parameters`
- `source_fsp`
- `output_dir`
- `status`
- `error_message`
- `traceback_file`
- `walltime_s`
- `max_point_walltime_s`
- `geometry_validation_file`
- `created_at`

检查结果：

- 检查脚本数：18
- 字段完整：18
- 字段缺失：0
- 记录文件：`docs/manifest_field_check.csv`

## 收尾复查记录

复查时间：2026-05-14 18:48 +08:00

- `fdtd_master_controller.py` 编译检查通过。
- `fdtd_results_manager.py` 编译检查通过。
- `brillouin_zone_folding_common.py` 编译检查通过。
- 18 个 BZF run 脚本编译检查通过。
- `docs/bzf_validation_summary.csv` 显示 18/18 preview 与 structure-only 通过。
- `docs/manifest_field_check.csv` 显示 18/18 字段检查通过。
- `docs/bzf_structure_only_validation.csv` 已回填 clean UTF-8 manifest / geometry_validation 路径。

## 当前仍存在的问题

- 本次没有运行 full FDTD，不验证真实求解器收敛性。
- 非 BZF 普通扰动脚本只做了 preview 级验收，没有逐个 structure-only 打开 FDTD 检查几何。
- `fdtd_results_manager.py` 的控制台输出依赖终端编码；已通过 `PYTHONIOENCODING=utf-8` 生成可读日志。

## 后续建议

- full 批量运行前，优先按母结构分批，而不是一次性全量运行。
- 对不收敛 run，不直接删除，先移动到“不收敛结果”或打标签。
- 对即将用于论文/汇报的 run，建议单独做真实谱线拟合，补充正式 FWHM/Q。

## 验收结论

FDTD 代码优化已达到当前交付阶段要求：总控可批量 preview，BZF 可 structure-only 生成超胞，结果整理 dry-run 可用，失败记录和 manifest 字段已补齐。
