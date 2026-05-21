# FDTD 结果整理脚本说明

脚本位置：

```text
H:\FDTD outcome\struct\群论_struct\fdtd_results_manager.py
```

## 它做什么

这个脚本会扫描所有母结构下面的 `results` 文件夹，识别每个扰动目录下的 `run_*` 仿真结果，并帮助你整理旧结果。

整理后的目标结构是：

```text
某母结构\results\某扰动\
    run_xxx_时间戳\          # 当前保留的最新一次结果
    旧文件\
        test\
            良好\
            待考察\
            无效\
        full\
            良好\
            待考察\
            无效\
        preview\
            良好\
            待考察\
            无效\
        unknown\
            良好\
            待考察\
            无效\
```

你主要使用 `test` 和 `full`。`preview` 与 `unknown` 是兜底分类，用来避免早期脚本或预览结果被误删。

## 推荐使用方式

先只扫描：

```text
D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe fdtd_results_manager.py --scan
```

交互式运行：

```text
D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe fdtd_results_manager.py
```

批量整理全部：

```text
D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe fdtd_results_manager.py --normalize-all
```

## 整理规则

- 每个 `results\某扰动` 目录下，默认只保留最新的一个 `run_*`。
- 其他旧 `run_*` 会移动到 `旧文件\类型\待考察`。
- 你看完 `待考察` 后，可以手动移动到 `良好` 或 `无效`。
- 每次运行脚本时，`无效` 里的内容会被自动清空。
- 脚本不会修改任何 `.fsp` 源文件，也不会修改 `coding` 里的仿真脚本。
