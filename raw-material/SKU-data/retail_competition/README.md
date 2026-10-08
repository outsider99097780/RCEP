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
