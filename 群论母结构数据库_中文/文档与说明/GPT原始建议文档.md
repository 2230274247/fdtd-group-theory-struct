# 基于群论对称性的母结构数据库建设说明文档

> 适用方向：光子结构、GMR / quasi-BIC / Fano 共振、高 Q 窄线宽滤波器、基于目标光谱的逆向设计。  
> 适用场景：你已经按对称性构建好一批母结构，希望后续系统记录“母结构—扰动方式—几何参数—仿真光谱—逆向设计目标”之间的关系。

---

## 0. 本文档的目的

本文档用于指导后续建立一套可复用的结构数据库，而不是简单记录几张结构图。  
核心目标是把每一个光子结构样本记录成一个可分析、可检索、可统计、可训练神经网络的数据点。

后续可以利用 Codex 或 Python 根据本文档自动生成：

1. Excel 模板；
2. CSV 表格；
3. JSON 数据结构；
4. FDTD 参数扫描脚本；
5. 光谱指标提取脚本；
6. 结构样本说明文档。

数据库的核心思想是：

```text
高对称母结构
    ↓
按群论思想分类，例如 C2、C3、C4、C6
    ↓
施加可控微扰，例如形变、位移、挖孔、开槽
    ↓
得到降群路径，例如 C4 → C2、C4 → C1、C2 → C1
    ↓
仿真得到光谱响应
    ↓
分析峰位、FWHM、Q 值、透过率与扰动强度之间的关系
    ↓
建立结构特征到光谱响应的映射
    ↓
服务于目标光谱反推结构参数的逆向设计
```

---

## 1. 为什么不能只建一张表？

不建议只建立一张大表。原因是“母结构”和“仿真样本”不是同一层级。

例如，“C4 十字结构”是一个母结构家族；而“周期 500 nm、厚度 180 nm、横臂 240 nm、竖臂 216 nm、扰动强度 0.10 的十字结构”才是一个具体仿真样本。

因此建议至少建立以下 4 张核心表：

| 表名 | 推荐文件名 | 作用 |
|---|---|---|
| 母结构表 | `mother_structures.csv` | 记录所有高对称母结构的基本信息 |
| 扰动规则表 | `perturbation_rules.csv` | 记录每类母结构可以怎么变形、怎么破缺对称性 |
| 仿真样本表 | `simulation_samples.csv` | 记录每一次具体 FDTD 仿真的输入参数 |
| 光谱结果表 | `spectrum_metrics.csv` | 记录每个样本仿真后提取出的峰位、FWHM、Q 值等结果 |

后续可扩展 2 张辅助表：

| 表名 | 推荐文件名 | 作用 |
|---|---|---|
| 文件索引表 | `file_index.csv` | 记录 `.fsp`、光谱 `.txt`、场图 `.png` 等文件路径 |
| 目标筛选表 | `inverse_targets.csv` | 记录逆向设计目标和候选结构筛选结果 |

---

## 2. 推荐文件夹结构

建议在一个总项目文件夹下建立如下目录。

```text
symmetry_structure_database/
│
├─ 00_docs/
│  ├─ database_schema.md
│  ├─ perturbation_definition.md
│  └─ naming_rules.md
│
├─ 01_tables/
│  ├─ mother_structures.csv
│  ├─ perturbation_rules.csv
│  ├─ simulation_samples.csv
│  ├─ spectrum_metrics.csv
│  ├─ file_index.csv
│  └─ inverse_targets.csv
│
├─ 02_fdtd_models/
│  ├─ C2_dimer/
│  ├─ C4_cross/
│  └─ C4_square_ring/
│
├─ 03_spectra_txt/
│  ├─ C2_dimer/
│  ├─ C4_cross/
│  └─ C4_square_ring/
│
├─ 04_field_images/
│  ├─ E_field/
│  ├─ H_field/
│  └─ mode_profiles/
│
├─ 05_scripts/
│  ├─ generate_sample_table.py
│  ├─ extract_spectrum_metrics.py
│  ├─ plot_delta_Q.py
│  └─ fdtd_batch_run_template.py
│
└─ 06_outputs/
   ├─ figures/
   ├─ selected_candidates/
   └─ reports/
```

---

## 3. 命名规则

所有样本必须有唯一编号。建议采用以下格式：

```text
对称性_母结构_扰动类型_编号
```

例如：

```text
C2_dimer_radiusdiff_0001
C4_cross_LxLy_0007
C4_square_ring_holeoffset_0012
C6_hole_ring_singlehole_0005
```

推荐字段：

