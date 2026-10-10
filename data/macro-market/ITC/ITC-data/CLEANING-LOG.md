# 数据清洗日志

1. Trade Map 保留完整 JSON；跨年份金额和数量均读取 `aggregateRecords` 的 HS850811 值。
2. 数量单位读取每条观察的 `unit` 字段，不跨单位直接求和。
3. 目的国市场份额以进口国报告的全球进口额为分母、中国来源进口额为分子。
4. 供应国排名按目的国报告的供应国进口金额排序；不以中国出口镜像值替代。
5. 增长率仅在起止值均有效且起始值大于零时计算；缺失值保持空白。
6. 单位价值只在数量单位为 Tons 且数量大于零时计算，公式为千美元/吨，即美元/千克。
7. Market Access Map 先取得目的国在 HS850811 下的全部 NTL，再逐条保存关税和 NTM；不挑选单一税则线。
8. EPI 的 `value` 和 `exportValue` 原样保存；未实现潜力仅按 `max(value-exportValue,0)` 机械计算，并保留官方 `gap` 与 `realizedPotential`。
9. 原始响应与派生表分目录保存；派生行通过 `source_ids` 或 `raw_source_file` 回指原始文件。

