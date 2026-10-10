---
name: itc-market-analysis
description: 从 ITC 官方 Market Analysis Tools 获取特定产品的贸易、市场准入与出口潜力数据，并建立可审计的市场吸引力初筛模型。用于需要严格分离原始数据与模型输出、保留完整来源链和可重复计算的产品—市场研究。
---

# ITC 产品市场数据与初步建模

## 1. 目的

对给定的出口国、产品和候选市场执行两层工作：

1. **第一层：官方数据获取。** 从 ITC Trade Map、Market Access Map、Export Potential Map 及必要的 ITC 官方辅助页面获取并原样保存数据。
2. **第二层：市场吸引力初步建模。** 仅以已登记、已清洗、可追溯的数据为输入，对候选市场进行标准化、赋权、排序与敏感性分析。

最终成果是数据包、来源账本、清洗记录、模型工作底稿和初筛结果，不是报告正文。任何进入报告的事实必须能从 `fact_registry` 反向追踪到模型结果或清洗数据，再追踪到原始文件、官方页面、查询条件和访问时间。

## 2. 适用范围与边界

适用于单个或一组明确 HS 产品的全球贸易概览、某出口国对多个候选市场的表现比较、关税与非关税措施获取、ITC 出口潜力调用，以及 AHP、熵权、TOPSIS 或组合赋权的初步市场筛选。

不适用于：

- 把模型排名表述为确定性投资、出口或合规建议；
- 绕过登录、验证码、付费墙、速率限制或网站技术保护；
- 猜测或反向工程 ITC 未公开接口；
- 用第三方转载数据替代可获得的 ITC 官方数据；
- 未经核验，把商品俗称直接当作唯一 HS 编码。

## 3. 权威依据与口径

优先使用以下官方入口，并在每次运行时重新记录实际落地 URL：

- ITC Market Analysis Tools Portal：<https://marketanalysis.intracen.org/>
- Trade Map：<https://www.trademap.org/>
- Market Access Map：<https://www.macmap.org/>
- Export Potential Map：<https://exportpotential.intracen.org/>
- 数据可用性：<https://marketanalysis.intracen.org/en/data-availability>
- Export Potential methodology：<https://umbraco.exportpotential.intracen.org/media/cklh2pi5/epa-methodology_230627.pdf>
- 产品组与 HS 对照：<https://exportpotential.intracen.org/en/resources/correspondences>

采用 ITC 官方基本口径：

\[
EPI_{ijk}=Supply_{ik}\times Ease_{ij}\times Demand_{ijk}
\]

其中 \(i\) 为出口国，\(j\) 为目标市场，\(k\) 为产品。单个组合的未实现出口潜力为：

\[
Untapped_{ijk}=EPI_{ijk}-\min(ActualExports_{ijk},EPI_{ijk})
=\max(EPI_{ijk}-ActualExports_{ijk},0)
\]

聚合多个国家、市场或产品时，必须先逐组合计算再求和：

\[
Untapped_{IJK}=\sum_{i,j,k}[EPI_{ijk}-\min(ActualExports_{ijk},EPI_{ijk})]
\]

禁止用 `sum(EPI) - sum(actual)` 替代，因为某些组合的超额实现不能抵消其他组合的未实现潜力。

把 EPI 解释为基于供给、需求、市场准入和双边贸易便利度的前瞻性基准，不解释为最大可能销售额、销量承诺或概率预测。严格区分：

- **ITC 官方 EPI/未实现潜力**：直接来自 Export Potential Map；
- **本技能的市场吸引力分数**：研究者定义的多指标初筛结果；
- **自建 EPI 近似值**：仅在官方 EPI 不可导出且用户明确要求时生成，标注 `estimate_type=researcher_replication`，不得冒充 ITC 官方结果。

## 4. 输入规范

开始前创建 `request.yaml`：

```yaml
study_id: "YYYYMMDD-exporter-product-scope-v01"
product_name_zh: ""
product_name_en: ""
product_description: ""
hs_code: ""
hs_level: 6
hs_version: "HS2017"
hs_candidates: []
exporter_name: ""
exporter_iso3: ""
candidate_markets: []
candidate_market_iso3: []
trade_flow: "export"
years_annual: []
months: null
currency: "USD"
trade_value_unit: "USD thousand"
model_method: "hybrid"
# ahp | entropy | topsis_equal | ahp_topsis | entropy_topsis | hybrid
weight_policy: ""
access_language: "en"
requested_outputs:
  - raw_exports
  - cleaned_tables
  - epi_snapshot
  - market_ranking
research_question: ""
notes: ""
```