| 字段 | 示例 | 含义 |
|---|---|---|
| `sample_id` | `C4_cross_LxLy_0007` | 具体样本编号 |
| `family_id` | `C4_cross` | 母结构家族编号 |
| `structure_name` | `十字` | 中文结构名称 |
| `perturb_type` | `arm_length_difference` | 扰动方式 |
| `index` | `0007` | 样本序号 |

命名规则的目的：保证 `.fsp` 文件、光谱文件、场图文件、Excel/CSV 数据行可以一一对应。

---

# 4. 表 1：母结构表 `mother_structures.csv`

## 4.1 这张表记录什么？

母结构表记录的是“高对称起点”。每一行是一类母结构，而不是一次具体仿真。

例如：

```text
C2 双柱
C4 十字
C4 方环
C6 六孔环
近径向圆环
```

## 4.2 推荐字段

| 字段名 | 类型 | 是否必填 | 示例 | 含义 |
|---|---|---:|---|---|
| `family_id` | string | 是 | `C4_cross` | 母结构家族编号 |
| `structure_name_cn` | string | 是 | `十字` | 中文名称 |
| `structure_name_en` | string | 否 | `cross resonator` | 英文名称 |
| `base_group` | string | 是 | `C4` | 母结构原始旋转对称群 |
| `symmetry_order` | int | 是 | `4` | 旋转阶数，C4 对应 4 |
| `lattice_type` | string | 是 | `square` | 周期晶格类型 |
| `geometry_type` | string | 是 | `solid_cross` | 几何类别 |
| `recommended_priority` | int | 是 | `1` | 推荐优先级，1 最高 |
| `recommended_use` | string | 是 | `quasi-BIC / Fano / high-Q` | 推荐用途 |
| `main_parameters` | string | 是 | `period_p, Lx, Ly, W, h` | 主要几何参数 |
| `possible_perturbations` | string | 是 | `arm_length_difference; single_arm_change` | 可用扰动方式 |
| `notes` | string | 否 | `适合研究 C4→C2→C1 降群路径` | 备注 |

## 4.3 字段解释

### `family_id`

母结构家族的唯一编号。程序、表格、文件夹都使用这个编号。

示例：

```text
C2_dimer
C4_cross
C4_square_ring
C6_hole_ring
radial_ring
```

为什么需要：后续要统计“哪一类母结构更容易产生窄线宽共振”，必须依赖这个字段分组。

---

### `base_group`

表示母结构在未扰动时的旋转对称性。

常用取值：

| `base_group` | 含义 |
|---|---|
| `C1` | 无非平凡旋转对称性 |
| `C2` | 旋转 180° 后重合 |
| `C3` | 旋转 120° 后重合 |
| `C4` | 旋转 90° 后重合 |
| `C6` | 旋转 60° 后重合 |
| `Cinf_approx` | 近似连续旋转对称，例如圆盘、圆环 |

判断方法：

```text
绕结构中心旋转多少度后，结构第一次与自身重合？
```

- 180°：C2；
- 120°：C3；
- 90°：C4；
- 60°：C6。

---

### `symmetry_order`

把 Cn 转成数字 n，便于后续数据分析或机器学习。

| 群 | `symmetry_order` |
|---|---:|
| C1 | 1 |
| C2 | 2 |
| C3 | 3 |
| C4 | 4 |
| C6 | 6 |

如果后续训练神经网络，更推荐对 `base_group` 做 one-hot 编码，而不是直接把 C4 当成数字 4 使用。因为数字 4 不一定代表它与 C2 的关系是简单线性的。

---

## 4.4 示例

| family_id | structure_name_cn | base_group | symmetry_order | lattice_type | recommended_priority | main_parameters | possible_perturbations | notes |
|---|---|---|---:|---|---:|---|---|---|
| C2_dimer | 双柱 | C2 | 2 | square | 1 | period_p, r1, r2, gap, h | radius_difference; position_shift | 最适合第一阶段验证 C2→C1 |
| C4_cross | 十字 | C4 | 4 | square | 1 | period_p, Lx, Ly, Wx, Wy, h | arm_length_difference; single_arm_change | 适合研究 C4→C2→C1 |
| C4_square_ring | 方环 | C4 | 4 | square | 2 | outer_L, inner_L, ring_width, h | hole_offset; single_slot | 适合孔偏心和开槽扰动 |
| C6_hole_ring | 六孔环 | C6 | 6 | hexagonal | 3 | ring_R, hole_r, h | single_hole_change; hole_shift | 后续扩展使用 |

---

# 5. 表 2：扰动规则表 `perturbation_rules.csv`

## 5.1 这张表记录什么？

扰动规则表记录每类母结构可以怎么改变、改变后对称性如何降低、扰动强度如何定义。

这张表是整个数据库中最能体现“群论思想”的部分。

## 5.2 推荐字段

