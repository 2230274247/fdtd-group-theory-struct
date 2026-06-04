# 对角失谐准BIC寻优

此目录存放双环八缝耦合腔的自动搜索脚本。脚本会先保留原始 D4 母版 `.fsp`，然后按候选参数逐个生成结果 `.fsp` 并计算透射谱。

结果批次目录固定为：

```text
results/对角失谐准BIC寻优/run_<mode>_<timestamp>/
  00_scan_plan/
  01_fsp/
  02_transmission_excel/
  03_transmission_abs2_png/
  04_logs/
  05_work_fsp/
```

目标光谱定义为：透射峰向上、峰值足够高、带外透射接近 0、FWHM 很窄。当前脚本的默认判据写在 `TARGETS` 中，后续可以根据已有结果收紧或放宽。