若 HS 编码未给出或存在歧义：

1. 记录商品材质、功能、工作原理、是否带电机、功率、用途、成套/零件状态等归类要素；
2. 保存候选编码和 ITC 官方英文品名；
3. 输出 `hs_resolution/hs_candidates.csv`，不得静默选码；
4. 若不同候选 HS 会实质改变结果，暂停建模并要求用户确认；
5. 探索性筛选可保留多个候选编码，但模型结果必须按 HS 分开。

## 5. 数据源优先级

1. ITC 工具直接导出的 CSV/XLSX/ZIP/JSON 或官方可下载表格；
2. ITC 页面中可见、可定位、可复现的表格或图表下载；
3. ITC 官方方法文件、元数据、数据可用性页面和产品对应表；
4. ITC 页面明确标示的底层官方来源，仅用于核验或补充；
5. 其他权威来源，仅当 ITC 不提供该指标且模型确有需要时使用，并单独登记来源等级与替代理由。

搜索引擎摘要、博客、新闻转载、无来源数据库和 AI 生成内容不得作为事实数据源。

## 6. 网站调用流程

### 6.1 通用调用协议

每次访问 ITC 工具时：

1. 使用用户授权的现有登录会话；若需要登录而未登录，停在登录页并请求用户接管。
2. 记录页面标题、最终 URL、访问时间（ISO 8601，含时区）、工具名称、界面语言和登录状态。
3. 设置出口国、进口国/区域、产品、HS 版本、贸易流、频率、年份、单位、指标和排序方式。
4. 截图或保存查询摘要区，确保所有筛选条件可见；截图是补充证据，不能替代结构化导出。
5. 优先使用官方 `Download/Export`；保留服务器原始文件名，并另存一份规范命名的只读副本。
6. 计算文件 SHA-256，记录文件大小、MIME/扩展名、工作表名和行列数。
7. 立即写入 `source_ledger.csv` 和本次查询的 `query_manifest.yaml`。
8. 不在浏览器下载目录直接清洗；先复制进本研究的 `raw/`，后续只读。

只有在官方界面没有下载功能时，才可提取页面可见表格。此时保存完整页面 URL、可见查询条件、截图、DOM/HTML（工具允许时）和转录校验记录。禁止复用未公开内部端点，除非 ITC 已公开并明确允许该 API。

### 6.2 Trade Map

至少获取：

- 世界对该产品的年度进口与出口总额；
- 主要进口市场：进口额、数量、单位价值、世界份额、增长率；
- 主要出口国：出口额、数量、单位价值、世界份额、增长率；
- 固定出口国后，对候选市场的双边出口额、数量、增长率和市场份额；
- 固定目标市场后，竞争来源国、进口额、份额、增长率、单位价值；
- 若研究季节性，导出至少 24 个月、优先 36–60 个月的月度数据。

分别保存 reporter 报告值和 mirror 值。若混用，添加 `trade_reporting_basis`：`direct_export`、`direct_import`、`mirror_import`、`mirror_export` 或 `mixed`。不得把 CIF 口径进口值与 FOB 口径出口值视为完全相等。

### 6.3 Market Access Map

以 `exporter × importer × product × tariff_year` 为最小单元，获取：

- MFN、实际适用税率、优惠税率；
- 贸易协定名称、税率类型、适用年份；
- 关税配额、贸易救济措施（如有）；
- 非关税措施分类、措施文本/代码、主管机构或链接（如提供）；
- 主要竞争来源国的相同口径税率。

分别保存 `applied_tariff`、`mfn_tariff`、`preferential_tariff`，不得用“最低税率”替代实际适用税率。协定优惠必须注明是否取决于原产地规则；未核验时标记 `preference_eligibility=unverified`。

### 6.4 Export Potential Map

固定 `exporter × market × ITC product group/HS`，记录页面预测基准或地平线，并获取：

- export potential value；
- actual/baseline exports；
- unrealized/untapped export potential，金额和比例；
- realized potential（如提供）；
- 产品或市场排名；
- 页面说明、方法版本、产品组标签及对应 HS；
- 下载文件、分享 URL 和查询截图。