| 字段名 | 类型 | 是否必填 | 示例 | 含义 |
|---|---|---:|---|---|
| `rule_id` | string | 是 | `C4_cross_LxLy` | 扰动规则编号 |
| `family_id` | string | 是 | `C4_cross` | 对应母结构 |
| `perturb_type` | string | 是 | `arm_length_difference` | 扰动类型 |
| `perturb_target` | string | 是 | `横臂/竖臂` | 具体改变对象 |
| `base_group` | string | 是 | `C4` | 扰动前对称性 |
| `perturbed_group` | string | 是 | `C2` | 扰动后对称性 |
| `symmetry_path` | string | 是 | `C4->C2` | 降群路径 |
| `delta_definition` | string | 是 | `(Lx-Ly)/L0` | 归一化扰动强度定义 |
| `delta_abs_definition` | string | 是 | `abs(Lx-Ly)` | 绝对扰动量定义 |
| `recommended_delta_values` | string | 是 | `0,0.02,0.04,0.06,0.08,0.10,0.12` | 推荐扰动强度 |
| `fixed_parameters` | string | 是 | `period_p,h,material` | 扰动扫描时固定的参数 |
| `changed_parameters` | string | 是 | `Lx,Ly` | 扰动扫描时改变的参数 |
| `physical_expectation` | string | 否 | `扰动增强时 Q 值下降，FWHM 变宽` | 预期物理趋势 |
| `notes` | string | 否 | `先只改变一种扰动，不要混合扰动` | 备注 |

---

## 5.3 关键字段解释

### `perturb_type`

表示采用哪一种破缺方式。

常见取值：

| `perturb_type` | 中文含义 | 典型结构 |
|---|---|---|
| `radius_difference` | 半径差 | C2 双柱、四柱簇 |
| `position_shift` | 位置偏移 | 双柱、孔阵列 |
| `arm_length_difference` | 臂长差 | C4 十字 |
| `arm_width_difference` | 臂宽差 | C4 十字、双梁 |
| `hole_offset` | 孔偏心 | 方环、圆盘挖孔 |
| `single_hole_change` | 单孔尺寸变化 | 四孔方块、六孔环 |
| `single_slot` | 单裂缝开槽 | 方环、圆环 |
| `rotation_angle_difference` | 转角差 | 双椭圆、旋转柱结构 |

---

### `perturbed_group`

表示扰动后结构剩余的旋转对称性。

示例：

| 母结构 | 扰动方式 | 扰动前 | 扰动后 |
|---|---|---|---|
| C2 双柱 | 左右半径不同 | C2 | C1 |
| C4 十字 | 横臂与竖臂长度不同，但上下左右仍成对 | C4 | C2 |
| C4 十字 | 只改变一个臂 | C4 | C1 |
| C6 六孔环 | 三个隔位孔一起变化 | C6 | C3 |
| C6 六孔环 | 只改变一个孔 | C6 | C1 |

---

### `symmetry_path`

降群路径。格式统一写成：

```text
C4->C2
C4->C1
C2->C1
C6->C3
C6->C2
C6->C1
```

为什么重要：后续可以按降群路径统计平均 Q 值、最小 FWHM、最大透过率，从而判断哪一种对称性破缺路径最适合目标光谱。

---

### `delta_definition`

归一化扰动强度的定义。建议所有扰动都定义一个无量纲的 `delta`。

常见定义：

#### 双柱半径差

```text
母结构：r1 = r2 = r0
扰动后：r1 ≠ r2

delta = (r1 - r2) / r0
```

#### 十字横竖臂长度差

```text
母结构：Lx = Ly = L0
扰动后：Lx ≠ Ly

delta = (Lx - Ly) / L0
```

#### 方环内孔偏心

```text
母结构：内孔位于中心
扰动后：内孔偏移距离 d

delta = d / period_p
```

#### 单孔尺寸变化

```text
母结构：所有孔半径为 r0
扰动后：其中一个孔半径为 ri

delta = (ri - r0) / r0
```

为什么需要：不同结构的实际尺寸不同，但 `delta` 是归一化量，可以用来比较不同结构的对称性破缺强弱。

---

## 5.4 示例

