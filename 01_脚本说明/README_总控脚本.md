# FDTD 自动化脚本总控说明

总控脚本路径：

`H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py`

## 它能做什么

运行总控脚本后，它会自动扫描：

`H:\FDTD outcome\struct\群论_struct\**\coding\**\run_*.py`

然后按下面层级输出可运行脚本：

`对称类别 / 母结构 / 扰动名称 / 脚本编号`

列表中还会显示该扰动是否已经有最近一次：

- `test` 测试仿真结果；
- `full` 完整仿真结果。

你可以选择：

- 运行单个脚本；
- 按编号运行多个脚本，例如 `1,3,5-8`；
- 运行某个母结构下的所有脚本；
- 运行当前已发现的全部脚本；
- 只查看列表，不运行。

## 推荐运行命令

建议用 Lumerical 自带 Python 运行：

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py"
```

只查看当前有哪些脚本：

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --list
```

直接预览编号 1 到 5 的脚本：

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --ids 1-5 --mode preview --style sequential
```

直接测试全部脚本：

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "H:\FDTD outcome\struct\群论_struct\fdtd_master_controller.py" --all --mode test --style sequential
```

## 运行模式

总控会把模式传给每个子脚本：

- `preview`：只生成扫描计划，不运行真实仿真；
- `test`：每个脚本只真实仿真前几个测试点；
- `full`：完整真实仿真；
- `ask`：让子脚本自己询问。

真实仿真建议用 `sequential` 依次运行。`parallel` 并行模式更适合 `preview`，因为多个 FDTD 同时跑会非常占 CPU/内存/License。

## 运行前审阅清单

在真正启动子脚本之前，总控会先输出一份中文审阅清单，然后再次要求你输入 `YES` 才开始。

审阅报告包括：

- 该脚本最近一次 `test` 和 `full` 结果；
- 脚本路径；
- 对用户主要修改区的中文解释；
- 本次到底改变哪个对象；
- 起始值、终止值、步长、目标扫描点数；
- 自动步长和自动截断会怎样影响实际扫描；
- 安全边界如何避免结构相交或贴边；
- 仿真时间、测试点数、最小收敛阈值。

审阅报告不会把脚本代码原样贴出来。长度会统一换算成 `um`，例如脚本内的 `120 nm` 会显示为 `0.12 um`，脚本内的 `5e-11 s` 会显示为 `50 ps`。

优先级理解：

- 高优先级：扰动对象、半径、宽度、长度、偏移、角度、扫描起点和终点；
- 中优先级：自动步长、目标点数、安全间隔、边界留白；
- 低优先级：运行模式、测试点数、仿真时间、收敛阈值。

如果你看到参数不合适，可以不要输入 `YES`，先去对应脚本顶部的“用户主要修改区”修改，然后重新运行总控。

## 日志在哪里

总控自己的日志会放在：

`H:\FDTD outcome\struct\群论_struct\controller_logs\master_run_时间戳\`

每个子脚本会有单独的：

- `*_stdout.log`
- `*_stderr.log`
- `master_run_summary.csv`

子脚本自己的仿真结果仍然按原规则放在各自母结构的：

`results\扰动名\run_模式_时间戳\`

## 后续如何添加新脚本

后续你只要按这个结构放脚本，总控就会自动发现，不需要修改总控：

```text
群论_struct
└─ 某对称结构
   └─ 某母结构
      ├─ fsp
      │  └─ 母版.fsp
      ├─ coding
      │  └─ 某扰动名称
      │     ├─ run_fdtd_xxx_sweep.py
      │     └─ README.md
      └─ results
```

总控只识别文件名以 `run_` 开头、扩展名为 `.py` 的脚本。公共模块如 `xxx_common.py` 不会被当成可运行脚本。

## 我建议的产品化改进

现在这个总控是“命令行批处理中心”。如果后续脚本数量继续增长，我建议再加一个 `script_registry.csv` 或 `script_registry.json`，让每个脚本可以声明：

- 推荐运行模式；
- 预计单点仿真时间；
- 扫描点数；
- 是否适合并行；
- 需要的 License 数量；
- 扰动降群路径；
- 当前脚本成熟度：草稿 / 已预览 / 已测试 / 可全跑。

这样总控不只是“能调用”，还可以在你运行前自动估算总耗时、筛掉不适合并行的脚本，并生成一个实验批次计划。等你的脚本数量超过 30 个时，这个注册表会非常有用。