若页面只显示四舍五入后的 `$x mn`，同时保存原始显示字符串和解析后的近似数值，设置 `precision_status=rounded_display`，不得伪造有效位数。若 ITC 产品组跨多个 HS 版本或编码，保存对应表并使用 `itc_product_group_id`。

### 6.5 数据覆盖检查

生成 `metadata/coverage_matrix.csv`，每行一个 `source × dataset × exporter × market × product × period`。状态仅可为：`complete`、`partial`、`not_available`、`blocked_login`、`blocked_captcha`、`blocked_terms`、`failed_technical`、`not_applicable`。只有 `complete` 或经说明可接受的 `partial` 数据可进入模型。

## 7. 失败与人工接管

遇到以下情况停止自动交互并请求人工接管：登录、验证码、多因素认证、账号权限、服务条款确认；会改变结论的 HS 歧义；下载所需许可确认；页面与导出条件不一致；两次重试后仍为空表、会话过期或页面未加载；网站明确禁止当前自动化方式。

接管请求必须说明已完成步骤、当前页面、所需用户动作、不会代替用户执行的动作和恢复方法。技术失败最多进行两次低风险重试并记录错误；不得快速循环刷新。官方工具不可用时保存错误截图并生成缺口清单，未经同意不得自动换第三方数据源。

## 8. 强制目录结构

```text
<study_id>/
├─ request.yaml
├─ README_DATA.md
├─ raw/                         # 永久只读
│  ├─ trademap/{annual,monthly,competition}/
│  ├─ macmap/{tariffs,ntm}/
│  ├─ export_potential_map/
│  └─ evidence/{screenshots,pages,methodology}/
├─ metadata/
│  ├─ source_ledger.csv
│  ├─ fact_registry.csv
│  ├─ file_manifest.csv
│  ├─ coverage_matrix.csv
│  ├─ hs_crosswalk.csv
│  └─ queries/<query_id>.yaml
├─ staging/{parsed,schema_profiles}/
├─ cleaned/
│  ├─ trade_annual.csv
│  ├─ trade_monthly.csv
│  ├─ tariffs.csv
│  ├─ ntm.csv
│  ├─ epi.csv
│  └─ data_dictionary.csv
├─ logs/{acquisition_log.csv,cleaning_log.csv,validation_log.csv,manual_interventions.csv}
├─ model/
│  ├─ config/{indicators.yaml,weights.yaml,scenarios.yaml}
│  ├─ input/{model_input.csv,input_lineage.csv}
│  ├─ intermediate/{transformed.csv,normalized.csv,weighted_matrix.csv,method_diagnostics.csv}
│  └─ output/{market_ranking.csv,sensitivity_results.csv,robustness_summary.csv,model_card.md}
├─ deliverables/{evidence_tables.xlsx,source_appendix.csv,fact_citation_map.csv,preliminary_findings.md}
└─ run/{run_manifest.yaml,environment.txt,checksums.sha256}
```

`raw/` 与 `model/` 之间禁止直接依赖。唯一合法链路：

```text
raw → staging → cleaned → model/input → model/intermediate → model/output → deliverables
```

每次跨层转换都要有日志和行级或字段级 lineage。

## 9. 文件命名规范

```text
<source>__<dataset>__exp-<ISO3>__imp-<ISO3-or-WLD>__hs<level>-<code-or-group>__hsv-<version>__<frequency>__<period>__access-<YYYYMMDD>__q-<query_id>.<ext>
```

示例：

```text
trademap__bilateral-exports__exp-CHN__imp-JPN__hs6-850811__hsv-HS2017__annual__2019-2024__access-20260904__q-Q0007.xlsx
```

仅用小写 ASCII、数字、短横线和双下划线分段。原始下载文件保留服务器文件名；规范副本通过 manifest 关联。`query_id`、`source_id`、`file_id`、`fact_id`、`model_run_id` 永久唯一。同一查询重下使用 `__r01`、`__r02`，不得覆盖。

## 10. 原始数据保存规则

- 按二进制原样保存并计算 SHA-256；
- 记录原始/规范文件名、下载时间、大小、MIME、工作表、编码、行列数；
- 保存触发下载的查询 manifest；
- 平台支持时将 raw 设为只读；
- 换单位、改列名、删合计行等全部在 `staging/` 或 `cleaned/` 完成；
- 不得用重新导出的文件替换原始文件；
- 截图不能替代可下载数据；
- 只能人工复制时，保存转录原稿，并以总计核验和抽样复核记录质量。