| rule_id | family_id | perturb_type | perturb_target | base_group | perturbed_group | symmetry_path | delta_definition | recommended_delta_values | physical_expectation |
|---|---|---|---|---|---|---|---|---|---|
| C2_dimer_radius | C2_dimer | radius_difference | 左右柱半径 | C2 | C1 | C2->C1 | `(r1-r2)/r0` | `0,0.02,0.04,0.06,0.08,0.10,0.12` | delta 增大时辐射泄露增强，Q 下降 |
| C4_cross_LxLy | C4_cross | arm_length_difference | 横臂/竖臂 | C4 | C2 | C4->C2 | `(Lx-Ly)/L0` | `0,0.02,0.04,0.06,0.08,0.10,0.12` | 可研究 C4→C2 降群 |
| C4_cross_single_arm | C4_cross | single_arm_change | 单个臂 | C4 | C1 | C4->C1 | `(L_top-L0)/L0` | `0,0.02,0.04,0.06,0.08,0.10` | 完全破坏 C4 对称性 |
| C4_square_ring_holeoffset | C4_square_ring | hole_offset | 内孔中心 | C4 | C2/C1 | C4->C2 or C4->C1 | `d/period_p` | `0,0.02,0.04,0.06,0.08,0.10` | 孔偏移改变模态泄露通道 |

---

# 6. 表 3：仿真样本表 `simulation_samples.csv`

## 6.1 这张表记录什么？

仿真样本表记录每一次具体 FDTD 仿真的输入参数。每一行对应一个实际仿真的结构。

这张表的作用是：

```text
告诉你这个样本是什么结构、用了什么参数、属于什么扰动、怎么复现这个样本。
```

## 6.2 推荐字段

| 字段名 | 类型 | 是否必填 | 示例 | 含义 |
|---|---|---:|---|---|
| `sample_id` | string | 是 | `C4_cross_LxLy_0005` | 样本编号 |
| `family_id` | string | 是 | `C4_cross` | 母结构家族 |
| `rule_id` | string | 是 | `C4_cross_LxLy` | 扰动规则 |
| `structure_name_cn` | string | 是 | `十字` | 中文名称 |
| `base_group` | string | 是 | `C4` | 扰动前对称性 |
| `perturbed_group` | string | 是 | `C2` | 扰动后对称性 |
| `symmetry_path` | string | 是 | `C4->C2` | 降群路径 |
| `period_p_nm` | float | 是 | `500` | 周期，单位 nm |
| `thickness_h_nm` | float | 是 | `180` | 结构厚度，单位 nm |
| `material_resonator` | string | 是 | `TiO2` | 结构主体材料 |
| `material_substrate` | string | 是 | `SiO2` | 衬底材料 |
| `material_background` | string | 是 | `air` | 背景材料 |
| `lattice_type` | string | 是 | `square` | 晶格类型 |
| `perturb_type` | string | 是 | `arm_length_difference` | 扰动类型 |
| `perturb_target` | string | 是 | `横臂/竖臂` | 扰动对象 |
| `delta` | float | 是 | `0.10` | 归一化扰动强度 |
| `delta_abs_nm` | float | 是 | `24` | 实际扰动量，单位 nm |
| `geometry_params_json` | string | 是 | `{"Lx":240,"Ly":216,"W":60}` | 具体几何参数 |
| `wavelength_min_nm` | float | 是 | `400` | 起始波长 |
| `wavelength_max_nm` | float | 是 | `900` | 终止波长 |
| `polarization` | string | 是 | `Ex` | 入射偏振 |
| `boundary_x` | string | 是 | `periodic` | x 方向边界 |
| `boundary_y` | string | 是 | `periodic` | y 方向边界 |
| `boundary_z` | string | 是 | `PML` | z 方向边界 |
| `mesh_size_nm` | float | 否 | `2` | 网格尺寸 |
| `monitor_name` | string | 是 | `Trans` | 透射监视器名称 |
| `run_status` | string | 是 | `planned/finished/failed` | 仿真状态 |
| `notes` | string | 否 | `峰较弱，需要复查` | 备注 |

---

## 6.3 几何参数如何记录？

建议采用两种方式之一。

### 方法 A：所有常见参数都拆成列

适合 Excel 初期使用。

例如：

```text
r1_nm, r2_nm, gap_nm, Lx_nm, Ly_nm, Wx_nm, Wy_nm, outer_L_nm, inner_L_nm, hole_r_nm, hole_x_nm, hole_y_nm
```

优点：直观，适合手动检查。  
缺点：不同结构用不到的字段很多，会出现大量空白。

### 方法 B：用 `geometry_params_json` 记录结构参数

适合 Python / Codex 后续处理。

例如 C4 十字：

```json
{"period_p": 500, "h": 180, "Lx": 240, "Ly": 216, "Wx": 60, "Wy": 60}
```

例如 C2 双柱：

```json
{"period_p": 500, "h": 180, "r1": 60, "r2": 54, "gap": 80}
```

例如 C4 方环：

```json
{"period_p": 500, "h": 180, "outer_L": 260, "inner_L": 120, "hole_dx": 20, "hole_dy": 0}
```

建议：初期可以同时保留常见拆分字段和 `geometry_params_json`。这样既方便人工阅读，也方便程序调用。

