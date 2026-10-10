# Retail competition SKU snapshot

This folder is a source-traceable, targeted snapshot of public robot-vacuum listings for Roborock, Ecovacs, Xiaomi, Dreame and Narwal on Kakaku (Japan), Danawa (South Korea) and GetPrice (Australia). Generated 2026-10-02T22:53:45+08:00.

## Scope

- Up to 20 eligible public product-detail pages per brand and site, selected in the public category/search order.
- Only fields needed for SKU, price, offer, review and specification research were parsed.
- Full HTML pages, hidden APIs, price-history endpoints, shop redirect links and access-control bypasses were not used or stored.
- Raw records are compact parsed JSON with URL, access time, page title, response hash, parsed fields and bounded evidence excerpts.

## Directory guide

- `config/`: brand labels and fixed collection/price rules.
- `raw/`: immutable parsed capture records and `robots.txt` compliance snapshots by site.
- `metadata/source_ledger.csv`: report-ready provenance ledger for every list/product source.
- `metadata/crawl_log.csv`: request outcomes and manual-takeover flags.
- `metadata/model_crosswalk.csv`: cautious marketing-name crosswalk; no official equivalence is asserted.
- `cleaned/`: normalized product, offer and specification tables, plus per-market subsets.
- `analysis/`: descriptive price positioning, brand summary and data-quality report.

## Price logic

- 3 or more qualifying normal offers: median.
- 1–2 qualifying normal offers: lowest available normal price, explicitly marked `<3_offers`.
- Membership/card/coupon/points prices, used/refurbished goods and overseas-purchase rows are flagged rather than silently treated as normal prices.
- Korean `overseas_purchase` rows are retained separately and excluded from the main Korean representative price.
- Missing values remain blank; blanks are never replaced with zero.

## Citation

Join any cleaned row to `metadata/source_ledger.csv` through `source_ledger_id`. The ledger contains the provider, direct URL, query parameters, page title, access date, response SHA-256, collection scope and raw-record path. The `citation_label` field can be adapted into report endnotes.

## Reproducibility

The collection policy is in `config/collection_rules.yaml`; all request outcomes are in `metadata/crawl_log.csv`; source content hashes let reviewers detect page changes. Because live retail pages change, reproducing the same query later may yield different products and prices.

## Explicit product exclusions

`cleaned/excluded_products.csv` records 9 non-comparable public listings removed from the floor robot-vacuum main tables. Raw evidence and source-ledger rows remain intact.

## 2026-10-10：新增新西兰、马来西亚

新西兰采用 PriceSpy；马来西亚按用户最新要求仅采用 PriceShop，PriceMe 不再是输入来源。原日本、韩国、澳大利亚的逐国文件保持不变，共享表只追加新市场记录。新增详细字段见 `cleaned/products_NZL_detailed.csv`；原始事实、报价、价格历史摘要和来源台账分开保存。

新增市场的代表价格规则：两个及以上合格新品报价取中位数，一个取单报价；与原三国“少于三个取最低价”的规则不同，跨国分析时须明确方法或另行统一重算。本轮不重算旧市场。未知库存报价保留并标记，同时提供仅确认有货报价的代表价，供敏感性检查。

PriceShop 马来西亚现有数据更新见 `analysis/priceshop_MYS_20261010.md`：44个商品页、281条缓存报价，另有独立保存的历史价格证据。人工采集已取消。商品汇总的代表价明确是缓存显示价，不是访问当日已验证价格；五品牌完整实时目录尚未取得，云鲸仍缺商品报价页。较早的访问限制见 `analysis/market_expansion_20261010.md`，仅代表之前那轮状态。

## 马来西亚专用价格与审计约定

MYS 的原结构价格列须同时读取 `representative_price_method`、`collection_status` 和 `data_quality_flag`。新增详细表提供缓存年龄、商家组平衡中位数和 `eligible_for_current_verified_price_comparison=false`。历史新闻、捆绑活动与商品报价分表保存，来源唯一为 PriceShop。未确认完整目录，不把本次样本的品牌均价解读为全国品牌价格或销售表现。
