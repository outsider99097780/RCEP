# 石头科技扫地机 ITC 市场潜力分析

## 研究口径

- 出口国：中国（CHN，ITC reporter 156）
- 产品：中国海关输入 `85098090.00`；ITC 可计算产品组为 HS6 `850980`
- ITC 产品组描述：`Electromechanical domestic appliances, n.e.s.`
- 候选市场：东盟十国、澳大利亚、新西兰、日本、韩国，共 14 个市场
- 数据期：2020—2025 年贸易数据；EPM 使用 ITC 返回的官方预测口径（当前记录显示 2030）
- 货币：USD；贸易金额原始单位为 USD thousand，EPM 金额为 USD
- 访问日期：2026-09-05（Asia/Shanghai）

## 重要产品边界

`85098090.00` 是中国海关 10 位申报码；本数据包在 ITC Trade Map、Market Access Map 和 Export Potential Map 中使用 HS6 `850980`。ITC 的 HS6 产品组并非扫地机器人专属，且产品描述明确排除/区分部分真空吸尘器。因而本分析可用于“扫地机相关 HS850980 产品组”的出口潜力筛选，不能直接等同于 Roborock 品牌或扫地机器人专属市场规模。产品归类依据及风险见 `raw-material/ITC-data/HS-CORRESPONDENCE.md`。

## 分析过程

1. 读取 `raw-material/ITC-data/_modeling-output/rcep_country_comparison_model_inputs.csv`，保留 14 个候选市场及其来源 ID。
2. 使用 Trade Map 的 2025 年目的国全球进口额、2020—2025 CAGR、中国份额和中国供应商排名衡量市场规模、增长和竞争位置。
3. 使用 EPM 官方 `epi_potential_usd`、`baseline_exports_usd` 和 `untapped_potential_usd` 衡量潜在空间；未实现潜力按 ITC 口径逐市场计算：`max(EPI - baseline, 0)`。
4. 使用 Market Access Map 返回的适用关税作为准入指标；`ntm_measure_count_max` 仅在原始 NTM 汇总真实可用时使用，空值不填 0。
5. 为避免高相关指标重复计权，主排序采用透明的等权 TOPSIS：
   - 正向：2025 进口额、进口 CAGR、中国份额、中国供应商排名的逆向转换、EPI、未实现潜力；
   - 负向：适用关税；
   - 缺失关键 Trade Map 数据的市场不进入主排序；
   - 结果仅是初筛，不是销量预测或确定性出口建议。

## 结果摘要

在完整 Trade Map 覆盖的市场中，按可复现的等权 TOPSIS 初筛，前三名为：

1. 日本：进口规模最大，EPI 与未实现潜力最高，但 2020—2025 进口 CAGR 为负，需关注成熟市场收缩。
2. 韩国：进口规模较大、增长为正，EPI 和未实现潜力高，中国份额高。
3. 澳大利亚：进口增长为正，EPI 与未实现潜力较高，中国为第一供应国，适用关税为 0%。

该排名是产品组层面的数据筛选结果，不代表 Roborock 在当地的品牌市占率，也不替代企业层面的渠道、价格和品牌研究。

## 文件结构

- `request.yaml`：研究请求和产品边界
- `model_inputs.csv`：模型输入副本，保留 `source_ids`
- `market_ranking.csv`：可复算的初筛排名及指标
- `methodology.md`：清洗、指标、缺失处理和局限
- `source_ledger.csv`：原始文件、ITC URL、查询条件、访问时间和 SHA-256 映射
- `fact_registry.csv`：报告可引用事实到来源文件的映射
- `limitations.md`：HS 代理口径、品牌层面缺口和数据风险

## 原始来源

所有原始文件均保留在 `raw-material/ITC-data/`，本目录不覆盖原始数据。来源账本来自：

- `raw-material/ITC-data/source-ledger.csv`
- `raw-material/ITC-data/source-ledger-master.csv`
- `raw-material/ITC-data/source-ledger-export-potential-map.csv`
- `raw-material/ITC-data/source-ledger-market-access-map.csv`
- `raw-material/ITC-data/file-inventory-sha256.csv`