---

## 6.4 示例

| sample_id | family_id | rule_id | base_group | perturbed_group | symmetry_path | period_p_nm | thickness_h_nm | perturb_type | delta | delta_abs_nm | geometry_params_json | polarization | monitor_name | run_status |
|---|---|---|---|---|---|---:|---:|---|---:|---:|---|---|---|---|
| C4_cross_LxLy_0005 | C4_cross | C4_cross_LxLy | C4 | C2 | C4->C2 | 500 | 180 | arm_length_difference | 0.10 | 24 | `{"Lx":240,"Ly":216,"Wx":60,"Wy":60}` | Ex | Trans | finished |

---

# 7. 表 4：光谱结果表 `spectrum_metrics.csv`

## 7.1 这张表记录什么？

光谱结果表记录每个仿真样本运行后提取出的结果。每一行对应一个 `sample_id`。

核心指标包括：

```text
峰位 lambda_peak
峰值透过率 T_peak
谷值透过率 T_min
半峰宽 FWHM
品质因子 Q
峰数量 num_peaks
Fano 参数
```

## 7.2 推荐字段

| 字段名 | 类型 | 是否必填 | 示例 | 含义 |
|---|---|---:|---|---|
| `sample_id` | string | 是 | `C4_cross_LxLy_0005` | 样本编号 |
| `lambda_peak_nm` | float | 是 | `612` | 共振峰位 |
| `T_peak` | float | 是 | `0.76` | 峰值透过率 |
| `lambda_dip_nm` | float | 否 | `605` | 透射谷位置 |
| `T_min` | float | 否 | `0.08` | 谷值透过率 |
| `FWHM_nm` | float | 是 | `8.4` | 半峰宽 |
| `Q_factor` | float | 是 | `72.9` | 品质因子 |
| `num_peaks` | int | 是 | `1` | 光谱中主要峰数量 |
| `sideband_T_left` | float | 否 | `0.12` | 左侧边带透过率 |
| `sideband_T_right` | float | 否 | `0.09` | 右侧边带透过率 |
| `sideband_T_max` | float | 否 | `0.12` | 最大边带透过率 |
| `fano_q` | float | 否 | `20` | Fano 非对称参数 |
| `fit_MSE` | float | 否 | `0.0018` | 目标函数拟合误差 |
| `spectrum_quality` | string | 是 | `good/weak/multi_peak/noisy` | 光谱质量评价 |
| `notes` | string | 否 | `单峰明显，线宽较窄` | 备注 |

---

## 7.3 指标解释

### `lambda_peak_nm`

共振峰所在波长。逆向设计中最基本的目标变量。

例如：如果目标是 610 nm 窄带透射峰，则首先筛选：

```text
abs(lambda_peak_nm - 610) < 5
```

---

### `T_peak`

峰值透过率。用于判断该共振峰是否足够明显。

例如：

```text
T_peak > 0.7
```

表示希望峰值透过率大于 70%。

---

### `FWHM_nm`

半峰宽，是窄线宽设计的核心指标。

对于透射峰，如果背景透过率接近 0，可以近似定义：

```text
T_half = T_peak / 2
FWHM = lambda_right_half - lambda_left_half
```

如果背景不为 0，建议使用：

```text
T_half = T_base + (T_peak - T_base) / 2
FWHM = lambda_right_half - lambda_left_half
```

---

### `Q_factor`

品质因子，定义为：

```text
Q_factor = lambda_peak_nm / FWHM_nm
```

例如：

```text
lambda_peak_nm = 612
FWHM_nm = 8.4
Q_factor = 612 / 8.4 = 72.86
```

为什么重要：FWHM 是绝对线宽，Q 值是归一化线宽指标，更适合比较不同波段的共振尖锐程度。

---

### `num_peaks`

光谱范围内主要峰的数量。建议优先保留单峰明显的结构。

取值建议：

```text
1：单峰结构，优先保留
2：双峰结构，需要进一步判断
>=3：多峰结构，可能不适合作为简单窄带滤波器
```

---

### `fano_q`

如果光谱呈现明显非对称线型，可以用 Fano 函数拟合，记录非对称参数 q。

该字段后续可以用于分析：

```text
哪一种对称性破缺方式更容易产生强 Fano 非对称线型？
```

---

## 7.4 示例

| sample_id | lambda_peak_nm | T_peak | T_min | FWHM_nm | Q_factor | num_peaks | sideband_T_max | fano_q | spectrum_quality | notes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| C4_cross_LxLy_0005 | 612 | 0.76 | 0.08 | 8.4 | 72.9 | 1 | 0.12 | 18.6 | good | 单峰明显，适合保留 |

---

# 8. 表 5：文件索引表 `file_index.csv`

