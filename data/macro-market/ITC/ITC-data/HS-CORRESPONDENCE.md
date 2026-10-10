# HS 对应关系

| 层级 | 代码 | 依据 |
|---|---|---|
| 中国海关研究输入 | `85081100` | 用户核查后指定 |
| ITC Trade Map 查询层级 | HS6 `850811` | 查询 URL 及原始 JSON 的 `aggregateRecords.productCd` |
| ITC Export Potential Map 产品组 | `850811` | `_shared/export-potential-map/hs850811_epm_product_reference_extract.json` |
| 目的国国家税则线 | 各国在 HS6 `850811` 下返回的 NTL | 各国 `market-access-map/destination_ntl_under_hs850811.json` |

Trade Map 跨年份响应可能含不同 HS 版本下的关联子记录；建模使用 `aggregateRecords` 中本次请求的 `850811` 聚合值，不能把子记录再次求和。

HS850811 的统计边界由功率和容器容量界定，并非“扫地机器人专属编码”。报告可将其称为扫地机器人所在的 HS850811 产品组，不应把该组贸易额直接写成扫地机器人或 Roborock 品牌销量。

