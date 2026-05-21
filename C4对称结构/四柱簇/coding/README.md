# 四柱簇自动化扰动脚本说明

本目录为 `H:\FDTD outcome\struct\群论_struct\C4对称结构\四柱簇` 生成四类 FDTD 自动化扫描脚本。

## 已确认的母版结构参数

- 源文件：`fsp\four_pillar_cluster_CodexAstra_20260426_232913.fsp`
- Si 柱：4 个 `Si_pillar`
- 柱中心：右 `(200 nm, 0)`、上 `(0, 200 nm)`、左 `(-200 nm, 0)`、下 `(0, -200 nm)`
- 柱半径：`95 nm`
- 柱厚度：`420 nm`
- 衬底：`SiO2_substrate`，`900 nm x 900 nm`，厚度 `1000 nm`
- FDTD 区域：`900 nm x 900 nm`，当前母版仿真时间 `50 ps`
- 透射监视器：`T`

## 通用运行方式

每个扰动文件夹内都有一个 `run_fdtd_*.py` 脚本。直接运行脚本时会提示：

- `1`：测试模式，只真实仿真前 3 个点；
- `2`：完整真实仿真；
- `3`：预览模式，只生成扫描计划和结构说明，不运行 FDTD。

也可以在命令行加参数：

```powershell
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "脚本路径.py" --preview
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "脚本路径.py" --test
"D:\Program Files\Lumerical\v202\python-3.6.8-embed-amd64\python.exe" "脚本路径.py" --full
```

## 源文件保护

脚本不会修改 `fsp` 文件夹内的源 `.fsp`。每次运行会先复制出 `results\扰动名\run_模式_时间戳\05_work_fsp\master_template.fsp`，每个扫描点再从这个母版复制出单点工作副本。

## 输出内容

每个真实仿真点会保存：

- 单点 `.fsp` 文件；
- 透射谱 `|T|^2` 图片；
- 透射谱 Excel 源数据；
- `scan_points.csv`；
- `manifest.csv`；
- `结构状态说明.md`。

运行过程中会实时输出当前参数、剩余点数、单点耗时、预计剩余时间、最大/最小 `|T|^2` 及对应波长。
