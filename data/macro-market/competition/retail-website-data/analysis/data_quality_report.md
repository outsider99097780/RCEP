# Data quality report

Generated: 2026-10-02T22:53:45+08:00

## Dataset and grain

- `cleaned/products.csv`: one row per source-site product ID; 170 rows.
- `cleaned/retailer_offers.csv`: one row per parsed visible retailer offer; 1014 rows.
- `cleaned/specifications.csv`: one row per product-detail page; 170 rows.
- Market row counts: {'JPN': 63, 'AUS': 19, 'KOR': 88}.

## Checks performed

- Composite-key uniqueness: `(source_site, source_product_id)`.
- Missing representative price, low normal-offer count, local-currency consistency and Korean overseas-purchase separation.
- Specification missingness for major comparable fields.
- Crawl failures and explicit no-fabrication/manual-takeover flags.

## Findings

| Check | Result | Severity | Interpretation |
|---|---:|---|---|
| Duplicate product keys | 0 | Low | Duplicate keys would mix product grain; none are retained when zero. |
| Missing representative price | 14/170 | Medium | Blank means no qualifying normal market price or an intentionally excluded overseas purchase; never zero-filled. |
| Fewer than 3 normal offers | 46/170 | Medium | Representative price uses the lowest available normal offer rather than a median. |
| Korean overseas-purchase rows | 14 | Low | Stored with `purchase_type=overseas_purchase` and excluded from Korea's representative-price analysis. |
| Non-success crawl events | 0 | Low | Status breakdown: {}. No bypass or invented substitute data was used. |

## Specification missingness

{
  "suction_pa": 45,
  "navigation_sensor": 54,
  "threshold_climb_cm": 113,
  "robot_height_mm": 97
}

Specification fields are populated only when the public page exposes a parseable value. Empty cells are not interpreted as absence of the feature.

## Coverage and analytical risk

- This is a targeted public-page snapshot, not a complete historical or full-site crawl. Each brand/site is capped at 20 selected product-detail pages in public listing order.
- Site rankings are not sales data. Kakaku rank is a site category rank, Danawa stores the captured search position, and GetPrice rank is blank by design.
- Retail prices are local-currency observations at collection time. No exchange-rate conversion or cross-country absolute price comparison is performed.
- Model crosswalk matches marketing names only and never marks official regional equivalence as verified.

## Recommended use

Use the snapshot for descriptive SKU breadth, visible price bands, seller coverage and specification screening. Re-collect before publication if freshness matters, and manually verify any exact cross-market model equivalence or unusually low/high offer used in a report.

## Cleaning exclusions

9 records were retained in the raw/source-ledger layers and listed in `cleaned/excluded_products.csv`, but removed from the floor robot-vacuum analytical tables because they were window-cleaning robots, bundles containing a window-cleaning robot, or accessories/consumables.