## 11. Source ledger

`metadata/source_ledger.csv` 一行代表一个可独立引用的数据获取事件，至少包含：

```text
source_id,study_id,source_tier,organization,tool_name,dataset_name,page_title,
landing_url,final_url,share_url,accessed_at,timezone,query_id,query_parameters_json,
exporter_name,exporter_iso3,importer_name,importer_iso3,region_scope,product_label,
hs_code,hs_level,hs_version,itc_product_group_id,trade_flow,frequency,period_start,
period_end,reference_year,tariff_year,projection_horizon,currency,value_unit,
quantity_unit,reporting_basis,valuation_basis,download_method,original_filename,
stored_raw_path,file_id,sha256,file_size_bytes,sheet_names,precision_status,
login_required,license_or_terms_note,methodology_url,coverage_status,retrieval_notes
```

要求：

- `query_parameters_json` 保存完整筛选条件和界面显示选项；
- `final_url` 是结果页，`landing_url` 是工具入口；
- `accessed_at` 精确到秒并带偏移，如 `2026-09-04T15:20:31+08:00`；
- `methodology_url` 指向与指标直接相关的 ITC 官方方法说明；
- 一个文件含多个数据集时可有多行 ledger，但关联同一 `file_id`；
- 页面数值无下载文件时，`stored_raw_path` 指向截图或保存页，并标注 `download_method=visible_page_capture`。

## 12. Fact registry 与引用字段

`metadata/fact_registry.csv` 是报告事实的唯一出口。每行一个可引用事实：

```text
fact_id,fact_text_short,metric_name,metric_value,display_value,currency,unit,
exporter_iso3,importer_iso3,hs_code,hs_version,period,source_id,file_id,
raw_locator,clean_table,clean_row_key,transformation_ids,model_run_id,
model_output_locator,citation_label,citation_url,accessed_at,confidence,
rounding_rule,status,reviewer_note
```

`raw_locator` 必须精确到工作表和单元格/行键，或 CSV 行键。`transformation_ids` 对应清洗日志。模型生成事实还必须填写 `model_run_id` 和 `model_output_locator`。

事实只有在以下条件全部满足时才可标为 `status=report_ready`：来源等级合格；HS、国家、年份、币种和单位明确；原始文件校验和存在；清洗链完整；计算已复核；舍入规则已记录；引用 URL 和访问日期可用。

内部引用标签建议：

```text
[ITC-<tool>-<source_id>, accessed <YYYY-MM-DD>]
```

最终报告可转换为脚注，但必须保留 `fact_id → source_id → raw file` 映射。

## 13. 数据清洗规则

清洗由确定性脚本或可复现步骤完成，并写入 `logs/cleaning_log.csv`：

```text
transformation_id,timestamp,input_file_id,input_path,input_sha256,output_path,
table_name,columns_affected,operation,parameters_json,rows_before,rows_after,
cells_changed,missing_before,missing_after,code_or_command_ref,operator,qa_result,notes
```

强制规则：

1. 先建立字段映射和数据字典，再改变列名。
2. 保留 `value_raw`、`unit_raw`、`country_raw`、`product_raw` 等原始文本列。
3. 空白、`-`、`n/a`、`...` 不自动转为 0；使用 `missing_reason`。
4. 国家统一为 ISO3，同时保留 ITC 显示名和区域/经济体性质。
5. 金额统一到明确基准单位并保存转换因子；千美元与美元不得混用。
6. 增长率统一为小数或百分数之一，并在数据字典声明。
7. 关税保存税率原值和适用类型，不自行选择最优惠税率。
8. HS 版本转换必须使用正式对照表，记录一对多/多对一及聚合方法。
9. 重复行按完整业务键检查；删除前记录原因和保留行。
10. 合计、世界、区域与单国行分层标记，不得重复计入。
11. 检查 reporter/mirror、FOB/CIF 和再出口风险；异常不静默修正。
12. 对 EPI 保留页面显示值、解析值、预测地平线和精度状态。
13. 对增长率同时保存 ITC 原值与自行计算值；不一致时标记期间或公式差异。

最低 QA：

