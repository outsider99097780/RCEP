# ITC 数据包：China → RCEP，HS 850980

本目录保存按用户指定编码 `85098090.00`、在 ITC 中按 HS6 `850980` 查询的官方原始响应与可复算派生表。范围为中国出口至除中国外的 14 个 RCEP 成员，贸易年份为 2020—2025；Market Access Map 与 Export Potential Map 使用访问日可获得的当前数据。

## 目录边界

- `{country}/trade-map/`：Trade Map 原始 JSON；不得手工修改。
- `{country}/market-access-map/`：目的国 NTL、关税和 NTM 原始 JSON；不得手工修改。
- `{country}/export-potential-map/`：该国官方 EPI 原始记录；不得手工修改。
- `{country}/derived/`：由上述原始文件计算或抽取的 CSV；可重建，不属于原始证据。
- `_shared/`：中国对全球贸易、ITC 国家代码表、EPM 全市场响应及产品参考表。
- `_modeling-output/`：14 国横向比较的模型输入，不属于原始数据。
- `source-ledger-*.csv`：各工具来源账本；`source-ledger-master.csv` 为统一索引。
- `file-inventory-sha256.csv`：文件清单与校验哈希。

## 最重要的分类限制

ITC EPM 将 `850980` 标为 “Electromechanical domestic appliances, n.e.s.”。Market Access Map 的目的国税则描述进一步注明：该产品组为带自备电机的其他机电家用器具，并排除 HS 8508 的真空吸尘器。中国海关 10 位编码 `85098090.00` 不能在没有商品归类依据的情况下等同于“扫地机器人”全部产品。

因此，本数据包只证明“按用户指定编码查询到的 HS850980 产品组数据”，不能证明其中所有贸易均为扫地机器人。若产品核心功能是吸尘，应在报告前核验是否归入 8508；详见 `HS-CORRESPONDENCE.md`。

## 计算口径

- Trade Map 金额：原始接口单位为 `USD thousand`。
- 数量：逐条读取原始 JSON 的 `unit`，不得默认；本次多数为 `Tons`。
- 单位价值（当数量单位为吨）：`金额（千美元） ÷ 数量（吨） = 美元/千克`。
- 目标市场中国份额：`目的国报告的自中国进口额 ÷ 目的国自全球进口额`。
- 目标市场在中国出口中的份额：`中国报告的对该国出口额 ÷ 中国对全球出口额`。
- CAGR：`(末期值/初期值)^(1/5)-1`；端点缺失或非正时留空。
- EPM 未实现潜力：`max(EPI potential - baseline exports, 0)`；原始官方字段保留在每国 EPI JSON 中。
- 关税：目的国 NTL 可能有多条，`tariff_summary.csv` 保留每条税则线和每个返回税制；不得把简单最小值直接称作整类产品的唯一税率。
- NTM：措施数量是 ITC/UNCTAD 数据库记录数，不等于合规成本或壁垒强度。
- `ntm_summary.csv` 为空表示该次 ITC 接口没有返回措施记录，不应解释为该市场依法不存在任何监管要求。

## 数据缺口

Trade Map 的 2025 年目的国直接进口数据在老挝、缅甸和越南为空；老挝 2024 年也为空。空值原样保留，没有使用镜像值填补。中国海关报告的对这些市场出口数据仍单独存在，不得与目的国进口口径混用。

## 使用规则

报告中引用任何数值时，应同时记录：来源工具、查询 URL、访问时间、HS 层级/版本、报告国与伙伴国、年份、原始文件路径、来源 ID。派生表的 `source_ids` 或 `raw_source_file` 可连接到来源账本。不要把派生值描述为 ITC 直接发布值。
