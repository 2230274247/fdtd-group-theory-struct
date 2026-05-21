# 本系列 FDTD 自动化脚本的继承规则

## 目录与命名

1. 每一种扰动都放在对应结构 `coding` 目录下的独立文件夹中。
2. 输出统一放在 `results/扰动名称/` 下，并按批次时间戳新建目录。
3. 输出批次目录内固定使用：`00_scan_plan`、`01_fsp_files`、`02_transmission_excel`、`03_transmission_png_abs2`、`04_logs`。

## FSP 文件处理

1. 脚本必须先把原始 `.fsp` 复制到 `05_work_fsp` 作为 `master_template.fsp`。
2. 每个扫描点从 `master_template.fsp` 复制出独立的 `work_*.fsp`。
3. 参数修改只能发生在当前扫描点的 `work_*.fsp` 上。

## 运行模式

必须支持 `RUN_MODE = "ask"`、`"test"`、`"full"`、`"preview"` 和命令行参数 `--preview`、`--test-run`、`--full-run`、`--resume`、`--run-dir`、`--show-gui`、`--max-points`。

## 兼容性

必须兼容 Lumerical v202 自带 Python 3.6.8。不使用 `dataclasses`、`from __future__ import annotations` 等新版特性。

## 当前十字结构数据

1. 水平臂对象：`Si_cross_horizontal`（x span = 580 nm, y span = 160 nm）
2. 竖直臂对象：`Si_cross_vertical`（x span = 160 nm, y span = 580 nm）
3. 透射监视器：`T`
4. 结构厚度：约 `420 nm`
5. 周期：`900 nm`
6. 材料：Si (Silicon) - Palik
