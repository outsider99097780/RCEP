"""Read-only verification; use --published after guarded publication."""
import argparse
import csv
import hashlib
import json
import pathlib
import statistics
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

BASE = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path('C:/Users/99097/Documents/GitHub/RCEP')
REL = pathlib.Path('data/macro-market/competition/retail-website-data')
arg = argparse.ArgumentParser()
arg.add_argument('--published', action='store_true')
arg.add_argument('--data-root', type=pathlib.Path)
options = arg.parse_args()
ROOT = options.data_root or ((REPO / REL) if options.published else BASE / 'publish' / REL)

def rows(rel):
    with (ROOT / rel).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def raw_money(value):
    return Decimal(value.replace('RM', '').replace(',', '').strip())

def rounded(value):
    return str(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

products = json.loads((ROOT / 'cleaned/products_MYS_detailed.json').read_text(encoding='utf-8'))
offers = json.loads((ROOT / 'cleaned/retailer_offers_MYS_detailed.json').read_text(encoding='utf-8'))
specs = rows('cleaned/specifications_MYS_long.csv')
ledger = {r['source_ledger_id']: r for r in rows('metadata/source_ledger.csv')}
assert len(products) == 44 and len(offers) == 281 and len(specs) == 247
assert len(ledger) == len(rows('metadata/source_ledger.csv'))
stale = 0
for product in products:
    pid = product['source_product_id']
    raw = json.loads((ROOT / product['raw_record_path']).read_text(encoding='utf-8'))
    assert raw['title_raw'] == product['product_title']
    assert raw['url'] == product['product_url']
    assert raw['source_cache_age_raw'] == product['source_cache_age_raw']
    assert raw['specifications_raw'] == product['specifications_raw']
    assert raw['full_reader_document_read'] is True
    assert raw['specifications_raw']['Vacuum Type']['value_raw'] == 'Robot'
    subset = [o for o in offers if o['source_product_id'] == pid]
    assert len(subset) == len(raw['offers_raw']) == product['all_offer_count']
    valid, groups = [], defaultdict(list)
    for normalized, original in zip(subset, raw['offers_raw']):
        for nk, ok in [('retailer_name','retailer_name_raw'),('merchant_group_raw','merchant_group_raw'),
                       ('location_raw','location_raw'),('quote_updated_raw','quote_updated_raw'),
                       ('price_raw','price_raw'),('promotion_notes_raw','promotion_notes_raw')]:
            assert normalized[nk] == original[ok], (pid, nk)
        amount = raw_money(original['price_raw'])
        assert normalized['offer_price'] == rounded(amount)
        assert normalized['eligible_for_current_verified_price_comparison'] is False
        assert normalized['merchant_link_followed'] is False
        assert normalized['source_ledger_id'] == product['source_ledger_id']
        if original['quote_updated_raw']:
            stale += 1
            assert normalized['is_normal_offer'] == 'no'
        else:
            assert normalized['is_normal_offer'] == 'yes'
            valid.append(amount)
            groups[original['merchant_group_raw']].append(amount)
    assert product['normal_offer_count'] == len(valid)
    assert product['minimum_price'] == rounded(min(valid))
    assert product['maximum_price'] == rounded(max(valid))
    assert product['representative_price'] == rounded(statistics.median(valid))
    assert product['merchant_balanced_median'] == rounded(statistics.median([statistics.median(v) for v in groups.values()]))
    assert product['representative_price_current_verified'] is None
    assert product['eligible_for_current_verified_price_comparison'] is False
    source = ledger[product['source_ledger_id']]
    assert source['query_or_product_url'] == raw['url']
    assert source['content_sha256'] == sha(ROOT / product['raw_record_path'])
    assert raw['url'] in source['citation_label'] and '2026-10-10' in source['citation_label']
    normalized_specs = [s for s in specs if s['source_product_id'] == pid]
    assert len(normalized_specs) == len(raw['specifications_raw'])
    for spec in normalized_specs:
        assert spec['value_raw'] == raw['specifications_raw'][spec['attribute_raw']]['value_raw']
assert stale == 10
historical = json.loads((ROOT / 'cleaned/historical_price_evidence_MYS.json').read_text(encoding='utf-8'))
assert len(historical) == 26 and {r['brand'] for r in historical} == {'Roborock','Ecovacs','Xiaomi','Dreame','Narwal'}
assert all(not r['representative_price'] for r in historical)
assert all(r['source_ledger_id'] in ledger for r in historical)
assert len(rows('cleaned/products_MYS.csv')) == 44
assert len(rows('cleaned/retailer_offers_MYS.csv')) == 281
assert [r['model_name'] for r in rows('cleaned/products_MYS.csv')] == [r['model_name'] for r in products]
for path in (ROOT / 'raw/MYS-PriceShop/20261010').glob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))

if (BASE / 'baseline.json').is_file():
    baseline = json.loads((BASE / 'baseline.json').read_text())
    manifest = json.loads((BASE / 'publication-manifest.json').read_text())
    changed = {r['relative_path'] for r in manifest}
    for rel, expected in baseline.items():
        if rel not in changed:
            assert sha(REPO / rel) == expected, 'Unrelated existing file changed: ' + rel
    if options.published:
        for entry in manifest:
            assert sha(REPO / entry['relative_path']) == entry['staged_sha256']
        for rel in ['cleaned/products.csv','cleaned/retailer_offers.csv','cleaned/specifications.csv',
                    'analysis/brand_summary.csv','analysis/brand_summary_NZL_MYS.csv',
                    'analysis/price_positioning.csv','metadata/model_crosswalk.csv']:
            prior = BASE / 'pre-publication-backup' / REL / rel
            with prior.open(encoding='utf-8-sig', newline='') as f:
                protected = [r for r in csv.DictReader(f) if r.get('country_code') != 'MYS']
            assert [r for r in rows(rel) if r.get('country_code') != 'MYS'] == protected
print(json.dumps(dict(passed=True, mode='published' if options.published else 'staged', products=44,
                      offers=281, specification_fields=247, historical_price_records=26,
                      stale_quotes_excluded=10, current_verified_prices=0), ensure_ascii=False))