## 8.1 这张表记录什么？

文件索引表用于管理所有与样本对应的文件路径。

每个样本至少应该保存：

1. `.fsp` 模型文件；
2. `.txt` 光谱文件；
3. `.png` 电场图；
4. `.png` 磁场图或模式图。

## 8.2 推荐字段

| 字段名 | 类型 | 是否必填 | 示例 | 含义 |
|---|---|---:|---|---|
| `sample_id` | string | 是 | `C4_cross_LxLy_0005` | 样本编号 |
| `fsp_path` | string | 是 | `02_fdtd_models/C4_cross/C4_cross_LxLy_0005.fsp` | FDTD 模型路径 |
| `spectrum_path` | string | 是 | `03_spectra_txt/C4_cross/C4_cross_LxLy_0005_T.txt` | 光谱 TXT 文件路径 |
| `E_field_path` | string | 否 | `04_field_images/E_field/C4_cross_LxLy_0005_E.png` | 电场图路径 |
| `H_field_path` | string | 否 | `04_field_images/H_field/C4_cross_LxLy_0005_H.png` | 磁场图路径 |
| `mode_profile_path` | string | 否 | `04_field_images/mode_profiles/C4_cross_LxLy_0005_mode.png` | 模式图路径 |
| `script_path` | string | 否 | `05_scripts/run_C4_cross.py` | 生成该样本的脚本路径 |
| `created_time` | string | 否 | `2026-04-xx` | 创建时间 |
| `verified` | string | 是 | `yes/no` | 是否检查过文件有效性 |
| `notes` | string | 否 | `需要加密网格复算` | 备注 |

---

# 9. 表 6：逆向设计目标表 `inverse_targets.csv`

## 9.1 这张表记录什么？

该表用于记录你希望实现的目标光谱，以及哪些结构样本满足该目标。

## 9.2 推荐字段

| 字段名 | 类型 | 是否必填 | 示例 | 含义 |
|---|---|---:|---|---|
| `target_id` | string | 是 | `target_610nm_highT_narrow` | 目标编号 |
| `target_type` | string | 是 | `peak` | 目标类型：峰或谷 |
| `target_lambda_nm` | float | 是 | `610` | 目标波长 |
| `lambda_tolerance_nm` | float | 是 | `5` | 波长容差 |
| `target_FWHM_max_nm` | float | 是 | `10` | 最大允许半峰宽 |
| `target_T_peak_min` | float | 否 | `0.7` | 最小峰值透过率 |
| `target_T_min_max` | float | 否 | `0.1` | 最大谷值透过率 |
| `preferred_symmetry_path` | string | 否 | `C4->C2` | 优先考虑的降群路径 |
| `candidate_sample_id` | string | 否 | `C4_cross_LxLy_0005` | 候选样本 |
| `inverse_loss` | float | 否 | `0.0018` | 与目标光谱的误差 |
| `success_flag` | int | 是 | `1` | 是否满足目标 |
| `notes` | string | 否 | `候选结构峰值较高，边带较低` | 备注 |

---

## 9.3 示例筛选规则

如果目标是：

```text
610 nm 附近高透过率窄峰
```

可以设置：

```text
abs(lambda_peak_nm - 610) <= 5
FWHM_nm <= 10
T_peak >= 0.7
num_peaks == 1
```

如果目标是：

```text
610 nm 附近低透过率窄谷
```

可以设置：

```text
abs(lambda_dip_nm - 610) <= 5
FWHM_nm <= 10
T_min <= 0.1
```

---

# 10. 第一阶段推荐实验路线

不要一开始把所有母结构全部仿真。建议先选择 3 个结构家族，建立第一版小规模数据库。

推荐优先级：

| 优先级 | 母结构 | 原始对称性 | 推荐扰动 | 降群路径 | 原因 |
|---:|---|---|---|---|---|
| 1 | 双柱 | C2 | 左右半径差 | C2→C1 | 最简单，参数少，容易验证 |
| 1 | 十字 | C4 | 横臂/竖臂长度差 | C4→C2 | 最适合体现群论降群思想 |
| 2 | 方环 | C4 | 内孔偏心 | C4→C2 或 C4→C1 | 适合研究孔偏心和环形模态 |

每个结构先设置 7 个扰动强度：

```text
0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12
```

其中：

```text
delta = 0
```

表示未扰动的高对称母结构。

---

# 11. 每种结构的推荐记录方式

## 11.1 C2 双柱结构

### 母结构参数

| 参数 | 含义 |
|---|---|
| `period_p_nm` | 周期 |
| `r0_nm` | 母结构柱半径 |
| `gap_nm` | 两柱间隙 |
| `thickness_h_nm` | 厚度 |
| `material_resonator` | 柱材料 |
| `material_substrate` | 衬底材料 |