- 原始与清洗后关键总计核对；
- 随机抽查不少于 10 行或总行数 5% 中的较大者，上限可设 50 行；
- 国家数、年份数、市场覆盖率和缺失率检查；
- 单位、币种、HS 版本、年份范围一致性检查；
- 极端值和符号方向检查；
- 直接报告与镜像报告差异检查。

## 14. 第一层：EPI 与未实现潜力调用逻辑

### 14.1 官方值优先

对每个 `exporter × market × product`：

1. 在 Export Potential Map 选择 EPI 而非 PDI；
2. 记录产品是否属于 ITC 可计算的既有出口产品；
3. 保存 potential、actual/baseline、untapped amount、untapped share、projection horizon；
4. 用下载值或可见值复核：

```text
untapped_check = max(epi_value - min(actual_exports, epi_value), 0)
untapped_share_check = untapped_check / epi_value    # epi_value > 0 时
```

5. 若差异超过页面舍入造成的合理范围，标记 `validation_status=needs_review`，不得覆盖 ITC 值；
6. 聚合前先在最细组合上计算未实现潜力。

### 14.2 官方 EPI 不可得

1. 记录 `not_available` 或技术失败，不把缺失写成 0；
2. 检查 HS—ITC 产品组不匹配、产品被排除、出口记录不足或预测口径变化；
3. 请求用户决定是否只用 Trade Map/Market Access Map 完成吸引力模型；
4. 只有用户明确要求复刻时，另建 `model/epi_replication/`，依据当次保存的 ITC 方法文件实现研究者近似模型；
5. 复刻必须记录贸易数据、五年加权、GDP/人口预测、关税、距离、弹性、归一化和缺失处理；无法获得的 ITC 内部处理不得假定为完全一致。

自建结果的标题和字段必须含 `Unofficial researcher replication` / `非 ITC 官方估计`。

## 15. 第二层：市场吸引力模型

### 15.1 指标体系

| 维度 | 指标 | 方向 | 默认变换 | 首选来源 |
|---|---|---:|---|---|
| 市场规模 | 目标国该产品最近年度进口额 | 正向 | `log1p` | Trade Map |
| 市场增长 | 3年或5年进口 CAGR | 正向 | Winsorize | Trade Map |
| 出口国表现 | 对该市场出口额/份额 | 正向 | `log1p` 或原值 | Trade Map |
| 未实现空间 | ITC untapped potential amount | 正向 | `log1p` | Export Potential Map |
| 潜力比例 | untapped potential / EPI | 正向 | Winsorize | Export Potential Map |
| 市场准入 | 实际适用/优惠关税 | 负向 | 成本型标准化 | Market Access Map |
| 关税优势 | 竞争国加权税率减出口国税率 | 正向 | 原值 | Market Access Map |
| 竞争强度 | HHI 或前三来源国份额 | 负向 | 成本型标准化 | Trade Map |
| 竞争位置 | 出口国在目标市场份额/排名 | 正向 | 排名转逆向 | Trade Map |
| 稳定性 | 月度或年度波动系数 | 负向 | 成本型标准化 | Trade Map |
| 非关税压力 | NTM 条目/覆盖的结构化代理 | 负向 | 分级或成本型 | Market Access Map |

不要把同一信息的高度相关指标重复计权。例如同时使用进口额、世界进口份额和进口排名时，应检查相关性并删减或降低权重。NTM 数量不等同实际合规成本；没有覆盖率或频率指数时标为代理变量。

### 15.2 指标方向与标准化

在 `indicators.yaml` 记录每个指标的定义、公式、方向、单位、期间、来源字段、缺失政策、变换、异常值处理、标准化方法和权重来源。

默认对金额用 `ln(1+x)`；增长率和比率仅在样本充分时做 1%/99% Winsorize，否则报告极端值并避免机械截尾。

Min-Max 正向指标：

\[
z_{ij}=\frac{x_{ij}-\min(x_j)}{\max(x_j)-\min(x_j)}
\]

负向指标：

\[
z_{ij}=\frac{\max(x_j)-x_{ij}}{\max(x_j)-\min(x_j)}
\]

若 `max=min`，该指标无区分度：从本次模型剔除并将权重重新归一化，不得让除零结果变成 0。

缺失值默认不做均值填补。依次尝试：补抓官方数据、删除缺失过多指标、在共同完整样本建模。若必须插补，单列场景并披露方法。不得把缺失关税当零关税。

### 15.3 可切换方案

#### A. AHP

