# 派生与初步建模说明

本目录没有替用户代写比赛报告。`derived/` 与 `_modeling-output/` 仅提供可复算的结构化输入。

## 原始数据与派生结果的边界

- 原始 JSON/B64 保留 ITC 的字段、空值、来源和接口响应，不做替换或插补。
- CSV 中的份额、排名、单位价值、CAGR 和未实现潜力属于本地计算。
- EPM 的 `value`、`exportValue`、`realizedPotential`、`gap`、`xik`、`mjk`、`xij`、`tariff` 和 `rank` 是官方响应字段；CSV 中将 `value` 命名为 EPI potential，将 `exportValue` 命名为 baseline exports。
- Market Access Map 对 HS6 下多个目的国 NTL 返回多条记录，横向模型中的最低返回税率仅为机器可读的预览变量，正式比较必须按实际产品对应 NTL 重新选择。

## 初步市场吸引力模型建议

`_modeling-output/rcep_country_comparison_model_inputs.csv` 可用于后续 TOPSIS、熵权或 AHP-TOPSIS。建议先处理缺失值，再分别标准化：市场进口规模、进口 CAGR、中国份额、EPI 未实现潜力为效益型；关税、NTM 数量为成本型。由于 NTM 数量不等于负担强度，建议仅作低权重风险代理，并进行剔除该指标的敏感性分析。

当前文件没有预设权重或最终排名，避免在 HS 归类与缺失值处理尚未确认时生成误导性结论。

