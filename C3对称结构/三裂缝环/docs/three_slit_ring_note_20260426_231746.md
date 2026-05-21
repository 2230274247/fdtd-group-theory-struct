# C3对称结构 / 三裂缝环

## 对称性类别
C3，旋转 120° 重合

## 几何组成
该母结构由参数化 Si 几何构成，放置在 SiO2 衬底上，使用周期边界形成超表面初扫单元。孔、环、裂缝结构采用 `air` 覆盖对象与 mesh order 近似刻蚀。

## 关键参数
| 参数 | 数值 | 单位 |
|---|---:|---|
| 周期 P | 0.9 | um |
| Si 高度 H | 0.42 | um |
| 衬底厚度 | 1.0 | um |
| 波长范围 | 900 - 1700 | nm |
| 频率采样点 | 501 | points |
| 初始仿真时间 | 1000 | fs |

## source / monitor
- Source：PlaneSource，正入射，沿 -z 方向。
- T monitor：2D Z-normal，位于透射侧，span 覆盖整个周期单元。
- 边界：x/y Periodic，z PML。

## 适合作母版
适合环模与裂缝耦合

## 允许破缺方式
改单裂缝宽度、单裂缝角度

## 初步仿真结果
- 状态：process_failed
- T_peak：None
- lambda_peak_nm：None
- 结果口径：若 T monitor 返回复振幅则取 Abs^2；若返回功率透射率则按功率透射率记录。

## 风险或异常说明
)"\n# "Al (Aluminium) - CRC"\n# "Al (Aluminium) - Palik"\n# "Al2O3 - Palik"\n# "Au (Gold) - CRC"\n# "Au (Gold) - Johnson and Christy"\n# "Au (Gold) - Palik"\n# "C (graphene) - Falkovsky (mid-IR)"\n# "Cr (Chromium) - CRC"\n# "Cr (Chromium) - Palik"\n# "Cu (Copper) - CRC"\n# "Cu (Copper) - Palik"\n# "Fe (Iron) - CRC"\n# "Fe (Iron) - Palik"\n# "GaAs - Palik"\n# "Ge (Germanium) - CRC"\n# "Ge (Germanium) - Palik"\n# "H2O (Water) - Palik"\n# "In (Indium) - Palik"\n# "InAs - Palik"\n# "InP - Palik"\n# "Ni (Nickel) - CRC"\n# "Ni (Nickel) - Palik"\n# "PEC (Perfect Electrical Conductor)"\n# "Pd (Palladium) - Palik"\n# "Pt (Platinum) - Palik"\n# "Rh (Rhodium) - Palik"\n# "Si (Silicon) - Palik"\n# "Si3N4 (Silicon Nitride) - Kischkat"\n# "Si3N4 (Silicon Nitride) - Phillip"\n# "SiO2 (Glass) - Palik"\n# "Sn (Tin) - Palik"\n# "Ta (Tantalum) - CRC"\n# "Ti (Titanium) - CRC"\n# "Ti (Titanium) - Palik"\n# "TiN - Palik"\n# "V (Vanadium ) - CRC"\n# "W (Tungsten) - CRC"\n# "W (Tungsten) - Palik"\n# "etch"'