用于存在明确专家判断或策略权重时。保存完整成对比较矩阵、判断依据、参与者、日期和一致性：

\[
CI=\frac{\lambda_{max}-n}{n-1},\quad CR=\frac{CI}{RI}
\]

仅当 `CR < 0.10` 时接受；否则修订判断矩阵。单人未经说明的主观权重不得称为专家共识。

#### B. 熵权

保存非负标准化矩阵、比例矩阵、熵值、差异系数和最终权重。若存在 0，使用明确的小常数或约定 `0 ln 0 = 0` 并记录实现。熵权反映区分度，不等于经济重要性。

#### C. TOPSIS

保存加权矩阵、正负理想解、距离和贴近度：

\[
C_i=\frac{D_i^-}{D_i^+ + D_i^-}
\]

`C_i` 越大，初筛吸引力越高。TOPSIS 可配等权、AHP、熵权或组合权重。

#### D. 默认 hybrid

默认以 AHP 表达研究目标、熵权反映样本信息量，再用 TOPSIS 排序：

\[
w_j^{hybrid}=\alpha w_j^{AHP}+(1-\alpha)w_j^{Entropy}
\]

默认 `alpha=0.5` 仅作为起点；在 `weights.yaml` 声明并做 `0.3/0.5/0.7` 敏感性分析。没有有效 AHP 判断矩阵时，使用 `entropy_topsis`，不得伪造 AHP 权重。

### 15.4 模型运行记录

每次生成唯一 `model_run_id`，记录输入文件 SHA-256、样本和被排除市场、指标与时间窗、变换和缺失处理、权重及来源、软件/脚本版本、随机种子、中间矩阵、得分与排名、相对上次运行的差异、局限性。禁止只保存最终排名。

### 15.5 敏感性与稳健性

至少执行：

1. AHP、熵权、等权或 hybrid 的可用权重场景；
2. `alpha=0.3/0.5/0.7`；
3. 单项权重 ±20%，其余同比例归一化；
4. 留一指标法；
5. 金额指标有无 `log1p`；
6. 3 年与 5 年 CAGR；
7. 舍入 EPI 值的容差场景；
8. 直接/镜像贸易口径场景（如适用）。

输出每个市场的平均排名、最好/最差排名、排名标准差、进入 Top 3 的比例和与基准排名的 Spearman 相关系数。若 Top 3 对合理变化高度敏感，输出“排名不稳健”，不得强行给出唯一市场。

## 16. 审计与可重复性

一次运行只有满足以下条件才算完成：

- `request.yaml`、查询 manifest 和覆盖矩阵齐全；
- 所有 raw 文件有 SHA-256 且未被修改；
- source ledger 无缺失核心定位字段；
- 每个模型字段均在 `input_lineage.csv` 指向来源和转换；
- 所有计算可从已保存输入重跑；
- 模型输出和敏感性结果可重现；
- `fact_registry` 中所有 `report_ready` 事实通过抽查；
- 所有失败、人工介入和手工修正均有日志；
- 运行环境、脚本/工作簿版本、时区和运行时间已记录；
- `README_DATA.md` 说明数据许可、引用方式和局限性。

使用电子表格建模时，公式单元格不得只保留粘贴值，并导出公式审计表。使用代码时保存依赖版本和入口命令。动态网页可能改变，查询截图和访问日期不可省略。

## 17. 最终输出模板

`deliverables/preliminary_findings.md` 仅使用以下结构，不扩写成比赛报告：

```markdown
# <产品> ITC 数据与市场初筛结果

## 研究口径
- 出口国：
- 产品与 HS 版本：
- 候选市场：
- 数据期间：
- 访问日期：
- 模型方法与 model_run_id：

## 数据覆盖与缺口
| 数据集 | 覆盖 | 缺口 | 处理 |

## 官方 ITC EPI/未实现潜力
| 市场 | ITC 产品组/HS | EPI | 实际/基准出口 | 未实现潜力 | 比例 | 预测地平线 | source_id |

## 市场吸引力初筛
| 排名 | 市场 | 得分 | 规模 | 增长 | 准入 | 潜力 | 竞争 | 稳健性 |

## 敏感性摘要
| 市场 | 基准排名 | 平均排名 | 最好 | 最差 | Top 3 比例 | 判断 |

## 证据与引用索引
| fact_id | 事实 | source_id | citation_label | URL | access date |

## 限制
- 本结果是数据初筛，不是销量预测或进入建议。
- EPI 是 ITC 模型基准，不是市场容量上限。
- 缺失、舍入、HS 对照、镜像数据和代理变量限制：...
```

