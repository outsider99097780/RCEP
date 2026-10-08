# 方法与可复现规则

## 数据层

模型输入来自 `raw-material/ITC-data/_modeling-output/rcep_country_comparison_model_inputs.csv`。该文件已经把各市场的 Trade Map、Market Access Map 和 EPM 字段拼接，并以 `source_ids` 指向原始来源。原始响应、查询 URL、访问时间和 SHA-256 不在模型阶段重写。

## 指标

- 市场规模：`imports_2025_usd_thousand`，目的国从全球进口额。
- 市场增长：`import_cagr_2020_2025_pct`。
- 中国供应地位：`china_share_2025_pct` 正向；`china_rank_2025` 作为审计字段，完整市场均为第 1 名而不进入评分。
- 官方潜力：`epi_potential_usd`。
- 未实现空间：`untapped_potential_usd`，由 ITC EPM 字段/逐市场公式得到。
- 准入：`minimum_returned_applied_tariff_pct` 作为成本型指标。
- `ntm_measure_count_max` 的空值保持缺失，不视为零。

## 排名规则

主排名只使用 Trade Map 关键字段完整的市场；缺失进口额、CAGR、中国份额或排名的市场列为 `insufficient_trade_coverage`，不强行补值。各指标在完整市场集合内做 min-max 标准化，正向指标按 `(x-min)/(max-min)`，适用关税在完整市场中均为 0% 且无区分度，因此不进入主评分；等权平均得到 `topsis_screen_score`。此处为可解释的初筛，不冒充 ITC 官方排名。

## 审计规则

金额、数量、单位、HS 层级、年份和来源标签不在模型中静默改写。贸易额、EPI 和关税分属不同工具，不能相互替代；中国海关 10 位码与 ITC HS6 产品组的差异必须在报告中披露。
