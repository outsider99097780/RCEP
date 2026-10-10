# ITC 数据包：China → RCEP，HS 850811

本目录保存按中国税号 `85081100`、在 ITC 跨国工具中按 HS6 `850811` 查询的官方原始响应与可复算派生表。范围为中国出口至除中国外的 14 个 RCEP 成员，贸易年份为 2020—2025；Market Access Map 与 Export Potential Map 使用访问日可获得的当前数据。

## 目录结构

- `{country}/trade-map/`：Trade Map 原始 JSON，包括中国对该国出口及该国从全球进口的金额、数量和供应国明细。
- `{country}/market-access-map/`：该国在 HS6 `850811` 下的全部国家税则线、对中国适用关税及 NTM 原始响应。
- `{country}/export-potential-map/`：中国—目的国—HS850811 的官方 EPI 记录。
- `{country}/derived/`：从原始响应机械提取的年度指标、供应国、关税、NTM 和出口潜力摘要。
- `_shared/`：中国对全球出口、国家代码表、EPM 产品和国家参考表。
- `_modeling-output/`：14 国横向比较模型输入；不覆盖原始数据。

## 引用与追溯

报告事实应先引用 `source-ledger-master.csv` 中的 `source_id`，再沿 `raw_file` 定位原始响应。账本保存发布者、工具、访问时间、完整 URL、查询参数和 SHA-256。`file-inventory-sha256.csv` 对整个数据包逐文件校验。

## 产品口径

ITC Trade Map 和 Export Potential Map 使用六位 HS `850811`。Market Access Map 先用 `850811` 查找每个目的国的国家税则线，再逐条查询对华税率和 NTM。中国输入 `85081100` 不能直接替代目的国税则线。

HS850811 的范围是额定功率不超过 1,500 瓦、集尘袋或其他容器容积不超过 20 升的自带电动机真空吸尘器。它涵盖扫地机器人，也可能包括满足同一技术边界的非机器人吸尘器，因此贸易额和 EPI 是产品组数据，不是石头科技品牌销量。

## 原始数据与派生结果

原始 JSON、EPM 加密传输响应和查询元数据不得手工改写。`derived/` 与 `_modeling-output/` 只读取原始文件并保留 `source_ids` 或 `raw_source_file`。金额单位、数量单位和年份直接继承 ITC 响应；数量单位必须逐观察值读取。