此外输出 `evidence_tables.xlsx`、`source_appendix.csv`、`fact_citation_map.csv`、`market_ranking.csv` 和 `model_card.md`。

## 18. 示例工作流

用户请求：“分析中国 HS 850811 吸尘器对日本、韩国、越南、泰国和马来西亚的市场吸引力，使用 2019–2024 年数据。”

1. 创建 `request.yaml`，确认 HS 版本和 ITC 官方产品名称。
2. 为每个 ITC 工具建立查询清单与 `query_id`。
3. 从 Trade Map 下载世界进口/出口、中国对五市场的年度贸易、五市场竞争来源国；需要季节性时再取月度数据。
4. 从 Market Access Map 获取中国进入五国的实际适用税率、MFN、协定优惠、NTM，以及主要竞争国可比税率。
5. 从 Export Potential Map 获取中国—每个市场—对应产品组的 EPI、实际/基准出口和未实现潜力。
6. 原样保存下载和截图，登记 source ledger、校验和与查询参数。
7. 在 `staging/` 解析，在 `cleaned/` 统一 ISO3、单位、年份和 HS 对照，保留原始文本列。
8. 建立模型输入，默认 hybrid + TOPSIS；无有效 AHP 判断矩阵时切换为熵权 TOPSIS。
9. 保存标准化、中间矩阵、权重、得分与敏感性场景。
10. 生成覆盖、排名、证据索引与局限说明；不撰写策划书段落。

## 19. Codex 执行指令

1. 先结构化产品、HS、出口国、候选市场、期间和方法；只在 HS 或授权问题会实质改变结果时暂停询问。
2. 检查当前目录的 `AGENTS.md` 和只读约束；不要修改来源材料。
3. 创建研究目录和 request，不在 `raw/` 写模型文件。
4. 先生成数据需求矩阵和查询计划，再访问网站。
5. 每获取一个文件立即登记来源和校验和，不在最后补记。
6. 优先官方下载；仅在无下载时保存页面证据并提取可见表格。
7. 每一清洗步骤产生可重跑记录；禁止直接改数值而不留日志。
8. 建模前运行覆盖、单位、HS、年份和重复值检查。
9. 官方 EPI 与研究者吸引力分数使用不同字段、表名和措辞。
10. 运行模型和敏感性分析，保存全部中间量。
11. 对每个计划用于报告的事实创建 `fact_id` 并验证链路。
12. 最后交付文件清单、数据缺口、排名稳健性和限制；不生成比赛报告正文。

## 20. 禁止事项

- 禁止修改、覆盖或删除 `raw/` 中任何文件。
- 禁止在没有 `source_id` 时把数值放入交付表。
- 禁止遗漏访问日期、最终 URL、查询参数、HS code/version、国家、年份、单位和原始文件名。
- 禁止把空值、受限值、未披露值自动变成 0。
- 禁止混合不同 HS 版本而不使用对照表和聚合说明。
- 禁止混合年度/月度、直接/镜像、FOB/CIF 或不同币种后直接比较。
- 禁止把页面四舍五入值伪装成精确值。
- 禁止把 Export Potential Map 产品组无条件等同单一 HS6。
- 禁止将自建分数称为 ITC EPI，或把自建 EPI 复刻称为官方值。
- 禁止将未实现潜力解释为必然可实现的销售额。
- 禁止只保存最终得分，或手工修改权重/排名而不产生新 `model_run_id`。
- 禁止把 AHP 主观权重描述为客观权重、把熵权描述为经济重要性、把 TOPSIS 排名描述为因果结论。
- 禁止绕过登录、验证码、服务条款、下载限制或技术保护。
- 禁止在官方数据不可用时静默替换为第三方数据。
- 禁止代写比赛报告、营销文案、战略建议或无证据结论。

## 21. 完成判定

仅当以下条件同时成立才声明完成：

1. 原始数据与来源证据独立保存且有校验和；
2. 清洗、输入、标准化、权重、中间计算、结果和敏感性可复现；
3. 所有可引用事实可通过 `fact_registry` 回溯到官方来源；
4. 已明确列出无法获取的数据、人工介入点、模型限制和不稳定结论。