### 推荐扰动

| 扰动 | 公式 | 降群路径 |
|---|---|---|
| 左右半径差 | `delta = (r1-r2)/r0` | C2→C1 |
| 左右位置差 | `delta = dx/period_p` | C2→C1 |

### 示例 JSON

```json
{"period_p": 500, "h": 180, "r1": 60, "r2": 54, "gap": 80}
```

---

## 11.2 C4 十字结构

### 母结构参数

| 参数 | 含义 |
|---|---|
| `period_p_nm` | 周期 |
| `L0_nm` | 母结构臂长 |
| `W0_nm` | 母结构臂宽 |
| `thickness_h_nm` | 厚度 |
| `material_resonator` | 结构材料 |
| `material_substrate` | 衬底材料 |

### 推荐扰动

| 扰动 | 公式 | 降群路径 |
|---|---|---|
| 横臂/竖臂长度差 | `delta = (Lx-Ly)/L0` | C4→C2 |
| 横臂/竖臂宽度差 | `delta = (Wx-Wy)/W0` | C4→C2 |
| 单个臂长度变化 | `delta = (L_top-L0)/L0` | C4→C1 |

### 示例 JSON

```json
{"period_p": 500, "h": 180, "Lx": 240, "Ly": 216, "Wx": 60, "Wy": 60}
```

---

## 11.3 C4 方环结构

### 母结构参数

| 参数 | 含义 |
|---|---|
| `period_p_nm` | 周期 |
| `outer_L_nm` | 外方形边长 |
| `inner_L_nm` | 内孔边长 |
| `ring_width_nm` | 环宽 |
| `thickness_h_nm` | 厚度 |
| `material_resonator` | 结构材料 |
| `material_substrate` | 衬底材料 |

### 推荐扰动

| 扰动 | 公式 | 降群路径 |
|---|---|---|
| 内孔沿 x 方向偏心 | `delta = dx/period_p` | C4→C2 |
| 内孔沿任意方向偏心 | `delta = sqrt(dx^2+dy^2)/period_p` | C4→C1 |
| 单边开槽 | `delta = slot_width/outer_L` | C4→C1 |
| 边宽差 | `delta = (w_x-w_y)/w0` | C4→C2 |

### 示例 JSON

```json
{"period_p": 500, "h": 180, "outer_L": 260, "inner_L": 120, "hole_dx": 20, "hole_dy": 0}
```

---

# 12. 数据生成流程

建议按照以下流程执行。

## Step 1：建立母结构表

先把已经完成的所有 HTML 母结构录入 `mother_structures.csv`。

至少记录：

```text
family_id
structure_name_cn
base_group
symmetry_order
recommended_priority
possible_perturbations
```

---

## Step 2：建立扰动规则表

从每个母结构中挑选 1–3 种最清晰的扰动方式。

原则：

```text
第一阶段每次只改变一种扰动，不要多个扰动混合。
```

优先选择：

```text
C2 双柱：左右半径差
C4 十字：横竖臂长度差
C4 方环：内孔偏心
```

---

## Step 3：自动生成仿真样本表

根据扰动规则和 delta 列表自动生成 `simulation_samples.csv`。

例如对 C4 十字：

```text
L0 = 240 nm
Wx = Wy = 60 nm
period_p = 500 nm
h = 180 nm

delta = 0.00 → Lx = 240, Ly = 240
delta = 0.02 → Lx = 240, Ly = 235.2
delta = 0.04 → Lx = 240, Ly = 230.4
...
```

也可以反过来固定平均尺寸，让一个变长、一个变短：

```text
Lx = L0 * (1 + delta/2)
Ly = L0 * (1 - delta/2)
```

推荐第二种方法，因为整体结构尺寸变化更小，更容易把变化归因于对称性破缺，而不是整体尺度变化。

---

## Step 4：运行 FDTD 仿真

每个样本运行后至少保存：

```text
.fsp 模型文件
.txt 光谱文件
.png 电场图
```

建议 monitor 名称统一为：

```text
Trans
```

避免后续脚本提取数据时因为监视器名称不一致而报错。

---

## Step 5：提取光谱指标

从每个光谱 TXT 中提取：

```text
lambda_peak_nm
T_peak
T_min
FWHM_nm
Q_factor
num_peaks
sideband_T_max
```

并写入 `spectrum_metrics.csv`。

---

## Step 6：画核心规律图

第一阶段至少画以下 4 张图：

```text
delta - lambda_peak_nm
delta - FWHM_nm
delta - Q_factor
delta - T_peak
```

其中最关键的是：

```text
delta - Q_factor
```

如果接近出现：

