"""Rebuild the established ITC screening model from the current, read-only data pack.

Usage: python rebuild_itc_model.py --raw ../ITC-data --output .
The generator writes new outputs but never deletes files or edits the data pack.
Publication/removal of obsolete files is a separate, explicitly scoped operation.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import math
import platform
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True

INDICATORS = ['market_size', 'market_growth', 'china_share', 'untapped_amount', 'untapped_ratio']
STRATEGY = np.array([.30, .10, .10, .30, .20])
SEED, DRAWS, CONCENTRATION = 850980, 5000, 40
HS = '850811'
VERSION = 'ITC query HS6 850811 aggregate; HS revision not declared in stored Trade Map response'
NAMES = {'036':'澳大利亚','096':'文莱','116':'柬埔寨','360':'印度尼西亚','392':'日本',
         '410':'韩国','418':'老挝','458':'马来西亚','104':'缅甸','554':'新西兰',
         '608':'菲律宾','702':'新加坡','764':'泰国','704':'越南'}
ISO = {'036':'AUS','096':'BRN','116':'KHM','360':'IDN','392':'JPN','410':'KOR',
       '418':'LAO','458':'MYS','104':'MMR','554':'NZL','608':'PHL','702':'SGP','764':'THA','704':'VNM'}

def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def number(x):
    if x is None or x == '' or str(x).lower() in ('n/a', 'na', 'null', '...','-'):
        return None
    ans = float(x)
    assert math.isfinite(ans)
    return ans

def save_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0])
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='raise')
        w.writeheader()
        w.writerows(rows)

def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def save_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip()+'\n', encoding='utf-8')

def series(data, key, reporter, partner):
    matches = [r for r in data.get(key, []) if r['reporterCd'] == reporter and
               r['partnerCd'] == partner and r['productCd'] == HS]
    assert len(matches) <= 1, ('nonunique aggregate', reporter, partner)
    return {int(d['period']): number(d.get('value')) for d in matches[0]['data']} if matches else {}

def cagr(start, end, years):
    return ((end/start)**(1/years)-1)*100 if start is not None and start > 0 and end is not None and end >= 0 else None

def transform(rows, growth=None, use_log=True):
    x = np.array([[r['imports_2025_usd_thousand'], r['import_cagr_2020_2025_pct'],
                   r['china_share_2025_pct'], r['untapped_potential_usd'],
                   r['untapped_potential_usd']/r['epi_potential_usd']] for r in rows], dtype=float)
    if growth is not None:
        x[:,1] = growth
    if use_log:
        x[:,[0,3]] = np.log1p(x[:,[0,3]])
    lo, hi = x.min(axis=0), x.max(axis=0)
    assert np.all(hi > lo), 'A constant indicator needs explicit exclusion and weight renormalization'
    return x, (x-lo)/(hi-lo), lo, hi

def topsis(z, weights):
    v = z*weights
    positive, negative = v.max(axis=0), v.min(axis=0)
    dp = np.sqrt(((v-positive)**2).sum(axis=1))
    dm = np.sqrt(((v-negative)**2).sum(axis=1))
    assert np.all(dp+dm > 0)
    scores = dm/(dp+dm)
    ranks = np.argsort(np.argsort(-scores, kind='stable'), kind='stable')+1
    return scores, ranks, v, positive, negative, dp, dm

def entropy(z):
    p = z/z.sum(axis=0)
    plnp = np.zeros_like(p)
    good = p > 0
    plnp[good] = p[good]*np.log(p[good])
    e = -plnp.sum(axis=0)/np.log(len(z))
    div = 1-e
    return div/div.sum(), p, e, div

def run(raw: Path, output: Path):
    raw, output = raw.resolve(), output.resolve()
    assert raw.is_dir() and raw.name == 'ITC-data'
    assert output != raw and raw not in output.parents, 'Outputs cannot be inside the raw data pack'
    output.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    run_id = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%dT%H%M%S')+'-CHN-HS850811-RCEP-TOPSIS'
    original_files = {str(p.relative_to(raw)).replace('\\','/'):sha(p) for p in raw.rglob('*') if p.is_file()}
    manifest = load_json(raw/'manifest.json')
    assert manifest['itc_hs6'] == HS
    countries = manifest['countries']
    assert len(countries) == 14 and len({c['code'] for c in countries}) == 14
    original_ledger = read_csv(raw/'source-ledger-master.csv')
    slug_codes = {c['slug']:c['code'] for c in countries}
    ledger, aliases = [], []
    for original in original_ledger:
        r = dict(original)
        r['original_source_id'] = original['source_id']
        if original['source_id'].startswith('MACMAP-'):
            path = Path(original['raw_file'].replace('\\','/'))
            code = slug_codes[path.parts[0]]
            kind = 'NTL' if path.stem.startswith('destination_ntl') else 'DUTY' if path.stem.startswith('custom_duties') else 'NTM'
            r['source_id'] = f'MACMAP-{code}-{kind}-{path.stem.split("_")[-1]}'
            r['country_code'] = code
        aliases.append({'original_source_id':original['source_id'],'source_id':r['source_id'],
                        'raw_file':r['raw_file'],'sha256':r['sha256'],
                        'reason':'country + response type + national tariff line disambiguation' if r['source_id']!=original['source_id'] else 'unchanged'})
        ledger.append(r)
    sources = {r['source_id']:r for r in ledger}
    assert len(sources) == len(ledger)
    for r in ledger:
        assert r['url'] and r['accessed_at'] and r['query_parameters']
        assert sha(raw/r['raw_file'].replace('\\','/')) == r['sha256'], ('source checksum mismatch',r['source_id'])
        assert r['hs_or_product_code'] == HS or r['source_id']=='TM-COUNTRY-REF', ('wrong product in current ledger',r['source_id'])
    source_by_path = {r['raw_file'].replace('\\','/'):r['source_id'] for r in ledger}
    copied_input = read_csv(raw/'_modeling-output/rcep_country_comparison_model_inputs.csv')
    assert {r['country_code'] for r in copied_input} == {c['code'] for c in countries}
    numeric_columns = [k for k in copied_input[0] if k not in ('country_code','country_name','source_ids')]
    rows = [{k:number(v) if k in numeric_columns else v for k,v in r.items()} for r in copied_input]
    by_code = {r['country_code']:r for r in rows}
    checks, lineage, clean_log, annual, epi_rows, tariff_rows, ntm_rows, coverage = [],[],[],[],[],[],[],[]
    def check(name, actual, expected, tol=1e-8, code=''):
        ok = (actual is None and expected is None) or (actual is not None and expected is not None and math.isclose(float(actual),float(expected),rel_tol=tol,abs_tol=tol))
        checks.append({'check_id':f'QA-{len(checks)+1:04d}','country_code':code,'check':name,'actual':actual,'expected':expected,'passed':ok})
        assert ok, (name,code,actual,expected)
    def add_line(c, field, ids, locator, formula, period, unit, value):
        selected = [sources[s] for s in ids]
        lineage.append({'country_code':c['code'],'country_name':c['name'],'field':field,'value':value,
                        'unit':unit,'period':period,'hs_code':HS,'hs_version':VERSION,
                        'source_ids':';'.join(ids),'raw_files':';'.join(r['raw_file'].replace('\\','/') for r in selected),
                        'raw_locators':locator,'formula':formula,'transformation_id':f'CLEAN-{c["code"]}',
                        'accessed_at':';'.join(sorted({r['accessed_at'] for r in selected})),
                        'query_urls':';'.join(r['url'] for r in selected),
                        'source_sha256':';'.join(r['sha256'] for r in selected),
                        'clean_table':'model_inputs.csv','clean_row_key':c['code']})
    all_decoded = load_json(raw/'_shared/export-potential-map/china_hs850811_all_markets_epi.decoded.json')
    decoded_by_code = {str(r['item']['code']).zfill(3):r for r in all_decoded}
    growth3 = {}
    for c in countries:
        code, slug, row = c['code'],c['slug'],by_code[c['code']]
        imp_rel = f'{slug}/trade-map/{slug}_imports_from_world_hs850811_2020-2025_by_supplier_val.json'
        exp_rel = f'{slug}/trade-map/china_exports_to_{slug}_hs850811_2020-2025_val.json'
        imp, exp = load_json(raw/imp_rel),load_json(raw/exp_rel)
        world = series(imp,'aggregateRecords',code,'000')
        from_china = series(imp,'records',code,'156')
        direct = series(exp,'aggregateRecords','156',code)
        supplier_values = [(r['partnerCd'],next((number(d['value']) for d in r['data'] if int(d['period'])==2025),None))
                           for r in imp.get('records',[]) if r['productCd']==HS and r['partnerCd']!='000']
        suppliers = sorted([(p,v) for p,v in supplier_values if v is not None], key=lambda pair:-pair[1])
        supplier_rank = next((i+1 for i,(p,v) in enumerate(suppliers) if p=='156'),None)
        w2025, w2020 = world.get(2025),world.get(2020)
        share = from_china.get(2025)/w2025*100 if from_china.get(2025) is not None and w2025 else None
        cg = cagr(w2020,w2025,5)
        growth3[code] = cagr(world.get(2022),w2025,3)
        check('model imports vs raw aggregateRecords',row['imports_2025_usd_thousand'],w2025,code=code)
        check('model CAGR vs raw endpoints; input rounded to 4 decimals',row['import_cagr_2020_2025_pct'],None if cg is None else round(cg,4),code=code)
        check('model China share vs import reporter; input rounded to 4 decimals',row['china_share_2025_pct'],None if share is None else round(share,4),code=code)
        check('model China supplier rank vs raw records',row['china_rank_2025'],supplier_rank,code=code)
        sid_imp, sid_exp = source_by_path[imp_rel], source_by_path[exp_rel]
        for year in range(2020,2026):
            annual.append({'country_code':code,'country_name':c['name'],'year':year,'hs_code':HS,
                           'world_imports_usd_thousand':world.get(year),'imports_from_china_usd_thousand':from_china.get(year),
                           'china_direct_exports_usd_thousand':direct.get(year),
                           'world_imports_raw':world.get(year),'china_imports_raw':from_china.get(year),
                           'value_unit_raw':'USD thousand','reporting_basis':'direct_import; direct_export separate',
                           'import_source_id':sid_imp,'export_source_id':sid_exp,
                           'missing_reason':'not_available_in_raw_response' if world.get(year) is None else ''})
        common_locator=f'aggregateRecords[reporterCd={code},partnerCd=000,productCd=850811].data'
        for field,value,loc,form,period,unit in [
            ('imports_2025_usd_thousand',row['imports_2025_usd_thousand'],common_locator+'[period=2025].value','copy aggregate; no summation of HS child records','2025','USD thousand'),
            ('import_cagr_2020_2025_pct',row['import_cagr_2020_2025_pct'],common_locator+'[period=2020|2025].value','round(((M2025/M2020)^(1/5)-1)*100,4)','2020-2025','percent'),
            ('china_share_2025_pct',row['china_share_2025_pct'],common_locator+'[period=2025]; records[partnerCd=156].data[period=2025]','round(China_imports/World_imports*100,4)','2025','percent'),
            ('china_rank_2025',row['china_rank_2025'],'records[productCd=850811].data[period=2025]','descending import value; exclude World row','2025','rank')]:
            add_line(c,field,[sid_imp],loc,form,period,unit,value)
        epi_rel=f'{slug}/export-potential-map/official_epi_record_hs850811.json'
        ep=load_json(raw/epi_rel)
        assert ep == decoded_by_code[code], ('EPM extract not identical to official decoded response',code)
        potential, baseline = ep['value'],ep['exportValue']
        untapped = max(potential-baseline,0)
        check('EPM potential',row['epi_potential_usd'],potential,code=code)
        check('EPM baseline',row['baseline_exports_usd'],baseline,code=code)
        check('EPM derived untapped amount',row['untapped_potential_usd'],untapped,code=code)
        check('EPM rank',row['epi_rank'],ep['rank'],code=code)
        check('EPM official gap ratio vs derived amount; official ratio rounding tolerance',ep['gap'],untapped/potential,tol=1e-9,code=code)
        epi_rows.append({'country_code':code,'country_name':c['name'],'hs_code':HS,
                         'itc_product_group_id':HS,'epi_potential_usd':potential,'baseline_exports_usd':baseline,
                         'untapped_potential_usd':untapped,'untapped_ratio':untapped/potential,
                         'official_gap_ratio':ep['gap'],'official_realized_ratio':ep['realizedPotential'],
                         'official_rank':ep['rank'],'projection_horizon':'2030 (interface note in saved derived table; not present in raw record)',
                         'projection_horizon_status':'saved_interface_note_not_independently_captured',
                         'amount_status':'potential and baseline official; untapped amount researcher arithmetic from official values',
                         'source_id':f'EPM-{code}','transport_source_id':'EPM-ALL-ENC','decoded_source_id':'EPM-ALL-DEC'})
        for f,k,formula,unit in [('epi_potential_usd','value','copy official field','USD'),
                               ('baseline_exports_usd','exportValue','copy official field','USD'),
                               ('untapped_potential_usd','value; exportValue','max(value-exportValue,0)','USD'),
                               ('epi_rank','rank','copy official field','rank')]:
            add_line(c,f,[f'EPM-{code}'],k,formula,'EPM current snapshot',unit,row[f])
        tariff = read_csv(raw/slug/'derived/tariff_summary.csv')
        tariff_ids=[]
        percentages=[]
        for t in tariff:
            path=t['raw_source_file'].replace('\\','/')
            sid=source_by_path[path]
            tariff_ids.append(sid)
            raw_tariff=load_json(raw/path)
            assert any(str(d['NTLCCode'])==t['ntl_code'] and d['TariffRegime']==t['tariff_regime'] and d['TariffReported']==t['applied_tariff'] for d in raw_tariff.get('CustomDuty',[]))
            text=t['applied_tariff'].strip()
            if text.endswith('%'):
                try: percentages.append(float(text[:-1]))
                except ValueError: pass
            tariff_rows.append(dict(country_code=code,country_name=c['name'],source_id=sid,preference_eligibility='unverified',**t))
        check('minimum returned tariff audit field, not product-specific applicable tariff',row['minimum_returned_applied_tariff_pct'],min(percentages) if percentages else None,code=code)
        add_line(c,'minimum_returned_applied_tariff_pct',sorted(set(tariff_ids)),
                 'CustomDuty[].TariffReported','min(returned numeric percentage tariffs); audit only, not scored',
                 ';'.join(sorted({t['tariff_year'] for t in tariff})),'percent',row['minimum_returned_applied_tariff_pct'])
        ntms=read_csv(raw/slug/'derived/ntm_summary.csv')
        counts=[]
        ntm_ids=[]
        for p in sorted((raw/slug/'market-access-map').glob('ntm_measures_*.json')):
            sid=source_by_path[str(p.relative_to(raw)).replace('\\','/')]
            ntm_ids.append(sid)
            for section in load_json(p):
                if str(section.get('MeasureDirection'))=='1' and number(section.get('MeasureAllDirTotalCount')) is not None:
                    counts.append(number(section['MeasureAllDirTotalCount']))
        # Original input used max total_measures from its saved summary, not category sums.
        count_summary=max([number(t['total_measures']) for t in ntms],default=None)
        check('NTM count vs saved structured summary; empty remains missing',row['ntm_measure_count_max'],count_summary,code=code)
        for t in ntms:
            ntm_raw=load_json(raw/t['raw_source_file'].replace('\\','/'))
            assert any(str(s.get('MeasureDirection'))==str(t['measure_direction']) and
                       str(s.get('MeasureTotalCount'))==str(t['total_measures']) and
                       any(m['MeasureCode']==t['measure_code'] and str(m['MeasureCount'])==str(t['measure_count']) for m in s.get('Measures',[]))
                       for s in ntm_raw), ('NTM summary differs from raw response',code,t['measure_code'])
            ntm_rows.append(dict(country_code=code,country_name=c['name'],source_id=source_by_path[t['raw_source_file'].replace('\\','/')],**t))
        add_line(c,'ntm_measure_count_max',sorted(set(ntm_ids)),
                 'import section MeasureTotalCount; derived ntm_summary.total_measures',
                 'max returned structured summary total; empty response is missing, not zero','tool-specific NTM reference years','count',row['ntm_measure_count_max'])
        # Replace the old free-text MACMAP placeholder by concrete, validated source identifiers.
        row['source_ids']=';'.join([sid_imp]+sorted(set(tariff_ids+ntm_ids))+[f'EPM-{code}'])
        missing=[f for f in ['imports_2025_usd_thousand','import_cagr_2020_2025_pct','china_share_2025_pct','epi_potential_usd','untapped_potential_usd'] if row[f] is None]
        coverage.append({'country_code':code,'country_name':c['name'],'hs_code':HS,
                         'coverage_status':'insufficient_trade_coverage' if missing else 'complete',
                         'model_included':not missing,'missing_model_fields':';'.join(missing),
                         'trade_import_available_years':';'.join(str(y) for y,v in sorted(world.items()) if v is not None),
                         'trade_status':'partial' if missing else 'complete','epi_status':'complete',
                         'tariff_status':'complete' if tariff else 'not_available','ntm_status':'partial' if ntms else 'not_available',
                         'source_ids':row['source_ids']})
        clean_log.append({'transformation_id':f'CLEAN-{code}','timestamp':started,'input_path':imp_rel+';'+epi_rel,
                          'input_sha256':sha(raw/imp_rel)+';'+sha(raw/epi_rel),'output_path':'model_inputs.csv',
                          'country_code':code,'operation':'validate existing derived input against aggregate Trade Map and official EPM; resolve source IDs',
                          'parameters_json':json.dumps({'hs':HS,'years':[2020,2025],'CAGR_round_decimals':4,'share_round_decimals':4,'missing':'preserve null','untapped':'max(EPI-baseline,0)'},ensure_ascii=False),
                          'numeric_cells_changed':0,'qa_result':'pass','code_reference':'rebuild_itc_model.py'})
    complete=[r for r in rows if all(r[k] is not None for k in ['imports_2025_usd_thousand','import_cagr_2020_2025_pct','china_share_2025_pct','epi_potential_usd','untapped_potential_usd'])]
    assert all(r['epi_potential_usd']>0 for r in complete)
    x,z,lo,hi=transform(complete)
    ew,p,e,div=entropy(z)
    weights={'strategy_weight_topsis':STRATEGY,'equal_weight_topsis':np.ones(5)/5,'entropy_topsis':ew}
    results={name:topsis(z,w) for name,w in weights.items()}
    scores,ranks=results['strategy_weight_topsis'][:2]
    check('main weights sum',STRATEGY.sum(),1)
    check('entropy weights sum',ew.sum(),1)
    check('all min-max minima',np.abs(z.min(axis=0)).sum(),0)
    check('all min-max maxima',np.abs(z.max(axis=0)-1).sum(),0)
    # Independent scalar implementation rather than comparing only files from one function.
    for i,r in enumerate(complete):
        dp=math.sqrt(sum((float(z[i,j])*float(STRATEGY[j])-float(STRATEGY[j]))**2 for j in range(5)))
        dm=math.sqrt(sum((float(z[i,j])*float(STRATEGY[j]))**2 for j in range(5)))
        check('independent scalar TOPSIS',scores[i],dm/(dp+dm),code=r['country_code'])
    ranking=[]
    for i in np.argsort(-scores,kind='stable'):
        r=complete[i]
        ranking.append({'rank':int(ranks[i]),'country_code':r['country_code'],'country_name':r['country_name'],
                        'strategy_topsis_score':float(scores[i]),'equal_weight_rank':int(results['equal_weight_topsis'][1][i]),
                        'equal_weight_score':float(results['equal_weight_topsis'][0][i]),
                        'entropy_weight_rank':int(results['entropy_topsis'][1][i]),
                        'entropy_topsis_score':float(results['entropy_topsis'][0][i]),
                        'imports_2025_usd_thousand':r['imports_2025_usd_thousand'],
                        'import_cagr_2020_2025_pct':r['import_cagr_2020_2025_pct'],'china_share_2025_pct':r['china_share_2025_pct'],
                        'epi_potential_usd':r['epi_potential_usd'],'untapped_potential_usd':r['untapped_potential_usd'],
                        'untapped_ratio':r['untapped_potential_usd']/r['epi_potential_usd'],'source_ids':r['source_ids']})
    transformed,normalized,weighted,diagnostics,entropy_detail=[],[],[],[],[]
    for i,r in enumerate(complete):
        common={'country_code':r['country_code'],'country_name':r['country_name']}
        transformed.append(dict(common,**{k:float(x[i,j]) for j,k in enumerate(INDICATORS)}))
        normalized.append(dict(common,**{k:float(z[i,j]) for j,k in enumerate(INDICATORS)}))
        entropy_detail.append(dict(common,**{k:float(p[i,j]) for j,k in enumerate(INDICATORS)}))
        for scenario,w in weights.items():
            res=results[scenario]
            weighted.append(dict(common,scenario=scenario,**{k:float(res[2][i,j]) for j,k in enumerate(INDICATORS)}))
            diagnostics.append(dict(common,scenario=scenario,distance_positive=float(res[5][i]),distance_negative=float(res[6][i]),score=float(res[0][i]),rank=int(res[1][i])))
    weight_rows=[{'indicator':k,'direction':'benefit','transform':'ln(1+x), then min-max' if j in (0,3) else 'min-max',
                  'entropy_weight':float(ew[j]),'equal_weight':.2,'strategy_weight':float(STRATEGY[j])} for j,k in enumerate(INDICATORS)]
    # Deterministic sensitivity matches the original NumPy generator, seed and concentration.
    rng=np.random.default_rng(SEED)
    draws=rng.dirichlet(STRATEGY*CONCENTRATION,size=DRAWS)
    rank_draws=np.zeros((len(complete),DRAWS),dtype=int)
    score_draws=np.zeros((len(complete),DRAWS))
    for j,w in enumerate(draws):
        score_draws[:,j],rank_draws[:,j]=topsis(z,w)[:2]
    mc=[]
    for i,r in enumerate(complete):
        rr=rank_draws[i]
        mc.append({'country_name':r['country_name'],'market':NAMES[r['country_code']],'base_score':float(scores[i]),
                   'mean_rank':float(rr.mean()),'best_rank':int(rr.min()),'worst_rank':int(rr.max()),
                   'top3_share':float((rr<=3).mean()),'country_code':r['country_code'],'base_rank':int(ranks[i]),
                   'rank_std':float(rr.std(ddof=0))})
    mc.sort(key=lambda r:r['mean_rank'])
    check('Monte Carlo top-three membership total',int((rank_draws<=3).sum()),DRAWS*3)
    check('Monte Carlo each draw contains rank permutation',int(np.sum(np.sort(rank_draws,axis=0)!=np.arange(1,len(complete)+1)[:,None])),0)
    def correlation(other_ranks):
        return float(np.corrcoef(ranks,other_ranks)[0,1])
    sensitivity=[]
    scenario_rows=[]
    def scenario(name,zz,w,kind,note=''):
        ss,rr=topsis(zz,w)[:2]
        scenario_rows.append({'scenario':name,'type':kind,'spearman_vs_base':correlation(rr),'notes':note})
        for i,r in enumerate(complete):
            sensitivity.append({'country_code':r['country_code'],'country_name':r['country_name'],'scenario':name,'score':float(ss[i]),'rank':int(rr[i])})
    for name,w in weights.items():
        scenario(name,z,w,'original weight scheme')
    for j,k in enumerate(INDICATORS):
        for mul in (.8,1.2):
            w=STRATEGY.copy();w[j]*=mul;w/=w.sum()
            scenario(f'weight_{k}_x{mul:.1f}',z,w,'single weight +/-20%; renormalized')
        keep=[q for q in range(5) if q!=j]
        w=STRATEGY[keep]/STRATEGY[keep].sum()
        scenario('leave_out_'+k,z[:,keep],w,'leave one indicator out')
    scenario('amounts_without_log1p',transform(complete,use_log=False)[1],STRATEGY,'amount transform')
    if all(growth3[r['country_code']] is not None for r in complete):
        scenario('cagr_2022_2025',transform(complete,growth=[growth3[r['country_code']] for r in complete])[1],STRATEGY,'3-year vs 5-year CAGR','same 11-market sample; 3-year CAGR retains raw endpoint precision')
    # Procedure hybrid/AHP scenarios are inapplicable, not synthesized expert weights.
    sensitivity_unavailable=[
        {'scenario':'AHP / hybrid alpha 0.3,0.5,0.7','status':'not_applicable','reason':'No valid AHP pairwise matrix or consistency test in the established method; strategy weights are not AHP weights.'},
        {'scenario':'EPM rounded-display tolerance','status':'not_applicable','reason':'Current official numeric records are machine-readable numbers, not rounded mn display strings.'},
        {'scenario':'direct/mirror complete import-demand substitution','status':'not_available','reason':'Stored China direct exports cannot replace each destination total imports from all suppliers on an equivalent basis; no complete mirror-world-demand series.'}]
    robustness=[]
    for r in complete:
        rr=np.array([s['rank'] for s in sensitivity if s['country_code']==r['country_code']])
        robustness.append({'country_code':r['country_code'],'country_name':r['country_name'],
                           'base_rank':int(ranks[complete.index(r)]),'scenario_count':len(rr),
                           'mean_rank':float(rr.mean()),'best_rank':int(rr.min()),'worst_rank':int(rr.max()),
                           'rank_std':float(rr.std(ddof=0)),'top3_share':float((rr<=3).mean()),
                           'conclusion':'rankings sensitive to weighting/indicator choices' if rr.min()<=3<rr.max() else 'consistently inside top three in tested deterministic scenarios' if rr.max()<=3 else 'consistently outside top three in tested deterministic scenarios'})
    # Existing filenames remain usable; market_ranking now has one authoritative scoring definition.
    save_csv(output/'model_inputs.csv',rows)
    save_csv(output/'model_normalized.csv',normalized)
    save_csv(output/'model_weights.csv',weight_rows)
    save_csv(output/'market_ranking_recalculated.csv',ranking)
    market_ranking=[]
    for rank in ranking:
        r=by_code[rank['country_code']]
        market_ranking.append({'rank':rank['rank'],'country':rank['country_name'],'coverage_status':'complete',
                               'topsis_screen_score':rank['strategy_topsis_score'],
                               **{k:r[k] for k in ['imports_2025_usd_thousand','import_cagr_2020_2025_pct','china_share_2025_pct','china_rank_2025','epi_potential_usd','untapped_potential_usd']},
                               'applied_tariff_pct':None,'source_ids':r['source_ids'],
                               'scoring_method':'strategy_weight_topsis; tariff not scored',
                               'minimum_returned_applied_tariff_pct':r['minimum_returned_applied_tariff_pct']})
    for c in coverage:
        if not c['model_included']:
            r=by_code[c['country_code']]
            market_ranking.append({'rank':None,'country':r['country_name'],'coverage_status':c['coverage_status'],
                                   'topsis_screen_score':None,**{k:r[k] for k in ['imports_2025_usd_thousand','import_cagr_2020_2025_pct','china_share_2025_pct','china_rank_2025','epi_potential_usd','untapped_potential_usd']},
                                   'applied_tariff_pct':None,'source_ids':r['source_ids'],'scoring_method':'excluded_missing_trade',
                                   'minimum_returned_applied_tariff_pct':r['minimum_returned_applied_tariff_pct']})
    save_csv(output/'market_ranking.csv',market_ranking)
    for filename,name in [('strategy_topsis_scores.csv','strategy_weight_topsis'),('equal_weight_scores.csv','equal_weight_topsis')]:
        ss,rr=results[name][:2]
        save_csv(output/filename,[{'country_name':complete[i]['country_name'],'market':NAMES[complete[i]['country_code']],'score':float(ss[i])} for i in np.argsort(-ss,kind='stable')])
    save_csv(output/'sensitivity_results.csv',sensitivity)
    save_csv(output/'monte_carlo_sensitivity.csv',mc)
    save_csv(output/'model/intermediate/transformed.csv',transformed)
    save_csv(output/'model/intermediate/normalized.csv',normalized)
    save_csv(output/'model/intermediate/weighted_matrix.csv',weighted)
    save_csv(output/'model/intermediate/method_diagnostics.csv',diagnostics)
    save_csv(output/'model/intermediate/entropy_proportions.csv',entropy_detail)
    save_csv(output/'model/intermediate/indicator_diagnostics.csv',[{'indicator':k,'transformed_min':float(lo[j]),'transformed_max':float(hi[j]),'entropy':float(e[j]),'divergence':float(div[j]),'entropy_weight':float(ew[j])} for j,k in enumerate(INDICATORS)])
    save_csv(output/'model/intermediate/ideal_solutions.csv',[{'scenario':name,'indicator':k,'positive_ideal':float(results[name][3][j]),'negative_ideal':float(results[name][4][j])} for name in weights for j,k in enumerate(INDICATORS)])
    save_csv(output/'model/intermediate/monte_carlo_weights.csv',[{'draw':i+1,**{k:float(draws[i,j]) for j,k in enumerate(INDICATORS)}} for i in range(DRAWS)])
    save_csv(output/'model/intermediate/monte_carlo_ranks.csv',[{'draw':j+1,**{r['country_code']:int(rank_draws[i,j]) for i,r in enumerate(complete)}} for j in range(DRAWS)])
    save_csv(output/'model/output/robustness_summary.csv',robustness)
    save_csv(output/'model/output/scenario_diagnostics.csv',scenario_rows)
    save_json(output/'model/config/scenarios.json',{'original':['strategy_weight_topsis','equal_weight_topsis','entropy_topsis'],'monte_carlo':{'seed':SEED,'draws':DRAWS,'dirichlet_concentration':CONCENTRATION,'center':STRATEGY.tolist(),'seed_note':'Historical random seed preserved for method comparability; not an HS product identifier.'},'additional_scenarios':scenario_rows,'inapplicable_or_unavailable':sensitivity_unavailable})
    save_json(output/'model/config/indicators.json',{'indicators':[{'name':k,'direction':'benefit','weight':float(STRATEGY[j]),'transform':'log1p_then_minmax' if j in (0,3) else 'minmax','missing_policy':'common complete sample, no imputation','winsorization':'none; original implementation retained'} for j,k in enumerate(INDICATORS)],'tariff':'not scored; minimum-returned tariff is not actual product-specific applicable tariff','NTM':'audit only; reference years differ and empty response is not zero','AHP':'not performed; no valid pairwise matrix'})
    save_csv(output/'cleaned/trade_annual.csv',annual)
    save_csv(output/'cleaned/epi.csv',epi_rows)
    save_csv(output/'cleaned/tariffs.csv',tariff_rows)
    save_csv(output/'cleaned/ntm.csv',ntm_rows)
    save_csv(output/'metadata/coverage_matrix.csv',coverage)
    save_csv(output/'model/input/input_lineage.csv',lineage)
    save_csv(output/'logs/cleaning_log.csv',clean_log)
    save_csv(output/'logs/validation_log.csv',checks)
    save_csv(output/'metadata/file_manifest.csv',[{'raw_file':k,'sha256':v,'layer':'read_only_ITC-data'} for k,v in sorted(original_files.items())])
    query_manifest=[{'source_id':r['source_id'],'url':r['url'],'query_parameters':r['query_parameters'],'accessed_at':r['accessed_at'],'raw_file':r['raw_file'],'sha256':r['sha256']} for r in ledger]
    save_json(output/'metadata/query_manifest.json',query_manifest)
    # Source ledgers are replaced by the corresponding CURRENT data-pack ledgers, never by old copies.
    for source,dest in [('source-ledger.csv','source_ledger.csv'),('source-ledger-export-potential-map.csv','source_ledger_epm.csv')]:
        shutil.copy2(raw/source,output/dest)
    save_csv(output/'source_ledger_master.csv',ledger)
    macmap_ledger = read_csv(raw/'source-ledger-market-access-map.csv')
    for r in macmap_ledger:
        r['original_source_id'] = r['source_id']
        r['source_id'] = source_by_path[r['raw_file'].replace('\\','/')]
    save_csv(output/'source_ledger_macmap.csv',macmap_ledger)
    save_csv(output/'metadata/source_id_aliases.csv',aliases)
    enriched=[]
    for r in ledger:
        enriched.append(dict(r,organization='International Trade Centre (ITC)',hs_code=HS if r['hs_or_product_code']==HS else 'not_applicable',hs_level=6 if r['hs_or_product_code']==HS else None,
                             hs_version=VERSION,raw_path_base='../ITC-data',raw_path='../ITC-data/'+r['raw_file'].replace('\\','/'),
                             precision_status='official machine-readable response; no additional invented precision'))
    save_csv(output/'metadata/source_ledger.csv',enriched)
    fact_rows=[]
    lineage_map={(r['country_code'],r['field']):r for r in lineage}
    metrics=[('imports_2025_usd_thousand','2025年目的国从全球进口额','USD thousand'),
             ('import_cagr_2020_2025_pct','2020—2025年进口CAGR','percent'),
             ('china_share_2025_pct','2025年中国进口供应份额','percent'),
             ('china_rank_2025','2025年中国供应国排名','rank'),
             ('epi_potential_usd','ITC官方出口潜力','USD'),('baseline_exports_usd','ITC官方基准出口','USD'),
             ('untapped_potential_usd','据ITC官方潜力与基准算得未实现潜力','USD')]
    for r in rows:
        code=r['country_code']
        for field,label,unit in metrics:
            if r[field] is None:
                continue
            ln=lineage_map[(code,field)]
            fact_rows.append({'fact_id':f'FACT-HS850811-{code}-{field}','fact_text_short':NAMES[code]+label,
                              'metric_name':field,'metric_value':r[field],'display_value':f'{r[field]:.4f}',
                              'currency':'USD' if unit.startswith('USD') else '', 'unit':unit,
                              'exporter_iso3':'CHN','importer_iso3':ISO[code],'hs_code':HS,'hs_version':VERSION,
                              'period':ln['period'],'source_id':ln['source_ids'],'file_id':ln['source_ids'],
                              'raw_locator':ln['raw_locators'],'raw_files':ln['raw_files'],'clean_table':'model_inputs.csv',
                              'clean_row_key':code,'transformation_ids':ln['transformation_id'],'model_run_id':run_id,
                              'model_output_locator':'model_inputs.csv#country_code='+code+'&field='+field,
                              'citation_label':f'ITC-HS850811-{code}-{field}','citation_url':ln['query_urls'],
                              'accessed_at':ln['accessed_at'],'rounding_rule':'machine-readable official numbers; derived trade CAGR/share inherited 4-decimal rounding',
                              'status':'source_verified_scope_limited','reviewer_note':'HS revision is not declared in stored Trade Map response; cite HS6 aggregate scope and source date explicitly.'})
        rank=next((x for x in ranking if x['country_code']==code),None)
        if rank:
            for field in ['rank','strategy_topsis_score']:
                fact_rows.append({'fact_id':f'FACT-HS850811-{code}-{field}','fact_text_short':NAMES[code]+('战略TOPSIS排名' if field=='rank' else '战略TOPSIS得分'),
                                  'metric_name':field,'metric_value':rank[field],'display_value':str(rank[field]) if field=='rank' else f'{rank[field]:.6f}',
                                  'currency':'','unit':'rank' if field=='rank' else 'dimensionless','exporter_iso3':'CHN','importer_iso3':ISO[code],
                                  'hs_code':HS,'hs_version':VERSION,'period':'Trade 2020-2025; EPM snapshot 2026-10-03',
                                  'source_id':r['source_ids'],'file_id':r['source_ids'],'raw_locator':'See model/input/input_lineage.csv by country_code and field',
                                  'raw_files':';'.join(sorted({q['raw_files'] for q in lineage if q['country_code']==code})),
                                  'clean_table':'model_inputs.csv','clean_row_key':code,'transformation_ids':f'CLEAN-{code}',
                                  'model_run_id':run_id,'model_output_locator':f'market_ranking_recalculated.csv#country_code={code}&field={field}',
                                  'citation_label':f'Researcher-TOPSIS-HS850811-{code}-{field}',
                                  'citation_url':';'.join(sources[s]['url'] for s in r['source_ids'].split(';')),
                                  'accessed_at':';'.join(sorted({sources[s]['accessed_at'] for s in r['source_ids'].split(';')})),
                                  'rounding_rule':'rank from unrounded score; presentation score 6 decimals',
                                  'status':'source_verified_scope_limited','reviewer_note':'Researcher screening model, not an official ITC ranking or company suitability score.'})
    save_csv(output/'fact_registry.csv',fact_rows)
    save_csv(output/'deliverables/fact_citation_map.csv',[{k:r[k] for k in ['fact_id','citation_label','citation_url','accessed_at','source_id','raw_files','raw_locator','model_output_locator','status']} for r in fact_rows])
    save_csv(output/'deliverables/source_appendix.csv',enriched)
    data_dictionary=[{'field':k,'type':'string' if k not in numeric_columns else 'nullable_number','definition':{
        'imports_2025_usd_thousand':'2025 destination-reported global imports, USD thousand',
        'import_cagr_2020_2025_pct':'((M2025/M2020)^(1/5)-1)*100, rounded 4 decimals in supplied input',
        'china_share_2025_pct':'destination imports from China / destination global imports *100, rounded 4 decimals',
        'minimum_returned_applied_tariff_pct':'minimum numeric tariff among returned national lines/regimes; NOT product applicable rate',
        'ntm_measure_count_max':'maximum total from structured NTM summary; empty response remains NULL',
        'epi_potential_usd':'official EPM value, USD', 'baseline_exports_usd':'official EPM exportValue, USD; not 2025 Trade Map exports',
        'untapped_potential_usd':'max(official EPM value - exportValue,0), USD',
        'epi_rank':'official all-market EPM rank, not researcher RCEP rank',
        'china_rank_2025':'China supplier rank from destination import records',
        'country_code':'three-digit ITC code; preserve leading zero',
        'source_ids':'concrete IDs resolving in source_ledger_master.csv',
        'country_name':'unchanged ITC display name'}.get(k,k),'missing_policy':'blank is missing, never zero-filled'} for k in copied_input[0]]
    save_csv(output/'cleaned/data_dictionary.csv',data_dictionary)
    request={'study_id':run_id,'product_name_zh':'扫地机器人所在的HS850811真空吸尘器产品组',
             'hs_code_itc':HS,'hs_level':6,'hs_version':VERSION,'exporter_iso3':'CHN','exporter_itc_code':'156',
             'candidate_markets':[c['name'] for c in countries],'years_annual':list(range(2020,2026)),
             'currency':'USD','trade_value_unit':'USD thousand','epi_value_unit':'USD',
             'model_method':'strategy_weight_topsis','weight_policy':dict(zip(INDICATORS,STRATEGY.tolist())),
             'access_dates':'2026-10-03 (inherited from source ledgers; not a new download)',
             'source_root':'../ITC-data','raw_update_policy':'read_only','replacement_policy':'replace old analysis outputs; no archived old analysis dataset',
             'reference_procedure':'../itc-market-analysis-procedure/SKILL.md',
             'method_implementation':'five-indicator original recalculate_model.ps1 and original Monte Carlo implementation'}
    # JSON is valid YAML 1.2 and avoids a separate YAML dependency.
    save_text(output/'request.yaml',json.dumps(request,ensure_ascii=False,indent=2))
    save_text(output/'model/config/weights.yaml',json.dumps({'strategy':dict(zip(INDICATORS,STRATEGY.tolist())),
        'equal':dict(zip(INDICATORS,[.2]*5)),'entropy':dict(zip(INDICATORS,ew.tolist())),
        'strategy_source':'preserved existing implementation, not AHP expert consensus'},ensure_ascii=False,indent=2))
    top=ranking[:3]
    top_text='、'.join(f"{NAMES[r['country_code']]}（{r['strategy_topsis_score']:.6f}）" for r in top)
    table='\n'.join(f"| {r['rank']} | {NAMES[r['country_code']]} | {r['strategy_topsis_score']:.6f} | {r['equal_weight_rank']} | {r['entropy_weight_rank']} |" for r in ranking)
    mc_table='\n'.join(f"| {r['market']} | {r['base_rank']} | {r['mean_rank']:.3f} | {r['best_rank']}—{r['worst_rank']} | {r['top3_share']:.2%} |" for r in mc)
    epi_table='\n'.join(f"| {NAMES[r['country_code']]} | {r['epi_potential_usd']:.2f} | {r['baseline_exports_usd']:.2f} | {r['untapped_potential_usd']:.2f} | {r['untapped_ratio']:.2%} | {r['source_id']} |" for r in epi_rows)
    methodology=f'''# 原方法重算说明

本轮读取更新后的 `../ITC-data`，使用 HS6 `850811`、2020—2025 年贸易数据及 2026-10-03 保存的 EPM/Market Access Map 快照。未联网、未修改原始数据，未加入公司适配指标。

## 方法优先级

用户要求保留原方法，故基准以原 `recalculate_model.ps1` 五指标正式计算及 `build_report_charts.py` 的随机权重实现为准。旧 README 所述“等权主排名”及旧 `market_ranking.csv` 的简单平均筛选与正式 TOPSIS 代码不一致，本轮统一为战略权重 TOPSIS；两个排名文件指向同一套新结果，不并存第二套主排名。没有改用技能的默认 hybrid，也没有伪造 AHP 判断矩阵。

## 输入与样本

完整保留当前横向输入表的数值；将 `MACMAP rows linked by raw_source_file` 占位文本解析成真实来源 ID。逐国复核原始 Trade Map `aggregateRecords`，不重复累加不同 HS 版本子记录；以进口国自报世界进口额衡量需求。中国直接出口额单列在 `cleaned/trade_annual.csv`，不与进口国 CIF 口径混为同一序列。输入 CAGR 与中国份额保持既有 4 位小数，不通过额外精度改变主排名。

14 个市场中 {len(complete)} 个有完整主指标；老挝、缅甸、越南缺少 2025 年进口数据，不插补、不补零。文莱与新加坡的未实现潜力是有依据的零，保留在样本中。

## 五指标与公式

顺序为市场规模、市场增长、中国供应份额、未实现潜力金额、未实现潜力比例，战略权重依次为 0.30、0.10、0.10、0.30、0.20，全部正向。金额分别在千美元（进口额）与美元（EPM）原有单位上做 `ln(1+x)`，不能先换单位再声称同一模型。增长为 `((M2025/M2020)^(1/5)-1)*100`；潜力比例为 `max(EPI-baseline,0)/EPI`。

在共同完整样本中做 Min-Max：`z=(x-min)/(max-min)`，`v=z*w`；理想解逐列取最大/最小，`D+=sqrt(sum((v-v+)^2))`、`D-=sqrt(sum((v-v-)^2))`，`C=D-/(D++D-)`。按未舍入得分降序排名，展示 6 位小数。

熵权由 `p=z/sum(z)`、`e=-sum(p*ln(p))/ln(n)`、`w=(1-e)/sum(1-e)` 得到；约定 `0*ln(0)=0`。等权为每项 0.2。无机械缩尾；小样本极端值通过敏感性呈现。

关税最低返回值仅作审计字段，不是具体扫地机器人型号的实际适用税率，不进入评分；完整样本最低返回值均为零，但越南为 5%，已保留且未进入完整样本。NTM 只作审计，空响应不作零，条目数不等于合规成本；供应国排名并非全部第一名，也不据此改动原五指标。

## 稳健性

保留战略/等权/熵权方案；蒙特卡洛严格沿用 `np.random.default_rng({SEED})`、`Dirichlet(strategy_weight*{CONCENTRATION})`、{DRAWS} 次。种子数字是历史随机参数，不是本轮 HS。保存全部抽样权重和排名。补充单项权重 ±20% 后归一化、留一指标、金额不用 log1p、2022—2025 三年 CAGR，仅作为诊断，不取代主结果。无有效 AHP，alpha 场景不适用；机器可读 EPM 不需粗显示舍入场景；无同口径镜像全球需求，相关场景列为不可用。

## 审计与重跑

从本目录运行 `python rebuild_itc_model.py --raw ../ITC-data --output .`，需要 Python 与 NumPy。不会删除文件；全量替换前应按 README 清单移除旧结果。`model/input/input_lineage.csv` 保存字段级来源与计算，`logs/validation_log.csv` 保存数值复核，`run/run_manifest.json` 记录版本及源文件哈希。原计算脚本 `recalculate_model.ps1` 仅为公式一致性核验入口，完整重建应使用 Python 入口。

`source_ledger*.csv` 的 `raw_file` 均相对 `../ITC-data`；`metadata/source_ledger.csv` 另提供可解析的相对路径。原始账本复用部分 Market Access Map 编号，新结果按“国家＋响应类型＋税则线”构造唯一编号，`original_source_id` 和 `metadata/source_id_aliases.csv` 保留原始对应关系，不修改原账本。访问时间沿用原获取时间，重算时间单独记录，不把重算写成重新下载。原始 Trade Map 响应未声明确切 HS 修订年份，事实登记为 `source_verified_scope_limited`，不虚标 `report_ready`。EPM 2030 地平线仅见已存界面说明，原记录无该字段，明确标注证据状态。
'''
    save_text(output/'methodology.md',methodology)
    save_text(output/'limitations.md','''# 使用限制

- HS850811 是功率/容器容量边界下的真空吸尘器产品组，包含非机器人吸尘器；不是 85081110 专属、扫地机器人专属或石头科技品牌数据。
- 老挝、缅甸、越南缺少 2025 年进口数据，未进入主模型，不能解释为市场没有机会。
- Trade Map 未在已存响应中声明 HS 修订年份；采用请求 HS6 聚合而非擅自指定某版 HS。EPM 2030 地平线来自已存说明，原记录无独立字段。
- EPM 基准出口是官方模型基准，不是 2025 年 Trade Map 出口；未实现潜力金额由官方两字段做机械差额，不是销量承诺。
- 关税保留各国家税则线、协定和年份。最低返回税率不代表所有型号的实际税率或已满足优惠原产地条件；NTM 记录年份、范围不同，不能直接比较合规成本。
- 战略权重是既有研究选择，不是 AHP 专家共识；熵权反映样本区分度，权重情景中的前三频率不是进入成功概率。
- 使用者应同时阅读等权、熵权和敏感性；主排名对指标设定敏感时，不据单一分数作企业进入决定。
- 本轮只更新 ITC 分析结果，未同步 main.tex、main/graphics 或其他数据目录。原始数据已有来源证据按原样引用，缺失截图或确切 HS 版本不由重算补造。
''')
    save_text(output/'analysis_summary.md',f'''# HS850811 市场初筛新结果

战略权重 TOPSIS 前三为：{top_text}。

| 排名 | 市场 | 战略TOPSIS | 等权排名 | 熵权排名 |
|---:|---|---:|---:|---:|
{table}

## 5,000 组原方法随机权重检验

| 市场 | 基准排名 | 平均排名 | 最好—最差 | 进入前三的情景比例 |
|---|---:|---:|---|---:|
{mc_table}

情景比例表示本组权重变化中的排序稳定性，不是商业成功概率。确定性场景详见 `model/output/robustness_summary.csv`；共同样本中部分市场在等权/熵权与战略权重之间排名不同，应保留多方案结果。数据是吸尘器产品组口径，不代表品牌适配或扫地机器人专属需求。

事实、来源与访问日期见 `fact_registry.csv`、`source_ledger_master.csv`。本轮不修改报告正文。
''')
    save_text(output/'README.md',f'''# 更新后的 ITC 市场分析结果

本目录仅包含基于当前 HS6 **850811** 数据的重算结果；旧分析数据已经全量替换，不保留归档副本。数据来源仍在只读的 `../ITC-data`。

主方法保留五指标战略权重 TOPSIS（30%/10%/10%/30%/20%），保留等权、熵权及 5,000 组随机权重检验。主结果前三：{top_text}。14 个候选市场中 {len(complete)} 个参与排名，另外 3 个保留缺口记录。

## 从哪里看

- `analysis_summary.md`：新排名和随机权重稳定性。
- `market_ranking_recalculated.csv`：完整主排名与三种权重结果。
- `market_ranking.csv`：同一战略 TOPSIS 结果的兼容入口，另含 3 个未排名市场。`topsis_screen_score` 明确等于战略 TOPSIS；不再另存旧简单平均排名。未确认的 `applied_tariff_pct` 留空，最低返回值另列，不冒充实际税率。
- `model_inputs.csv`、`model_normalized.csv`、`model_weights.csv`：保留既有入口格式；原始数值不更改，只解析来源占位符。
- `cleaned/`：机械提取的年度贸易、EPM、关税与 NTM；`metadata/coverage_matrix.csv`：覆盖与排除理由。
- `model/input/input_lineage.csv`：每个输入字段到来源及公式的映射。
- `model/intermediate/`：变换、标准化、加权、理想解、距离、熵权过程、5,000 组抽样权重与排名。
- `model/output/`、`sensitivity_results.csv`、`monte_carlo_sensitivity.csv`：补充敏感性及稳健性。
- `fact_registry.csv`、`deliverables/fact_citation_map.csv`：可供报告尾注转换的来源索引。`source_verified_scope_limited` 提醒 HS 版本等尚未披露事项，不意味着引用链缺失。
- `source_ledger*.csv`：当前来源记录，`raw_file` 相对 `../ITC-data`；Market Access Map 编号已消歧，保留 `original_source_id` 及 `metadata/source_id_aliases.csv` 对照，不改原始账本。`metadata/source_ledger.csv` 含显式路径、URL、参数、访问时间、SHA-256。
- `logs/`、`run/`：清洗/验证与运行环境、源文件指纹。
- `model_audit.ipynb`：已顺序执行的复算与审计阅读入口；不需要联网或公司数据。

## 重跑

在本目录执行 `python rebuild_itc_model.py --raw ../ITC-data --output .`。需要 Python 与 NumPy；没有网络依赖。脚本只生成本轮文件，不自动删除目录。如更换输出模式，先按生成清单核对残留文件，再按明确目标清理，不删除 ITC-data、流程或报告。

## 方法沿用与修正

旧文档的等权初筛叙述与正式代码不一致，现统一以原五指标 TOPSIS 计算为准。随机种子 {SEED} 原样保留，数字只是随机参数。旧图表脚本硬编码旧研究路径且会写入报告图表目录，本次移除；未生成或替换报告图表。没有重下数据，来源访问时间为 2026-10-03，运行时间另记。

Trade Map 2020—2025（千美元）；EPM 当前快照（美元）；税率及 NTM 各自保存参考年份。关税、NTM 不参与五指标评分。HS850811 包含非机器人吸尘器；本结果不是石头科技经营判断。详情见 `methodology.md` 与 `limitations.md`。
''')
    save_text(output/'model/output/model_card.md',f'''# Model card

- Run: {run_id}
- Scope: China / HS850811 / 14 foreign RCEP members, 11 complete markets.
- Main: five-indicator strategy TOPSIS; weights {STRATEGY.tolist()}.
- Target: product-group market screening, not official ITC ranking or company-fit prediction.
- Reproducibility: input hashes, field lineage, normalization bounds, weighted matrices, ideal solutions, distances, entropy steps and sensitivity draws retained.
- Sources: existing official ITC data pack, original access timestamps preserved.
- Missing: Lao PDR, Myanmar, Viet Nam 2025 import-demand data; no imputation.
- Statistical limits: small cross-market sample, strategy weights, EPM and trade reference periods differ; Monte Carlo weight frequencies are not probabilities of success.
- See methodology.md and limitations.md for scope and provenance qualifications.
''')
    save_text(output/'deliverables/preliminary_findings.md',f'''# HS850811 ITC 数据与市场初筛结果

## 研究口径

中国出口至 RCEP 其余 14 国；Trade Map HS6 850811，2020—2025 年；数据访问 2026-10-03，重算 {started}。方法为原五指标战略权重 TOPSIS，运行 {run_id}。

## 数据覆盖与缺口

11 国主指标完整；老挝、缅甸、越南因缺 2025 进口数据未排名。覆盖表列明逐国缺口。关税/NTM 为审计，不作为评分。

## 官方 ITC EPI 与未实现潜力

单位美元。EPI 与基准为官方字段；未实现潜力金额为二者机械计算值，比例与官方 gap 复核。预测 2030 来自既存界面说明，非原记录字段。

| 市场 | 官方 EPI | 官方基准 | 算得未实现潜力 | 比例 | 来源 |
|---|---:|---:|---:|---:|---|
{epi_table}

## 市场吸引力初筛

| 排名 | 市场 | 战略TOPSIS | 等权排名 | 熵权排名 |
|---:|---|---:|---:|---:|
{table}

## 敏感性摘要

| 市场 | 基准排名 | 平均排名 | 最好—最差 | Top3情景比例 |
|---|---:|---:|---|---:|
{mc_table}

## 证据与引用索引

见 `fact_citation_map.csv` 与 `../fact_registry.csv`，逐事实提供 source_id、原始文件定位、访问日期、URL 和计算出口。

## 限制

HS 产品组不是扫地机器人专属；初筛不是企业进入判断；EPI 不是市场上限；缺失、税则线资格、HS 修订版本及权重敏感性见 `../limitations.md`。
''')
    # Save only the new executable. Never carry old numeric outputs into this directory.
    if Path(__file__).resolve() != (output/'rebuild_itc_model.py').resolve():
        shutil.copy2(__file__,output/'rebuild_itc_model.py')
    raw_after={str(p.relative_to(raw)).replace('\\','/'):sha(p) for p in raw.rglob('*') if p.is_file()}
    assert raw_after == original_files, 'Read-only data pack changed during model run'
    run_manifest={'model_run_id':run_id,'started_at':started,'timezone':'Asia/Shanghai','hs_code':HS,
                  'raw_root':'../ITC-data','source_access_dates':sorted({r['accessed_at'] for r in ledger}),
                  'input_sha256':sha(raw/'_modeling-output/rcep_country_comparison_model_inputs.csv'),
                  'script_sha256':sha(__file__),'raw_file_count':len(original_files),'source_event_count':len(ledger),
                  'raw_unchanged':True,'validation_checks':len(checks),'validation_passed':True,
                  'complete_markets':[r['country_code'] for r in complete],
                  'excluded_markets':[c['country_code'] for c in coverage if not c['model_included']],
                  'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),
                  'strategy_weights':STRATEGY.tolist(),'random_seed':SEED,'monte_carlo_draws':DRAWS,'dirichlet_concentration':CONCENTRATION,
                  'procedure_sha256':sha(raw.parent/'itc-market-analysis-procedure/SKILL.md'),
                  'top3_country_codes':[r['country_code'] for r in top],
                  'scope':'results directory only; main.tex and report graphics unchanged'}
    save_json(output/'run/run_manifest.json',run_manifest)
    save_text(output/'run/environment.txt',f'Python: {sys.version}\nNumPy: {np.__version__}\nPlatform: {platform.platform()}\nTimezone: Asia/Shanghai\nNo new packages installed; no network retrieval.')
    save_json(output/'run/validation_summary.json',{'passed':True,'checks':len(checks),'source_hashes_verified':len(ledger),
                                                  'all_raw_files_unchanged':True,'independent_scalar_TOPSIS':True,
                                                  'EPM_extracts_equal_decoded_official_response':True,'complete_markets':len(complete),
                                                  'total_candidate_markets':14,'deterministic_sensitivity_scenarios':len(scenario_rows)})
    print(json.dumps({'run_id':run_id,'top3':top,'validation_checks':len(checks),'excluded':run_manifest['excluded_markets'],'output':str(output)},ensure_ascii=False,indent=2))
    return run_manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',type=Path,default=Path(__file__).resolve().parent.parent/'ITC-data')
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    run(args.raw,args.output)
