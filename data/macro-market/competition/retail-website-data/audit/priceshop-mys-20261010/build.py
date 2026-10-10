"""Offline, deterministic normalization of selected public PriceShop facts.

No network calls. Raw capture payloads are copied unchanged. Only MYS rows in
shared tables are replaced; all other market rows are compared before publish.
"""
import csv
import hashlib
import json
import pathlib
import re
import shutil
import statistics
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

BASE = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path('C:/Users/99097/Documents/GitHub/RCEP')
REL = pathlib.Path('data/macro-market/competition/retail-website-data')
OLD = REPO / REL
OUT = BASE / 'publish' / REL
BRANDS = ['Roborock', 'Ecovacs', 'Xiaomi', 'Dreame', 'Narwal']
DATE = '2026-10-10'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def readcsv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def header(rel):
    with (OLD / rel).open(encoding='utf-8-sig', newline='') as f:
        return next(csv.reader(f))

def dump(rel, obj):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def write_text(rel, content):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

def writecsv(rel, rows, fields=None):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})

def money(raw):
    return Decimal(re.sub(r'[^\d.]', '', raw))

def cents(value):
    return '' if value is None else str(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

def merge_market(rel, new_rows):
    prior = readcsv(OLD / rel)
    protected = [r for r in prior if r.get('country_code') != 'MYS']
    writecsv(rel, protected + new_rows, header(rel))
    assert [r for r in readcsv(OUT / rel) if r.get('country_code') != 'MYS'] == protected, rel

def append_rows(rel, new_rows):
    prior = readcsv(OLD / rel)
    writecsv(rel, prior + new_rows, header(rel))
    assert readcsv(OUT / rel)[:len(prior)] == prior, rel

baseline = {p.relative_to(REPO).as_posix(): digest(p) for p in OLD.rglob('*') if p.is_file()}
captures = json.loads((BASE / 'captures/products.json').read_text(encoding='utf-8'))
news = json.loads((BASE / 'captures/news.json').read_text(encoding='utf-8'))
assert len(captures) == 44 and len({r['source_product_id'] for r in captures}) == 44
assert all(r['full_reader_document_read'] for r in captures)

products, detailed, offers, specs, specs_long, ledger, crawl, crosswalk, quality = ([] for _ in range(9))

def ledger_row(sid, raw, url, title, access, kind, scope):
    return dict(source_ledger_id=sid, site='PriceShop', country_code='MYS', source_type=kind,
                source_name='PriceShop / Price Guide Sdn Bhd', base_url='https://my.priceshop.com/',
                query_or_product_url=url, query_parameters='{}', accessed_at=access, http_status='',
                page_title=title, content_sha256=digest(OUT / raw), robots_url='https://my.priceshop.com/robots.txt',
                terms_url='https://my.priceshop.com/en/wp-page/terms-of-service/', collection_scope=scope,
                raw_record_path=raw,
                citation_label=f'PriceShop（Price Guide Sdn Bhd），《{title}》，{url}，访问日期：{DATE}。' +
                ('公开网页阅读器缓存；缓存年龄见原始记录，不代表访问当日有效报价或有货。' if kind == 'cached_public_product_detail' else '历史发布报道；价格类型和发布日期见原始记录，不是当前零售报价。'))

for capture in sorted(captures, key=lambda r: r['source_product_id']):
    pid = capture['source_product_id']
    brand = next(b for b in BRANDS if capture['title_raw'].lower().startswith(b.lower()))
    model = capture['title_raw'][len(brand):].strip()
    # Preserve the site's duplicated Dreame wording in product_title/raw, clean only the model label.
    if brand == 'Dreame' and model.startswith('Dreame '):
        model = model[len('Dreame '):]
    sid = 'SRC-20261010-MYS-PS-' + pid
    raw = f'raw/MYS-PriceShop/20261010/product_{pid}.json'
    dump(raw, capture)
    ledger.append(ledger_row(sid, raw, capture['url'], capture['title_raw'], capture['accessed_at'],
                             'cached_public_product_detail', 'Selected public product, specification and visible offer fields; no current-stock confirmation or complete-site catalogue claim.'))
    sp = capture['specifications_raw']
    assert sp.get('Vacuum Type', {}).get('value_raw') == 'Robot', pid
    declared = int(re.search(r'\d+', capture['declared_seller_count_raw']).group())
    parents = {o['merchant_group_raw'] for o in capture['offers_raw']}
    flags = ['cached_page_not_live_price', 'stock_shipping_quote_freshness_unverified',
             'catalogue_census_not_verified', 'rating_reviews_rank_not_captured']
    if declared != len(parents):
        flags.append('declared_seller_count_differs_from_visible_merchant_groups')
    if pid == 'xiaomi-trouver-finder-robot-lds-vacuum-mop':
        flags.append('brand_as_labeled_by_priceshop_not_independent_ownership_verification')
    if sp.get('Suction Power', {}).get('value_raw', '').endswith(' W'):
        flags.append('source_suction_in_watts_not_convertible_to_pa')
    if sp.get('Airflow', {}).get('value_raw', '').endswith(' rpm'):
        flags.append('source_airflow_rpm_dimension_suspect_retained')
    values, by_parent, stale = [], defaultdict(list), 0
    for index, offer in enumerate(capture['offers_raw'], 1):
        value = money(offer['price_raw'])
        expired = bool(offer['quote_updated_raw'])  # Here all explicitly dated quotes say 2023-01-03.
        if expired:
            assert offer['quote_updated_raw'] == 'Updated as of 3 January 2023'
            stale += 1
        else:
            values.append(value)
            by_parent[offer['merchant_group_raw']].append(value)
        offers.append(dict(market='Malaysia', country_code='MYS', source_site='PriceShop', source_product_id=pid,
                           brand=brand, model_name=model, retailer_name=offer['retailer_name_raw'],
                           offer_price=cents(value), currency='MYR', shipping='', stock_status='not_reported_not_verified',
                           offer_url='', purchase_type='malaysia_listed_offline_or_online_quote',
                           price_type='cached_displayed_brand_new_price_not_live',
                           is_promoted='yes' if offer['promotion_notes_raw'] else 'unknown',
                           is_normal_offer='no' if expired else 'yes',
                           exclusion_reason='explicit_quote_updated_2023_stale' if expired else '',
                           accessed_at=capture['accessed_at'], source_ledger_id=sid, raw_record_path=raw,
                           offer_id=f'MYS-{pid}-{index:03}', merchant_group_raw=offer['merchant_group_raw'],
                           merchant_group_locations_raw=offer['merchant_group_locations_raw'],
                           location_raw=offer['location_raw'], price_raw=offer['price_raw'],
                           quote_updated_raw=offer['quote_updated_raw'], promotion_notes_raw=offer['promotion_notes_raw'],
                           source_price_line=offer['price_line'], source_name_line=offer['name_line'],
                           source_cache_age_raw=capture['source_cache_age_raw'],
                           source_product_url=capture['url'], qualifying_for_cached_summary=not expired,
                           eligible_for_current_verified_price_comparison=False,
                           official_authorized_distribution_verified=False, merchant_link_followed=False,
                           offer_title_scope='PriceShop product page identity; merchant SKU title not displayed',
                           condition_raw='Brand new price (page-level label)'))
    med = statistics.median(values) if values else None
    parent_med = statistics.median([statistics.median(v) for v in by_parent.values()]) if by_parent else None
    source_range = [money(v) for v in re.findall(r'RM[\d,.]+', capture['summary_price_raw'])]
    if values and (min(values) != min(source_range) or max(values) != max(source_range)):
        flags.append('source_summary_range_differs_from_captured_nonstale_quotes')
    if stale:
        flags.append('explicit_2023_quotes_excluded_from_summary')
    if len(parents) == 1:
        flags.append('single_merchant_group_even_if_multiple_branches_or_platforms')
    if len(values) == 1:
        flags.append('single_quote_not_robust_market_price')
    row = dict(market='Malaysia', country_code='MYS', source_site='PriceShop', source_product_id=pid,
               brand=brand, model_name=model, variant='', purchase_type='malaysia_listed',
               product_title=capture['title_raw'], product_url=capture['url'], first_seen_at=capture['accessed_at'],
               registration_or_release='', site_rank='', ranking_scope='', rating='', review_count='',
               seller_count=declared, currency='MYR', minimum_price=cents(min(values)) if values else '',
               maximum_price=cents(max(values)) if values else '', representative_price=cents(med),
               representative_price_method='cached_displayed_quote_median_not_current_verified' if len(values) >= 2 else 'single_cached_displayed_quote_not_current_verified',
               normal_offer_count=len(values), all_offer_count=len(capture['offers_raw']),
               collection_status='cached_public_listing_current_price_and_stock_unverified',
               data_quality_flag=';'.join(flags), source_ledger_id=sid, raw_record_path=raw)
    detail = {**row, 'accessed_at': capture['accessed_at'], 'source_cache_age_raw': capture['source_cache_age_raw'],
              'first_seen_scope': 'first observation in this collection, not product listing/release date',
              'source_provider': capture['source_provider'], 'category_raw': 'Robot',
              'source_summary_price_raw': capture['summary_price_raw'],
              'source_summary_minimum_price': cents(min(source_range)), 'source_summary_maximum_price': cents(max(source_range)),
              'visible_merchant_group_count': len(parents), 'nonstale_merchant_group_count': len(by_parent),
              'explicitly_stale_quote_count': stale, 'displayed_quote_median': cents(med),
              'merchant_balanced_median': cents(parent_med),
              'merchant_balanced_method': 'median within each merchant group, then median across groups; sensitivity only',
              'all_captured_quote_median_including_explicitly_stale': cents(statistics.median([money(o['price_raw']) for o in capture['offers_raw']])),
              'representative_price_current_verified': None,
              'eligible_for_current_verified_price_comparison': False,
              'all_visible_reader_lines_read': True, 'full_site_catalogue_coverage_verified': False,
              'rank_rating_review_status': 'not_captured_not_zero',
              'specifications_raw': sp, 'dimensions_scope': 'source scope not independently verified',
              'dust_capacity_scope': 'robot versus dock not specified by source; do not equate',
              'weight_scope': 'robot versus full system not specified by source; do not equate'}
    specrow = dict(market='Malaysia', country_code='MYS', source_site='PriceShop', source_product_id=pid,
                   brand=brand, model_name=model, specification_text=json.dumps(sp, ensure_ascii=False),
                   accessed_at=capture['accessed_at'], source_ledger_id=sid, raw_record_path=raw)
    suction = sp.get('Suction Power', {}).get('value_raw', '')
    if re.fullmatch(r'[\d,.]+\s*PA', suction, re.I):
        specrow['suction_pa'] = str(money(suction))
    for key, cell in sp.items():
        specs_long.append(dict(country_code='MYS', source_site='PriceShop', source_product_id=pid, brand=brand,
                               model_name=model, section_raw=cell['section'], attribute_raw=key, value_raw=cell['value_raw'],
                               source_attribute_line=cell['line'], source_value_line=cell['value_line'],
                               accessed_at=capture['accessed_at'], source_cache_age_raw=capture['source_cache_age_raw'],
                               product_url=capture['url'], source_ledger_id=sid, raw_record_path=raw))
    products.append(row)
    detailed.append(detail)
    specs.append(specrow)
    quality.append(dict(source_product_id=pid, flags=flags, source_ledger_id=sid))
    crosswalk.append(dict(crosswalk_group_id='XW-MYS-' + pid, brand=brand,
                          normalized_model_key=re.sub(r'[^a-z0-9+]', '', model.lower()), country_code='MYS', source_site='PriceShop',
                          source_product_id=pid, market_model_name=model, markets_in_group='MYS',
                          match_method='preserve_priceshop_identity_no_exact_cross_market_equivalence', confidence='not_verified',
                          official_equivalence_verified='no', include_in_exact_cross_market_comparison='no',
                          notes='Marketing-name similarity is not an official regional SKU match.'))
    crawl.append(dict(site='PriceShop', country_code='MYS', stage='cached_public_product_detail', brand=brand,
                      url=capture['url'], status='cached_selected_facts_captured_not_live_verified', http_status='',
                      accessed_at=capture['accessed_at'], response_sha256=digest(OUT / raw), page_title=capture['title_raw'],
                      records_found=len(capture['offers_raw']), manual_intervention_required='no', error='',
                      notes='User cancelled manual acquisition. Public web-reader cache, no HTTP status exposed. Saved hash covers selected fact JSON, not a full HTTP response.'))

historical = []
for old in readcsv(OLD / 'cleaned/launch_availability_MYS.csv'):
    historical.append({**old, 'historical_record_id': old['source_ledger_id'] + '-' + old['model_name'].replace(' ', '-'),
                       'reference_price_myr': '', 'bundle_price_myr': '', 'condition_raw': 'Historical presale; not current',
                       'eligible_for_current_verified_price_comparison': False})
for article in news:
    raw = f"raw/MYS-PriceShop/20261010/news_{article['capture_id']}.json"
    sid = 'SRC-20261010-MYS-PS-NEWS-' + article['capture_id']
    dump(raw, article)
    ledger.append(ledger_row(sid, raw, article['url'], article['title'], article['accessed_at'], article['source_type'],
                             'Selected historical article facts; launch, editorial and expired campaign/bundle prices kept distinct from product quotes.'))
    for i, item in enumerate(article['products'], 1):
        historical.append(dict(country_code='MYS', source_site='PriceShop', brand=item['brand'], model_name=item['model_name'],
                               product_type='robot_vacuum_mop', currency='MYR', official_or_list_price_raw=item.get('list_price_myr', ''),
                               promotion_price_raw=item.get('promotion_price_myr', ''), price_source_type=item['price_source_type'],
                               representative_price='', publication_date=article['publication_date'], launch_date='',
                               promotion_start=item.get('promotion_start', ''), promotion_end=item.get('promotion_end', ''),
                               current_stock_status='', availability_as_of_publication='See historical article; not checked currently',
                               reported_sales_channels='', source_ledger_id=sid, raw_record_path=raw, product_url=article['url'],
                               historical_record_id=sid + f'-{i:02}', reference_price_myr=item.get('reference_price_myr', ''),
                               bundle_price_myr=item.get('bundle_price_myr', ''), bundle_free_item=item.get('bundle_free_item', ''),
                               condition_raw=item.get('condition_raw', ''), source_price_line=item['source_line'],
                               accessed_at=article['accessed_at'], source_cache_age_raw=article['source_cache_age_raw'],
                               eligible_for_current_verified_price_comparison=False))
    crawl.append(dict(site='PriceShop', country_code='MYS', stage='historical_news', brand=';'.join(sorted({p['brand'] for p in article['products']})),
                      url=article['url'], status='historical_facts_captured_not_current_price', http_status='',
                      accessed_at=article['accessed_at'], response_sha256=digest(OUT / raw), page_title=article['title'],
                      records_found=len(article['products']), manual_intervention_required='no', error='',
                      notes='Historical source only. As-low-as campaign floor is not assigned to individual models.'))

# Shared table schemas are unchanged; detailed tables hold the extra freshness/grain fields.
merge_market('cleaned/products.csv', products)
merge_market('cleaned/retailer_offers.csv', offers)
merge_market('cleaned/specifications.csv', specs)
writecsv('cleaned/products_MYS.csv', products, header('cleaned/products.csv'))
writecsv('cleaned/products_MYS_detailed.csv', detailed)
dump('cleaned/products_MYS_detailed.json', detailed)
writecsv('cleaned/retailer_offers_MYS.csv', offers, header('cleaned/retailer_offers.csv'))
writecsv('cleaned/retailer_offers_MYS_detailed.csv', offers)
dump('cleaned/retailer_offers_MYS_detailed.json', offers)
writecsv('cleaned/specifications_MYS.csv', specs, header('cleaned/specifications.csv'))
writecsv('cleaned/specifications_MYS_long.csv', specs_long)
writecsv('cleaned/historical_price_evidence_MYS.csv', historical)
dump('cleaned/historical_price_evidence_MYS.json', historical)
append_rows('metadata/source_ledger.csv', ledger)
writecsv('metadata/source_ledger_MYS.csv', readcsv(OLD / 'metadata/source_ledger_MYS.csv') + ledger, header('metadata/source_ledger.csv'))
append_rows('metadata/crawl_log.csv', crawl)
writecsv('logs/crawl_MYS.csv', readcsv(OLD / 'logs/crawl_MYS.csv') + crawl, header('metadata/crawl_log.csv'))
merge_market('metadata/model_crosswalk.csv', crosswalk)
writecsv('metadata/model_crosswalk_MYS.csv', crosswalk, header('metadata/model_crosswalk.csv'))

summary, positioning = [], []
market_values = [Decimal(r['representative_price']) for r in products if r['representative_price']]
market_median = statistics.median(market_values)
for brand in BRANDS:
    subset = [r for r in products if r['brand'] == brand]
    values = [Decimal(r['representative_price']) for r in subset if r['representative_price']]
    median = statistics.median(values) if values else None
    summary.append(dict(country_code='MYS', brand=brand, currency='MYR', sku_count=len(subset),
                        minimum_representative_price=cents(min(values)) if values else '',
                        median_representative_price=cents(median), maximum_representative_price=cents(max(values)) if values else '',
                        median_price_index_vs_market=cents(median / market_median) if median is not None else '',
                        average_seller_count=str(statistics.mean([Decimal(r['seller_count']) for r in subset])) if subset else '',
                        rating_coverage_rate='', review_count_coverage_rate='',
                        notes='Cached listed SKU mix, not current prices/sales/share or a full-site census. Blank ratings/reviews were not captured. Narwal historical evidence only.' if brand == 'Narwal' else 'Cached displayed quote medians, explicit 2023 quotes excluded; unknown stock/shipping and heterogeneous cache ages; descriptive only, not current verified price.'))
    dump(f'cleaned/by-brand/MYS/{brand}.json', dict(country_code='MYS', source_site='PriceShop', brand=brand,
                                                collection_date=DATE, complete_site_catalogue_verified=False,
                                                current_verified_price_coverage=0,
                                                products=[r for r in detailed if r['brand'] == brand],
                                                historical_evidence=[r for r in historical if r['brand'] == brand]))
for row in products:
    value = Decimal(row['representative_price'])
    positioning.append(dict(country_code='MYS', brand=row['brand'], source_product_id=row['source_product_id'],
                            model_name=row['model_name'], currency='MYR', representative_price=row['representative_price'],
                            market_median_price=cents(market_median), price_index_vs_market_median=cents(value / market_median),
                            market_quartile_segment='', seller_count=row['seller_count'], site_rank='',
                            descriptive_only='cached_not_current_verified_no_sales_inference', source_ledger_id=row['source_ledger_id']))
merge_market('analysis/brand_summary.csv', summary)
merge_market('analysis/brand_summary_NZL_MYS.csv', summary)
merge_market('analysis/price_positioning.csv', positioning)
writecsv('analysis/brand_summary_MYS.csv', summary, header('analysis/brand_summary.csv'))
writecsv('analysis/price_positioning_MYS.csv', positioning, header('analysis/price_positioning.csv'))
dump('analysis/quality_flags_MYS.json', quality)

discovery_raw = 'raw/MYS-PriceShop/20261010/discovery_manifest.json'
dump(discovery_raw, json.loads((BASE / 'captures/discovery.json').read_text(encoding='utf-8')))
dump('raw/MYS-PriceShop/20261010/query_log.json', json.loads((BASE / 'captures/queries.json').read_text(encoding='utf-8')))
dump('raw/MYS-PriceShop/20261010/access_review.json', json.loads((BASE / 'captures/access_review.json').read_text(encoding='utf-8')))
coverage = dict(snapshot_date=DATE, only_source='PriceShop', public_reader_product_pages=len(products),
                by_brand=dict(Counter(p['brand'] for p in products)), captured_offer_rows=len(offers),
                nonstale_cached_quote_rows=sum(o['qualifying_for_cached_summary'] for o in offers),
                explicitly_stale_quote_rows=sum(not o['qualifying_for_cached_summary'] for o in offers),
                specification_field_rows=len(specs_long), historical_article_sources=9,
                historical_price_evidence_rows=len(historical), current_verified_price_skus=0,
                narwal_product_pages_found=0, narwal_historical_price_rows=sum(r['brand'] == 'Narwal' for r in historical),
                full_site_catalogue_coverage_verified=False, all_selected_product_reader_documents_read=True,
                manual_collection_cancelled=True, missing_brand_current_catalogue=['Narwal'],
                current_price_qualified_skus=0, current_price_coverage='not_verified_cached_data_only',
                manual_PriceMe_plan_cancelled=True,
                incomplete_visible_merchant_group_pages=[r['source_product_id'] for r in quality if 'declared_seller_count_differs_from_visible_merchant_groups' in r['flags']],
                limitations=['Category page returned undefined/no products; this is not evidence of an empty catalogue.',
                             'No complete catalogue or product/offer pagination verification is available from the public reader.',
                             'Retrieved product cache ages range from today to over one year; no quote is certified current.',
                             'All stock and shipping are unknown; no merchant redirect was followed.',
                             'Narwal product listings were not found; only historical PriceShop articles were obtained.',
                             'Full reader document read does not mean all merchant offers on the live site were returned.'])
dump('analysis/coverage_MYS_20261010.json', coverage)
old_coverage = json.loads((OLD / 'analysis/coverage_NZL_MYS.json').read_text(encoding='utf-8'))
old_coverage['mys'] = coverage
dump('analysis/coverage_NZL_MYS.json', old_coverage)
config = json.loads((OLD / 'config/market_expansion_20261010.json').read_text(encoding='utf-8'))
config['mys_latest_collection'] = dict(source='PriceShop only', mode='public cached web-reader facts',
                                        live_access_or_bypass='No new direct HTTP crawl, hidden API, mirror, credentials, CAPTCHA or merchant redirects used.',
                                        manual_collection_cancelled=True, full_catalogue_verified=False,
                                        representative_price_semantics='median of cached displayed new quotes excluding explicit 2023 updates; not current verified price',
                                        merchant_sensitivity='Per-group median then across-group median additionally supplied.',
                                        history='Separate historical_price_evidence_MYS; never mixed into retail offer medians',
                                        source_cache_age='Relative label copied as reported; exact cache timestamp not inferred')
config['policy_review_notes'].append('Subsequent user-authorized collection retrieved publicly indexed PriceShop cached pages only. Earlier direct HTTP403 remains historical; not bypassed or overwritten.')
dump('config/market_expansion_20261010.json', config)

report = f'''# 马来西亚 PriceShop 采集结果（{DATE}）

本轮只用 PriceShop，人工采集已取消。获取的是公开网页阅读器返回的缓存事实，不是对当日库存和结算价格的确认。五品牌的完整实时商品目录尚未取得。

| 品牌 | 商品页 | 历史价格证据行 |
|---|---:|---:|
''' + ''.join(f"| {b} | {sum(r['brand']==b for r in products)} | {sum(r['brand']==b for r in historical)} |\n" for b in BRANDS) + f'''
共 {len(products)} 个机器人商品页、{len(offers)} 条商家/门店/平台报价、{len(specs_long)} 个原始参数字段；{coverage['explicitly_stale_quote_rows']} 条报价明确写着 2023-01-03 更新，保留在明细中但排除出汇总。历史报道单独存储，共 {len(historical)} 条价格证据，来自 9 篇 PriceShop 文章。

## 读取入口

- `cleaned/products_MYS_detailed.json` / `.csv`：商品、来源、原始参数、缓存年龄、显示报价中位数、按商家组平衡的中位数。
- `cleaned/retailer_offers_MYS_detailed.json` / `.csv`：全部可读报价；明确区分商家组、门店、平台、过期更新和未知库存/运费。
- `cleaned/specifications_MYS_long.csv`：参数逐字段来源，保留原始单位和值。
- `cleaned/historical_price_evidence_MYS.json` / `.csv`：上市价、编辑参考价、预售价、活动价、捆绑价；不进入商品报价中位数。
- `cleaned/by-brand/MYS/`：五品牌分别的商品与历史证据。
- `metadata/source_ledger_MYS.csv`：主体、URL、访问日期、引用文字、原始记录路径及 SHA-256。
- `raw/MYS-PriceShop/20261010/`：本轮不可变的选定公开事实快照和检索发现清单；不是整页 HTML 镜像。

## 价格字段的含义

`representative_price` 是**缓存页面显示报价的中位数**，不是访问当日已验证价格。仅排除有明确 2023 年更新标记的报价；其余报价的新旧日期仍未知。该字段保留原结构便于调用，方法及质量标记必须一起读取。`representative_price_current_verified` 一律为空，`eligible_for_current_verified_price_comparison` 一律为 false。

同一商家可能有多个门店和电商平台报价，不能据此声称独立竞争商家数量增加。原始报价全部保留；`merchant_balanced_median` 先求商家组内中位数，再求组间中位数，供检查门店重复权重。中位数不含未知运费，不使用汇率换算，不等于成交价或企业 ASP。

## 尚未完整的部分

分类页返回 `undefined results found / No products are here`，未得到可核对的完整目录。通过逐品牌公开检索及已见链接取得的 44 页不能证明全站 SKU 已收齐。4 页声明商家数与可见商家组数不同，见 `analysis/coverage_MYS_20261010.json`；未臆造缺失商家或分页。

云鲸没有取得可读商品报价页，只有 2025 年上市/预售及 2026 年开店活动证据。没有把它记作“马来西亚未销售”，也没有把新闻价格补进当前零售报价。开店文章中的 RM1,399 是多个型号活动的合并最低起价，没有分配给每个型号。

缓存年龄原样保留，部分超过一年；检索摘要和打开的缓存版本可能不同，以该条原始记录对应的完整阅读器版本为准，不混合版本。真实 HTTP 状态未由阅读器暴露，台账留空。旧的直接访问 403 记录仍保留为历史记录。

机器人与基站的容量/重量范围未明确时不强行统一；源站用 W 表示吸力或 rpm 表示气流的字段原样保存并标记，不改成 Pa。评分、评论数、销量和排名未取得时留空，不补零。

## 来源与可重复性

清洗表按 `source_ledger_id` 连接来源台账。原始快照保存 URL、访问时间、缓存标签及字段定位；SHA-256 仅覆盖保存的事实 JSON，不冒充完整 HTTP 响应校验。规范化脚本与采集输入在 `audit/priceshop-mys-20261010/`，可离线重算。原日本、韩国、澳大利亚、新西兰逐国文件保持不变；共享表只替换 MYS 业务行，台账和访问日志追加。
'''
write_text('analysis/priceshop_MYS_20261010.md', report)
readme = (OLD / 'README.md').read_text(encoding='utf-8')
old_para = 'PriceShop 目前仅有2025年两款 Narwal 机器人的上市价/预售价证据，当前代表价留空；其他四品牌未取得可用当前价格。详情和访问限制见 `analysis/market_expansion_20261010.md`。上市新闻不等于当前零售价，未收集不等于当地无销售。'
assert old_para in readme
readme = readme.replace(old_para, 'PriceShop 马来西亚现有数据更新见 `analysis/priceshop_MYS_20261010.md`：44个商品页、281条缓存报价，另有独立保存的历史价格证据。人工采集已取消。商品汇总的代表价明确是缓存显示价，不是访问当日已验证价格；五品牌完整实时目录尚未取得，云鲸仍缺商品报价页。较早的访问限制见 `analysis/market_expansion_20261010.md`，仅代表之前那轮状态。')
readme += '\n## 马来西亚专用价格与审计约定\n\nMYS 的原结构价格列须同时读取 `representative_price_method`、`collection_status` 和 `data_quality_flag`。新增详细表提供缓存年龄、商家组平衡中位数和 `eligible_for_current_verified_price_comparison=false`。历史新闻、捆绑活动与商品报价分表保存，来源唯一为 PriceShop。未确认完整目录，不把本次样本的品牌均价解读为全国品牌价格或销售表现。\n'
write_text('README.md', readme)
write_text('analysis/data_quality_report.md', (OLD / 'analysis/data_quality_report.md').read_text(encoding='utf-8') + '\n\n## 马来西亚 PriceShop 更新\n\n本轮状态及规则以 `priceshop_MYS_20261010.md` 和 `coverage_MYS_20261010.json` 为准。44个商品页、281条缓存报价，其中10条明确2023年更新的报价排除出汇总。五品牌完整实时目录未取得，云鲸只有历史证据；其他国家结果未重算。\n')
write_text('analysis/market_expansion_20261010.md', '> 状态更新：本文件记录较早的采集批次。马来西亚最新状态、缓存报价和来源以 `priceshop_MYS_20261010.md` 为准；本文件原有内容保留作历史过程记录。\n\n' + (OLD / 'analysis/market_expansion_20261010.md').read_text(encoding='utf-8'))

# Evidence integrity and conservative join checks before creating a publication manifest.
assert len(offers) == 281 and len(specs_long) == 247 and len(historical) == 26
assert sum(not r['qualifying_for_cached_summary'] for r in offers) == 10
assert all(not r['eligible_for_current_verified_price_comparison'] for r in offers)
all_ledger = readcsv(OUT / 'metadata/source_ledger.csv')
assert len(all_ledger) == len({r['source_ledger_id'] for r in all_ledger})
ids = {r['source_ledger_id'] for r in all_ledger}
for row in [*products, *offers, *specs_long, *historical]:
    assert row['source_ledger_id'] in ids
    rawpath = OUT / row['raw_record_path']
    assert rawpath.is_file() or (OLD / row['raw_record_path']).is_file()
for row in ledger:
    assert digest(OUT / row['raw_record_path']) == row['content_sha256']
for capture in captures:
    saved = json.loads((OUT / f"raw/MYS-PriceShop/20261010/product_{capture['source_product_id']}.json").read_text(encoding='utf-8'))
    assert saved == capture

# Archive transformation companion and exact selected inputs; no live crawl is reproduced here.
for name in ['build.py', 'reader_fact_extractor.js', 'verify.py']:
    write_text('audit/priceshop-mys-20261010/' + name, (BASE / name).read_text(encoding='utf-8'))
write_text('audit/priceshop-mys-20261010/README.md', (BASE / 'AUDIT_README.md').read_text(encoding='utf-8'))
for name in ['products.json', 'news.json', 'discovery.json', 'queries.json', 'access_review.json']:
    dump('audit/priceshop-mys-20261010/inputs/' + name, json.loads((BASE / 'captures' / name).read_text(encoding='utf-8')))
dump('audit/priceshop-mys-20261010/validation.json', dict(passed=True, counts=coverage,
      unchanged_non_mys_shared_rows=True, existing_raw_files_not_overwritten=True,
      raw_fact_payloads_roundtrip_equal=True, source_ledger_ids_unique=True,
      source_ledger_hashes_valid=True, all_cleaned_records_have_resolvable_sources=True,
      input_hashes={p.name: digest(p) for p in (BASE / 'captures').glob('*.json')}))
manifest = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        rel = (REL / path.relative_to(OUT)).as_posix()
        manifest.append(dict(relative_path=rel, staged_sha256=digest(path), expected_existing_sha256=baseline.get(rel)))
(BASE / 'publication-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
(BASE / 'baseline.json').write_text(json.dumps(baseline, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(products=len(products), offers=len(offers), specs=len(specs_long), historical=len(historical),
                      by_brand=coverage['by_brand'], staged_files=len(manifest), validation='passed'), ensure_ascii=False))
