# HS 对应关系与归类风险

## 已验证的对应层级

| 层级 | 本次使用 | 证据位置 |
|---|---|---|
| 中国海关申报输入 | `85098090.00` | 用户指定；本数据包未取得中国海关税则原文 |
| ITC Trade Map 查询层级 | HS6 `850980` | Trade Map 查询 URL、各原始 JSON 的 `aggregateRecords.productCd` |
| ITC Export Potential Map 产品组 | `850980` — Electromechanical domestic appliances, n.e.s. | `_shared/export-potential-map/hs850980_epm_product_reference_extract.json` |
| 目的国国家税则线 | 各国在 HS6 `850980` 下返回的 1—5 条 NTL | 各国 `market-access-map/destination_ntl_under_hs850980.json` |

Trade Map 的跨年份序列为了统一不同 HS 版本，响应中可能同时出现关联的子记录代码，而 `aggregateRecords` 保留本次请求的 `850980`。建模应使用 aggregate record；子记录只能用于审计 ITC 的跨版本聚合，不应相加后替代 aggregate record。

## 不能自动推定的事项

1. 中国 10 位税号与 ITC HS6 产品组是“上卷聚合”关系，不代表 10 位税号占该 HS6 的全部贸易。
2. 目的国 NTL 与中国 10 位税号不是一一对应；本数据包保存了每个目的国在 HS6 下返回的全部候选 NTL。
3. HS850980 的官方描述排除 HS8508 真空吸尘器。带吸尘功能的扫地机器人可能涉及 8508，必须依据产品结构、主要功能、归类决定或海关预裁定核验。
4. 未完成上述核验前，报告只能写“HS850980 产品组”，不应写成“扫地机器人专属市场规模”。