```text
Q ∝ 1 / delta^2
```

说明该结构具有明显的对称性保护或类 quasi-BIC 特征。

---

# 13. Codex 可执行任务描述

可以把下面这段话复制给 Codex，让它根据本文档生成表格模板和脚本。

```text
请根据《基于群论对称性的母结构数据库建设说明文档》生成一个 Python 项目，用于创建和维护光子结构母结构数据库。要求如下：

1. 在当前目录下创建文件夹 symmetry_structure_database。
2. 在 01_tables 文件夹中生成以下 CSV 模板：
   - mother_structures.csv
   - perturbation_rules.csv
   - simulation_samples.csv
   - spectrum_metrics.csv
   - file_index.csv
   - inverse_targets.csv
3. 每个 CSV 文件必须包含文档中定义的字段表头。
4. 先预置 3 个母结构：
   - C2_dimer：双柱，base_group=C2
   - C4_cross：十字，base_group=C4
   - C4_square_ring：方环，base_group=C4
5. 为每个母结构预置至少一种扰动规则：
   - C2_dimer：radius_difference，C2->C1
   - C4_cross：arm_length_difference，C4->C2
   - C4_square_ring：hole_offset，C4->C2 or C4->C1
6. 编写 generate_sample_table.py，根据扰动规则和 delta 列表自动生成 simulation_samples.csv。
7. 编写 extract_spectrum_metrics.py，读取 spectrum txt 文件，并提取 lambda_peak、T_peak、FWHM、Q_factor、num_peaks 等指标。
8. 编写 plot_delta_Q.py，读取 simulation_samples.csv 和 spectrum_metrics.csv，绘制 delta-Q、delta-FWHM、delta-T_peak 图。
9. 所有脚本应包含中文注释，字段名保持英文，方便后续机器学习处理。
```

---

# 14. 第一版 Excel / CSV 字段总览

如果暂时只想生成一个 Excel 文件，可以设置 6 个 sheet：

| Sheet 名 | 对应 CSV | 作用 |
|---|---|---|
| `母结构表` | `mother_structures.csv` | 记录母结构 |
| `扰动规则表` | `perturbation_rules.csv` | 记录可变参数和降群方式 |
| `仿真样本表` | `simulation_samples.csv` | 记录每个样本的输入参数 |
| `光谱结果表` | `spectrum_metrics.csv` | 记录每个样本的输出光谱指标 |
| `文件索引表` | `file_index.csv` | 记录模型、光谱、场图文件路径 |
| `逆向目标表` | `inverse_targets.csv` | 记录目标光谱和筛选结果 |

---

# 15. 重要原则

## 原则 1：先少后多

第一阶段不要把所有母结构全部仿真。先做：

```text
C2 双柱
C4 十字
C4 方环
```

每个结构只做一种扰动。

---

## 原则 2：每次只改变一种物理因素

不要同时改变：

```text
周期 + 厚度 + 扰动 + 材料
```

否则无法判断光谱变化来自哪里。

推荐第一阶段固定：

```text
period_p
thickness_h
material
polarization
boundary_condition
```

只改变：

```text
delta
```

---

## 原则 3：delta 必须归一化

不要只记录“变化了 10 nm”。还要记录：

```text
delta = 归一化扰动强度
```

这样才能比较不同结构之间的规律。

---

## 原则 4：完整保存原始光谱

Excel 里记录的只是提取后的指标，不能代替原始光谱 TXT。

必须保存：

```text
wavelength_nm, transmission
```

因为后续可能需要重新计算 FWHM、重新做 Fano 拟合、重新筛选目标波长。

---

## 原则 5：场图只保存关键样本，但关键样本必须保存

建议至少保存以下三类样本的场图：

| 样本 | 意义 |
|---|---|
| `delta = 0` | 高对称母结构 |
| 小扰动样本 | 可能对应 quasi-BIC 或窄线宽状态 |
| 大扰动样本 | 辐射泄露增强、线宽变宽状态 |

---

# 16. 最终希望得到什么结果？

第一阶段目标不是马上训练复杂神经网络，而是先建立以下规律：

```text
母结构类型
    ↓
对称性标签
    ↓
降群路径
    ↓
扰动强度 delta
    ↓
光谱峰位 / FWHM / Q 值 / 透过率
```

如果可以得到清晰的：

```text
delta 增大 → Q 下降 → FWHM 变宽
```

或者某些结构在特定扰动范围内出现高 Q 窄峰，那么就可以进一步进入逆向设计阶段：

```text
目标光谱 → 筛选母结构类型 → 筛选降群路径 → 反推几何参数和扰动强度
```

这就是“基于群论对称性破缺的光子结构逆向设计”的核心路线。
