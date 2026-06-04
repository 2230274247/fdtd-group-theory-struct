# FDTD 群论结构自动化仿真平台用户使用指南

> 适用项目：`fdtd-group-theory-struct`  
> 推荐本地根目录：`H:\FDTD outcome\struct\群论_struct`  
> 推荐使用顺序：`preview → test → full → 网页查看 → 质量审计 → 补做实验 → 结果整理`

---

## 目录

1. [项目用途](#1-项目用途)
2. [推荐使用方式总览](#2-推荐使用方式总览)
3. [启动仿真：命令行总控方式](#3-启动仿真命令行总控方式)
4. [总控运行时需要输入什么](#4-总控运行时需要输入什么)
5. [运行过程中会发生什么](#5-运行过程中会发生什么)
6. [仿真中途如何操作](#6-仿真中途如何操作)
7. [出错时会发生什么](#7-出错时会发生什么)
8. [结果保存在哪里](#8-结果保存在哪里)
9. [如何查看结果：新版 V2 网页工作台](#9-如何查看结果新版-v2-网页工作台)
10. [旧版结果查看器](#10-旧版结果查看器)
11. [如何整理旧结果](#11-如何整理旧结果)
12. [常见使用场景](#12-常见使用场景)
13. [常见问题与处理](#13-常见问题与处理)
14. [安全操作建议](#14-安全操作建议)
15. [推荐日常工作流](#15-推荐日常工作流)
16. [给新用户的一句话版](#16-给新用户的一句话版)

---

# 1. 项目用途

本项目用于批量管理和运行一系列基于群论对称性的 FDTD 扰动仿真。

整体流程可以理解为：

```text
选择结构与扰动脚本
→ 预览或确认扫描参数
→ 复制母版 FSP
→ 逐个扰动参数点修改结构
→ 调用 Lumerical FDTD 运行
→ 保存 FSP / Excel / 透射谱图 / 日志
→ 用网页工作台查看、诊断、补做和整理结果
```

项目的核心使用入口有三个：

```text
fdtd_master_controller.py          # 命令行总控：启动仿真
fdtd_results_manager.py            # 结果整理：整理旧 run
结果查看器_html_v2\server_v2.py     # 新版网页工作台：查看、控制、诊断、补做
```

---

# 2. 推荐使用方式总览

建议优先采用以下顺序：

```text
第一步：用总控脚本 preview
第二步：确认扫描点、参数、输出目录
第三步：用 test 跑少量点
第四步：网页查看 test 结果
第五步：确认无误后用 full 完整运行
第六步：网页查看结果、筛选不收敛点、必要时补做
第七步：用结果整理脚本归档旧 run
```

不建议一开始直接使用 `full --all`。

原因：

1. 多个 FDTD 仿真可能同时占用大量 CPU、内存和 License。
2. 如果扫描范围、母文件、monitor、扰动对象设置错误，full 会浪费大量时间。
3. full 模式下产生的数据量很大，错误结果后期整理成本较高。
4. 真实仿真建议使用 `sequential` 依次运行，`parallel` 更适合 `preview` 或极少量任务测试。

---

# 3. 启动仿真：命令行总控方式

## 3.1 打开 PowerShell 或 CMD

进入项目根目录：

```powershell
cd /d "H:\FDTD outcome\struct\群论_struct"
```

推荐使用 Lumerical 自带 Python 运行总控：

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py"
```

如果你已经把 Python 环境配置好，也可以直接使用：

```powershell
python "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py"
```

---

## 3.2 只查看当前有哪些可运行脚本

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --list
```

总控会扫描：

```text
H:\FDTD outcome\struct\群论_struct\**\coding\**\run_*.py
```

然后按以下信息输出可运行脚本：

```text
对称类别
母结构
扰动名称
脚本编号
最近 test / full 结果状态
```

---

## 3.3 典型运行命令

### 预览编号 1 到 5 的脚本

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --ids 1-5 --mode preview --style sequential
```

### 测试全部脚本

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --all --mode test --style sequential
```

### 只跑缺少结果的脚本

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --missing-only --mode test --style sequential
```

### 跑某几个指定脚本

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --ids 1,3,5-8 --mode test --style sequential
```

---

## 3.4 常用总控参数说明

| 参数 | 含义 | 推荐场景 |
|---|---|---|
| `--list` | 只列出可运行脚本，不启动仿真 | 查看编号 |
| `--ids 1,3,5-8` | 指定脚本编号 | 单个或小批量仿真 |
| `--all` | 选择全部脚本 | preview 或谨慎 test |
| `--missing-only` | 只跑缺少结果的脚本 | 补齐缺失任务 |
| `--mode preview` | 只生成扫描计划，不真实仿真 | 每次正式运行前 |
| `--mode test` | 只跑测试点 | 检查脚本是否能跑通 |
| `--mode full` | 完整真实仿真 | 正式产出数据 |
| `--style sequential` | 依次运行 | 真实仿真首选 |
| `--style parallel` | 并行运行 | preview 或少量轻任务 |
| `--child-timeout-s 3600` | 子脚本超时时间 | 防止卡死 |
| `--yes` | 跳过部分确认 | 自动化流程中谨慎使用 |
| `--overrides-json` | 从 JSON 传入临时参数覆盖 | 网页端或自动化调用 |

---

# 4. 总控运行时需要输入什么

如果你不加 `--ids`、`--all`、`--mode` 等参数，总控会进入交互式流程。

---

## 4.1 第一次输入：选择运行范围

界面会让你选择：

```text
1 = 单个脚本
2 = 多个脚本编号，例如 1,3,5-8
3 = 某个母结构下全部脚本
4 = 全部脚本
5 = 只查看列表，不运行
0 = 退出总控
```

建议：

```text
第一次检查：选 5
单个调试：选 1
同一类扰动批量跑：选 2
某个母结构系统跑：选 3
全部批量：选 4，但只建议 preview 或 test 阶段使用
```

---

## 4.2 第二次输入：选择运行模式

总控会询问传给子脚本的模式：

```text
1 = preview：只生成扫描计划，不仿真
2 = test：每个脚本只跑测试点
3 = full：完整仿真
```

三种模式含义如下：

| 模式 | 是否打开 FDTD | 是否真实运行仿真 | 适用场景 |
|---|---:|---:|---|
| `preview` | 通常会准备目录和计划 | 否 | 检查扫描范围、点数、输出目录 |
| `test` | 是 | 是，只跑前几个测试点 | 检查脚本是否能跑通 |
| `full` | 是 | 是，完整扫描 | 正式产出论文/分析数据 |

---

## 4.3 第三次输入：选择运行方式

一般会出现：

```text
1 = sequential：依次运行，最稳
2 = parallel：并行运行，适合 preview；真实仿真请谨慎
```

建议：

```text
preview：可以 sequential，也可以少量 parallel
test：推荐 sequential
full：强烈推荐 sequential
```

如果选择 `parallel + full`，总控可能会要求再次输入 `YES` 确认。

原因是 full 并行会明显增加：

```text
CPU 占用
内存占用
磁盘读写压力
FDTD License 占用
结果文件冲突风险
异常排查难度
```

---

## 4.4 第四次输入：是否临时覆盖扫描参数

总控可能会询问是否临时覆盖：

```text
start
end
step
simulation time
auto shutoff min
mesh accuracy
dt stability factor
```

含义是：

```text
只在本次运行中临时修改扫描范围或 FDTD 参数
不会直接改原始小脚本
```

建议：

```text
如果只是正常跑脚本：直接回车或输入 N
如果临时缩小范围测试：输入 y，然后只改 start / end / step
如果怀疑不收敛：可以适当提高 simulation time、降低 auto shutoff min、提高 mesh accuracy
```

注意：

临时覆盖适合快速验证，不建议长期依赖。若某个参数以后都要这么设置，应该回到对应小脚本顶部“用户主要修改区”中修改。

---

## 4.5 最后确认：必须输入 YES

总控会输出运行前检查报告，包括：

```text
脚本路径
扰动对象
扫描起点、终点、步长
目标扫描点数
自动步长 / 自动截断影响
安全边界
仿真时间
测试点数
收敛阈值
最近 test / full 结果
```

如果确认无误，输入：

```text
YES
```

如果参数不合适，不要输入 `YES`，直接取消，然后去对应脚本顶部“用户主要修改区”修改参数后重新运行。

---

# 5. 运行过程中会发生什么

## 5.1 preview 模式

`preview` 会创建本次 run 目录，生成扫描计划和结构说明，但不会执行真实 FDTD 仿真。

典型输出目录：

```text
results\扰动名\run_preview_时间戳\
    00_scan_plan\
        scan_points.csv
    结构状态说明.md
    01_fsp\
    04_logs\
    05_work_fsp\
```

preview 模式通常会做：

```text
找到源 FSP
复制或准备母版
读取几何信息
生成扫描点
写入 scan_points.csv
写入结构状态说明
打印预览信息
结束，不运行真实 FDTD
```

注意：

`preview` 生成 `run_preview_*` 文件夹是正常现象，不代表真实仿真已经完成。

---

## 5.2 test / full 模式

在 `test` 或 `full` 中，每个扫描点大致会经历：

```text
从母版复制当前点工作 FSP
→ 修改扰动参数
→ 保存工作 FSP
→ 调用 FDTD
→ fdtd.run()
→ 提取 T monitor 的透射谱
→ 判断谱线质量
→ 保存最终 FSP、Excel、PNG、诊断 JSON
→ 更新 manifest.csv
```

每个扫描点通常会输出：

```text
01_fsp\xxx.fsp
02_transmission_excel\xxx_transmission_abs2.xlsx
03_transmission_abs2_png\xxx_transmission_abs2.png
04_logs\xxx_diagnostic.json
05_work_fsp\xxx.fsp
manifest.csv
04_logs\manifest.csv
```

---

## 5.3 自动重试与质量检测

仿真后会进行质量检测。如果谱线或求解器状态不理想，系统会记录：

```text
quality_status
quality_flags
quality_reasons
badness_score
improvement_ratio
decision_reason
solver_status
autoshutoff_final
```

可能出现的结果：

```text
passed
need_retry
failed
failed_quarantined
skipped
```

如果质量不合格但仍允许重试，系统会保存 attempt 记录。

如果重试后仍不通过，通常不会让整个批次停止，而是会把该点标记为失败或隔离，然后继续下一个扰动点。

这对长批量仿真很重要：一个坏点不应该拖垮整个任务。

---

# 6. 仿真中途如何操作

总控支持运行中干预：

```text
s / n / skip / next：跳过当前任务，继续下一个脚本
q / quit / exit / Esc：结束当前子脚本和 FDTD 进程树，并退出总控
p：提示当前不能安全暂停，只能跳过或退出
Ctrl+C：尝试结束当前子脚本和它启动的 FDTD 进程树
```

建议：

```text
发现当前点卡死：先等一段时间，确认不是正常长仿真后按 s
发现参数整体错了：按 q 或 Ctrl+C，回到脚本修改参数
只是想暂停：不要强行挂起 FDTD，建议按 s 或 q
```

当前项目不建议在 FDTD 正在运行时强制暂停，因为这可能导致：

```text
FSP 未完整保存
Excel 未生成
PNG 未生成
manifest 状态不完整
FDTD 进程残留
License 被占用
```

---

# 7. 出错时会发生什么

## 7.1 子脚本报错

如果某个子脚本异常退出，总控通常不会立刻毁掉整个批次，而是：

```text
记录失败信息
提示当前脚本路径
提示当前参数
提示错误日志路径
继续后续任务
```

你需要查看：

```text
controller_logs\controller_run_时间戳\logs\*_stdout.log
controller_logs\controller_run_时间戳\logs\*_stderr.log
```

---

## 7.2 单点不收敛或谱线异常

如果 FDTD 能跑完，但谱线质量差，通常不会直接崩溃，而是记录质量旗标、诊断文件和 retry 历史。

可能出现：

```text
status = need_retry
quality_flags = exception / abnormal / ripple / high_T 等
failed_quarantined
```

优先检查：

```text
04_logs\manifest.csv
04_logs\retry_history.csv
04_logs\*_diagnostic.json
04_logs\attempt_artifacts\
03_transmission_abs2_png\
02_transmission_excel\
```

---

## 7.3 超时

总控支持：

```powershell
--child-timeout-s 3600
```

含义：

```text
某个子脚本运行超过指定秒数后，总控尝试结束它和它启动的 FDTD 进程树
```

建议：

```text
普通测试：3600 秒通常足够
正式 full：如果单点很慢，可以适当增大
不建议随意设置为 0，除非你确定不会卡死
```

---

## 7.4 源 FSP 被中途修改

正式仿真运行中不要手动修改源 FSP。

正确流程：

```text
先停止仿真
修改源 FSP 或母版
重新 preview
重新 test
最后 full
```

如果运行过程中修改源 FSP，可能导致：

```text
当前 run 的母版来源不一致
前后扫描点基准不一致
结果不可比较
源文件 hash 检查失败
后续点无法继续运行
```

---

# 8. 结果保存在哪里

每个子脚本自己的结果会保存到对应母结构下：

```text
某对称结构\某母结构\results\某扰动名\run_模式_时间戳\
```

典型目录如下：

```text
run_full_2026年5月xx日_xx时xx分xx秒\
    00_scan_plan\
        scan_points.csv

    01_fsp\
        每个扫描点最终 FSP

    02_transmission_excel\
        每个扫描点透射谱 Excel

    03_transmission_abs2_png\
        每个扫描点透射谱图

    04_logs\
        manifest.csv
        retry_history.csv
        *_diagnostic.json
        attempt_artifacts\

    05_work_fsp\
        每个扫描点工作 FSP

    manifest.csv
    结构状态说明.md
```

各目录含义：

| 目录 | 含义 |
|---|---|
| `00_scan_plan` | 本次扫描计划，重点看 `scan_points.csv` |
| `01_fsp` | 每个扫描点最终保存的 FSP |
| `02_transmission_excel` | 透射谱 Excel 原始数据 |
| `03_transmission_abs2_png` | 透射谱 PNG 图片 |
| `04_logs` | 日志、诊断、manifest、重试记录 |
| `05_work_fsp` | 每个扫描点的工作 FSP |
| `manifest.csv` | run 级别总表 |
| `结构状态说明.md` | 本次结构和参数说明 |

---

# 9. 如何查看结果：新版 V2 网页工作台

## 9.1 启动 V2 工作台

在 PowerShell 中运行：

```powershell
cd /d "H:\FDTD outcome\struct\群论_struct"
python "结果查看器_html_v2\server_v2.py" --root "H:\FDTD outcome\struct\群论_struct" --port 8787
```

浏览器打开：

```text
http://127.0.0.1:8787/
```

如果端口被占用，可以换一个端口，例如：

```powershell
python "结果查看器_html_v2\server_v2.py" --root "H:\FDTD outcome\struct\群论_struct" --port 8790
```

然后打开：

```text
http://127.0.0.1:8790/
```

---

## 9.2 V2 工作台主要页面

V2 工作台主要包含：

```text
研究总览
运行控制
结果浏览
光谱诊断
模式接力 / 拓扑候选
质量审计
补做实验
资源浏览
```

建议使用顺序：

```text
研究总览：先看全局 KPI、群覆盖、候选、风险
运行控制：选择脚本，预览或启动仿真任务
结果浏览：按 run 树查看某次仿真的样本、文件和谱图
光谱诊断：看 T(λ)、参数趋势、质量旗标
质量审计：集中看不收敛、缺失、异常样本
补做实验：针对缺失证据生成补做任务包
资源浏览：按需打开本地文件、日志、FSP、Excel、PNG
```

---

## 9.3 网页刷新与缓存

V2 工作台通常采用：

```text
快速首屏
后台预热
用户优先
增量更新
任务记录
缓存索引
```

如果刚跑完新的仿真，网页可能不会立刻显示最新结果。

应在网页中执行：

```text
重新扫描
后台刷新
增量刷新
刷新索引
```

具体按钮名称可能随版本略有不同，但核心动作是让网页重新扫描项目结果目录。

---

## 9.4 网页端启动仿真

V2 的“运行控制”页通常通过 subprocess 调用：

```text
fdtd_master_controller.py
```

而不是直接 import 或执行某个小脚本模块。

网页端启动后，会在：

```text
结果查看器_html_v2\runtime_state\jobs\job_时间戳_xxxxx\
```

生成任务记录，通常包括：

```text
job_manifest.json
before_snapshot.json
after_snapshot.json
delta_files.json
command.txt
stdout.log
stderr.log
overrides.json
```

这些文件的作用：

| 文件 | 作用 |
|---|---|
| `job_manifest.json` | 记录网页任务元信息 |
| `before_snapshot.json` | 运行前项目状态快照 |
| `after_snapshot.json` | 运行后项目状态快照 |
| `delta_files.json` | 本次任务新增或变化的文件 |
| `command.txt` | 实际执行的命令 |
| `stdout.log` | 标准输出日志 |
| `stderr.log` | 错误输出日志 |
| `overrides.json` | 网页端临时参数覆盖 |

---

# 10. 旧版结果查看器

旧版结果查看器目录是：

```text
H:\FDTD outcome\struct\群论_struct\结果查看器_html
```

启动方式：

```powershell
cd "H:\FDTD outcome\struct\群论_struct\结果查看器_html"
python .\server.py
```

然后打开：

```text
http://127.0.0.1:8787/
```

旧版查看器通常可用于：

```text
浏览结果目录
查看谱图
打开本地文件夹
自动播放 PNG 谱图
重新扫描
基础结果管理
```

建议现在优先用 V2，旧版适合作为备用查看器。

---

# 11. 如何整理旧结果

运行结果整理脚本：

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_results_manager.py" --scan
```

交互式整理：

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_results_manager.py"
```

批量整理全部：

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_results_manager.py" --normalize-all
```

结果整理脚本一般会扫描：

```text
所有母结构下面的 results 文件夹
识别每个扰动目录下的 run_* 仿真结果
整理旧结果
```

常见整理规则：

```text
每个 results\某扰动 目录下保留最新一个 run_*
其他旧 run 移动到旧文件\类型\待考察
无效目录中的内容可能会在整理时清空
不会修改 .fsp 源文件
不会修改 coding 里的仿真脚本
```

使用建议：

```text
正式论文数据确认前，不要轻易清理旧 run
清理前先确认最新 run 是你需要的
重要 run 可以手动复制备份
```

---

# 12. 常见使用场景

## 场景 A：我只是想看看当前有哪些脚本

```powershell
python fdtd_master_controller.py --list
```

看输出中的：

```text
编号
母结构
扰动名
最近 test / full 状态
```

---

## 场景 B：我想先验证某个脚本是否正常

第一步，preview：

```powershell
python fdtd_master_controller.py --ids 12 --mode preview --style sequential
```

第二步，打开：

```text
run_preview_xxx\00_scan_plan\scan_points.csv
```

确认扫描点没问题。

第三步，test：

```powershell
python fdtd_master_controller.py --ids 12 --mode test --style sequential
```

第四步，网页打开 V2，进入：

```text
结果浏览
光谱诊断
质量审计
```

查看 test 结果。

---

## 场景 C：我想跑完整仿真

先确保 test 正常，然后运行：

```powershell
python fdtd_master_controller.py --ids 12 --mode full --style sequential
```

完成后：

```text
打开 V2
刷新索引
进入结果浏览
查看 run_full_xxx
检查 Excel / PNG / manifest / diagnostic
```

---

## 场景 D：我想批量跑某几个脚本

```powershell
python fdtd_master_controller.py --ids 1,3,5-8 --mode test --style sequential
```

如果 test 都通过，再改为：

```powershell
python fdtd_master_controller.py --ids 1,3,5-8 --mode full --style sequential
```

---

## 场景 E：我只想补跑还没有结果的脚本

```powershell
python fdtd_master_controller.py --missing-only --mode test --style sequential
```

或：

```powershell
python fdtd_master_controller.py --missing-only --mode full --style sequential
```

---

## 场景 F：我想临时改扫描范围，但不想改原脚本

交互式运行总控：

```powershell
python fdtd_master_controller.py
```

当出现：

```text
是否在总控中临时覆盖 start/end/step 和 FDTD 运行参数？
```

输入：

```text
y
```

然后只填需要改变的：

```text
start
end
step
```

空白表示不修改。

---

## 场景 G：我想补做某几个异常点

建议流程：

```text
1. 在 V2 中进入质量审计
2. 找到 failed / abnormal / high_T / 缺失 Excel / 缺失 PNG 的点
3. 进入补做实验
4. 选择对应 run 和样本点
5. 生成补做任务包
6. 确认补做任务使用正确母版或工作文件
7. 运行补做
8. 补做结果仍保存到对应 run 或补做目录
9. 回到结果浏览刷新索引
10. 对比补做前后的谱图和 manifest
```

---

# 13. 常见问题与处理

## 问题 1：GitHub 或网页里看不到刚跑完的结果

优先检查：

```text
1. 仿真是否真的完成
2. results\扰动名\run_xxx 是否存在
3. run 目录下是否有 manifest.csv
4. 02_transmission_excel 是否有 xlsx
5. 03_transmission_abs2_png 是否有 png
6. V2 是否点击了重新扫描 / 增量刷新
```

网页缓存不会自动知道所有本地新文件，尤其是刚生成的大量 run，需要刷新索引。

---

## 问题 2：preview 也生成了 run 文件夹，是不是正常？

正常。

当前逻辑下，preview 会生成：

```text
run_preview_*
```

并写入：

```text
scan_points.csv
结构状态说明.md
部分日志
```

但不会执行真实 FDTD 仿真。

---

## 问题 3：为什么有些点没有 Excel 或 PNG？

可能原因：

```text
FDTD 运行失败
T monitor 名称不匹配
没有成功提取 transmission
谱线质量检测失败
自动重试后仍失败
中途被跳过或中断
FDTD 进程被系统或用户关闭
结果目录写入失败
```

检查：

```text
04_logs\manifest.csv
04_logs\retry_history.csv
04_logs\*_diagnostic.json
04_logs\attempt_artifacts\
controller_logs\...\*_stderr.log
```

---

## 问题 4：某个点 max(T)>1，被标为不收敛

可能原因：

```text
仿真时间不足
auto shutoff 没有达到目标
网格过粗
边界条件或 monitor 设置不合理
结构扰动导致数值异常
谱线提取或归一化异常
```

处理建议：

```text
先看是否只是轻微超过 1
查看 autoshutoff_final
查看 simulation_time
查看 mesh accuracy
必要时提高 simulation time
降低 auto shutoff min
提高 mesh accuracy
对关键点使用补做实验重新跑
```

---

## 问题 5：运行时想暂停

当前总控不提供安全暂停 / 恢复正在运行 FDTD 的功能。

按 `p` 时，总控通常只会提示不能外部暂停。

建议：

```text
短时间等待：不要操作
确认卡死：按 s 跳过当前点
整体参数错误：按 q 或 Ctrl+C 退出
```

---

## 问题 6：中途修改了源 FSP，会怎样？

不建议这样做。

可能导致：

```text
当前 run 的母版来源不一致
前后扫描点基准不一致
结果不可比较
源文件 hash 检查失败
后续点无法继续运行
```

正确流程：

```text
先停止仿真
修改源 FSP 或母版
重新 preview
重新 test
最后 full
```

---

## 问题 7：为什么 full 很慢？

可能原因：

```text
扫描点数多
simulation time 较长
mesh accuracy 较高
结构复杂
FDTD 单点仿真本身耗时
磁盘写入大量 FSP / Excel / PNG
License 或 CPU 资源受限
```

建议：

```text
先用 preview 估算点数
用 test 测单点耗时
必要时缩小 start / end / step
优先 sequential
不要盲目 parallel full
```

---

## 问题 8：为什么 CMD 输出很多、不好看？

这是正常的，因为总控和子脚本需要输出：

```text
当前脚本
当前扰动点
FDTD 状态
保存路径
质量检测结果
重试记录
错误信息
```

如果需要更美观，建议通过 V2 工作台查看任务状态；CMD 保留为底层真实日志。

---

# 14. 安全操作建议

正式跑 full 之前，建议始终执行：

```text
preview → test → full
```

每次 full 前检查：

```text
扫描起点 / 终点 / 步长是否合理
点数是否过多
是否选择了正确母结构
扰动对象是否正确
FDTD monitor 是否存在
simulation time 是否足够
auto shutoff min 是否合理
结果目录是否正确
上一次 test 是否成功
磁盘空间是否足够
FDTD License 是否可用
```

不要在 full 运行中：

```text
修改源 FSP
移动 results 目录
清空 runtime_state
关闭 Lumerical License 服务
强制删除正在写入的 run 文件夹
同时运行多个 full 任务
手动改 manifest.csv
手动删除 05_work_fsp 中正在使用的文件
```

建议定期备份：

```text
关键 run_full 结果
源 FSP
重要小脚本
结果查看器 runtime_state
```

---

# 15. 推荐日常工作流

最稳的日常流程是：

```text
1. 打开 PowerShell
2. --list 查看脚本编号
3. --ids N --mode preview 检查扫描计划
4. 打开 run_preview 的 scan_points.csv
5. --ids N --mode test 跑测试点
6. 打开 V2 网页工作台
7. 看 test 谱图、Excel、manifest、质量旗标
8. 没问题后 --ids N --mode full
9. full 完成后在 V2 中刷新索引
10. 在“结果浏览 / 光谱诊断 / 质量审计”中检查数据
11. 对缺失或异常点使用“补做实验”
12. 定期用 fdtd_results_manager.py 整理旧 run
```

---

# 16. 给新用户的一句话版

这个项目不要直接点开某个小脚本乱跑。

正确入口是：

```text
命令行仿真：fdtd_master_controller.py
网页查看与控制：结果查看器_html_v2\server_v2.py
结果归档整理：fdtd_results_manager.py
```

正确顺序是：

```text
先 preview
再 test
最后 full
```

关键数据位置：

```text
每次仿真结果：
results\扰动名\run_模式_时间戳\

总控日志：
controller_logs\controller_run_时间戳\

网页任务记录：
结果查看器_html_v2\runtime_state\jobs\
```

使用原则：

```text
先小范围验证
再正式 full
发现异常先看 manifest 和 diagnostic
网页看结果，CMD 看底层日志
重要结果先备份，再整理
```

---

# 附录 A：推荐命令速查

## 查看脚本列表

```powershell
python fdtd_master_controller.py --list
```

## 预览单个脚本

```powershell
python fdtd_master_controller.py --ids 12 --mode preview --style sequential
```

## 测试单个脚本

```powershell
python fdtd_master_controller.py --ids 12 --mode test --style sequential
```

## 完整运行单个脚本

```powershell
python fdtd_master_controller.py --ids 12 --mode full --style sequential
```

## 批量测试脚本

```powershell
python fdtd_master_controller.py --ids 1,3,5-8 --mode test --style sequential
```

## 只跑缺失脚本

```powershell
python fdtd_master_controller.py --missing-only --mode test --style sequential
```

## 启动 V2 网页工作台

```powershell
python "结果查看器_html_v2\server_v2.py" --root "H:\FDTD outcome\struct\群论_struct" --port 8787
```

## 启动旧版查看器

```powershell
cd "H:\FDTD outcome\struct\群论_struct\结果查看器_html"
python .\server.py
```

## 扫描结果

```powershell
python fdtd_results_manager.py --scan
```

## 整理全部旧结果

```powershell
python fdtd_results_manager.py --normalize-all
```

---

# 附录 B：推荐排查顺序

当结果异常时，按这个顺序排查：

```text
1. 看 controller_logs 中 stderr
2. 看对应 run 的 manifest.csv
3. 看 04_logs\manifest.csv
4. 看 retry_history.csv
5. 看 *_diagnostic.json
6. 看 03_transmission_abs2_png 谱图
7. 看 02_transmission_excel 原始数据
8. 看 05_work_fsp 是否保存完整
9. 看源 FSP 是否被中途修改
10. 看网页 runtime_state\jobs 的 stdout / stderr
```

---

# 附录 C：适合写进 README 的极简版

```text
本项目推荐通过 fdtd_master_controller.py 启动 FDTD 批量仿真，通过结果查看器_html_v2 查看和诊断结果，通过 fdtd_results_manager.py 整理旧结果。

推荐流程：
1. python fdtd_master_controller.py --list
2. python fdtd_master_controller.py --ids N --mode preview --style sequential
3. python fdtd_master_controller.py --ids N --mode test --style sequential
4. python fdtd_master_controller.py --ids N --mode full --style sequential
5. python 结果查看器_html_v2\server_v2.py --root "H:\FDTD outcome\struct\群论_struct" --port 8787

注意：
- full 前必须先 preview 和 test。
- 真实仿真优先 sequential，不建议 parallel full。
- 仿真结果位于 results\扰动名\run_模式_时间戳。
- 总控日志位于 controller_logs。
- 网页任务记录位于 结果查看器_html_v2\runtime_state\jobs。
```
