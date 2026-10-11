"""Offline HS composition validation. Requires NumPy and Pillow, not SciPy.

python code/verify_model.py --repo C:/Users/99097/Documents/GitHub/RCEP
python code/verify_model.py  # rerun using immutable local snapshots

Original Customs files, ITC inputs, official values, and model results are NEVER
edited. Counterfactual scores are diagnostics, not official ITC EPI estimates.
"""
from __future__ import annotations
import argparse
import contextlib
import csv
import hashlib
import importlib.util
import io
import itertools
import json
import math
import platform
import shutil
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
IND = ['market_size', 'market_growth', 'china_share', 'untapped_amount', 'untapped_ratio']
# Customs partner codes are NOT ITC/UN M49 codes. Explicit verified name join.
COUNTRIES = [
    ('601','036','AUS','Australia','澳大利亚'),
    ('105','096','BRN','Brunei Darussalam','文莱'),
    ('107','116','KHM','Cambodia','柬埔寨'),
    ('112','360','IDN','Indonesia','印度尼西亚'),
    ('116','392','JPN','Japan','日本'),
    ('133','410','KOR','Korea, Republic of','韩国'),
    ('119','418','LAO',"Lao People's Democratic Republic",'老挝'),
    ('122','458','MYS','Malaysia','马来西亚'),
    ('106','104','MMR','Myanmar','缅甸'),
    ('609','554','NZL','New Zealand','新西兰'),
    ('129','608','PHL','Philippines','菲律宾'),
    ('132','702','SGP','Singapore','新加坡'),
    ('136','764','THA','Thailand','泰国'),
    ('141','704','VNM','Viet Nam','越南'),
    ('502','842','USA','United States of America','美国'),
]

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def readcsv(p, encoding='utf-8-sig'):
    with Path(p).open(encoding=encoding, newline='') as f:
        return list(csv.DictReader(f))

def writecsv(p, rows, fields=None):
    p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0])
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def writejson(p, obj):
    p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def rankdata(x):
    """Average ranks (ascending), including ties; supports last-axis batches."""
    x = np.asarray(x)
    return 1 + (x[..., :, None] > x[..., None, :]).sum(-1) + .5*((x[..., :, None] == x[..., None, :]).sum(-1)-1)

def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    dx, dy = x-x.mean(-1, keepdims=True), y-y.mean(-1, keepdims=True)
    den = np.sqrt((dx*dx).sum(-1)*(dy*dy).sum(-1))
    with np.errstate(invalid='ignore', divide='ignore'):
        return (dx*dy).sum(-1)/den

def kendall(x, y):
    """Tau-b = (concordant-discordant)/sqrt(non-tied-x * non-tied-y)."""
    x, y = np.asarray(x), np.asarray(y)
    a, b = np.triu_indices(x.shape[-1], 1)
    dx = np.sign(x[..., a]-x[..., b])
    dy = np.sign(y[..., a]-y[..., b])
    den = np.sqrt(np.count_nonzero(dx, axis=-1)*np.count_nonzero(dy, axis=-1))
    with np.errstate(invalid='ignore', divide='ignore'):
        return (dx*dy).sum(-1)/den

def association(x, y):
    return {'pearson':float(pearson(x,y)),
            'spearman':float(pearson(rankdata(x),rankdata(y))),
            'kendall_tau_b':float(kendall(x,y))}

def exact_kendall_p(x,y):
    # No ties: Mahonian inversion-count distribution (n! equally likely orders).
    n=len(x)
    if len(set(x)) != n or len(set(y)) != n:
        return None
    counts=[1]
    for k in range(2,n+1):
        nxt=[0]*(len(counts)+k-1)
        for i,v in enumerate(counts):
            for j in range(k):
                nxt[i+j]+=v
        counts=nxt
    pairs=n*(n-1)//2
    observed=round(abs(float(kendall(x,y)))*pairs)
    return sum(v for d,v in enumerate(counts) if abs(pairs-2*d)>=observed)/math.factorial(n)

def aggregate_customs(path, hs):
    rows=readcsv(path, 'gb18030')
    totals=defaultdict(int)
    loc=defaultdict(list)
    names={}
    keys=set()
    for line,r in enumerate(rows,2):
        assert r['商品编码']==hs
        assert r.get('', '')==''
        key=tuple(r[k] for k in ['商品编码','贸易伙伴编码','注册地编码','贸易方式编码'])
        assert key not in keys, ('duplicate Customs grain',key)
        keys.add(key)
        code=r['贸易伙伴编码']
        amount=r['人民币']
        assert amount.strip(), ('missing value, not zero',line)
        val=int(amount.replace(',',''))
        assert val>=0
        totals[code]+=val
        loc[code].append(line)
        names[code]=r['贸易伙伴名称']
    return rows,totals,loc,names

def snapshot(repo):
    """Copy exact bytes only once; reject changed input rather than overwrite."""
    h=repo/'data/HS-verification'
    m=repo/'data/macro-market/ITC/ITC-analysis-result'
    entries=[]
    fixed=[
        (h/'2026-china-export-850811.csv','raw/customs/2026-china-export-850811.csv','GACC-850811'),
        (h/'2026-china-export-85081110.csv','raw/customs/2026-china-export-85081110.csv','GACC-85081110'),
        (h/'2026-china-export-85081110-share-by-country.csv','raw/customs/existing-share-by-country.csv','GACC-SHARE-PREVIOUS'),
    ]
    for name in ['model_inputs.csv','strategy_topsis_scores.csv','model_weights.csv','methodology.md',
                 'rebuild_itc_model.py','model/input/input_lineage.csv','run/run_manifest.json','metadata/source_ledger.csv']:
        fixed.append((m/name,'raw/itc-model/'+name,'ITC-MODEL-'+name.replace('/','-')))
    fixed.append((m.parent/'itc-market-analysis-procedure/SKILL.md','raw/method/itc-market-analysis-SKILL.md','ITC-METHOD'))
    for source,dest,sid in fixed:
        p=ROOT/dest
        p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():
            assert sha(p)==sha(source), ('frozen snapshot conflict',p)
        else:
            shutil.copyfile(source,p)
        entries.append({'source_id':sid,'original_absolute_path':str(source),'snapshot_path':dest,
                        'sha256':sha(source),'file_size_bytes':source.stat().st_size})
    ledger=readcsv(m/'metadata/source_ledger.csv')
    wanted={c[1] for c in COUNTRIES if c[2] not in ['USA','VNM','LAO','MMR']}
    selected=[]
    for r in ledger:
        if r['country_code'] not in wanted or not (r['source_id'].startswith('EPM-') or
                (r['dataset']=='target_import_imports_by_supplier' and r['indicator']=='VAL')):
            continue
        source=(m/r['raw_path']).resolve()
        assert source.is_relative_to((m.parent/'ITC-data').resolve())
        dest='raw/itc-official/'+r['raw_file'].replace('\\','/')
        p=ROOT/dest
        p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():
            assert sha(p)==sha(source)
        else:
            shutil.copyfile(source,p)
        assert sha(p)==r['sha256'], ('upstream source hash mismatch',r['source_id'])
        entries.append({'source_id':r['source_id'],'original_absolute_path':str(source),'snapshot_path':dest,
                        'sha256':sha(source),'file_size_bytes':source.stat().st_size})
        selected.append(dict(r,snapshot_path=dest))
    assert len(selected)==22
    writecsv('metadata/official_itc_source_ledger.csv',selected)
    writecsv('metadata/input_file_manifest.csv',entries)

def load_data():
    cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    m=ROOT/'raw/itc-model'
    raw=readcsv(m/'model_inputs.csv')
    scores=readcsv(m/'strategy_topsis_scores.csv')
    ws=readcsv(m/'model_weights.csv')
    w=np.array([float(next(r for r in ws if r['indicator']==k)['strategy_weight']) for k in IND])
    assert np.allclose(w,[.3,.1,.1,.3,.2],rtol=0,atol=1e-15)
    previous=readcsv(ROOT/'raw/customs/existing-share-by-country.csv')
    bpath=ROOT/'raw/customs/2026-china-export-850811.csv'
    npath=ROOT/'raw/customs/2026-china-export-85081110.csv'
    br,b,bl,bn=aggregate_customs(bpath,'850811')
    nr,n,nl,nn=aggregate_customs(npath,'85081110')
    assert '第一数量' not in br[0] and '第一数量' in nr[0]
    assert set(b)==set(n)=={c[0] for c in COUNTRIES}
    checks=[]
    countries=[]
    row_lineage=[]
    for cc,ic,iso,en,zh in COUNTRIES:
        old=next(r for r in previous if r['贸易伙伴编码']==cc)
        assert bn[cc]==nn[cc]==zh==old['国家或地区']
        assert b[cc]>0 and 0<=n[cc]<=b[cc]
        s=n[cc]/b[cc]
        assert b[cc]==int(old['HS850811出口金额_人民币']) and n[cc]==int(old['HS85081110出口金额_人民币'])
        assert abs(s-float(old['HS85081110占HS850811出口金额比重']))<=5.01e-9
        assert old['分母文件SHA256']==sha(bpath) and old['分子文件SHA256']==sha(npath)
        ir=next((r for r in raw if r['country_code']==ic),None)
        sr=next((r for r in scores if r['country_name']==en),None)
        status='ranked' if sr else 'US_reference_only' if iso=='USA' else 'ITC_missing_indicators'
        row={'customs_partner_code':cc,'itc_country_code':ic,'iso3':iso,'market':zh,'country_name':en,
             'period':cfg['customs_period'],'broad_export_cny':b[cc],'narrow_export_cny':n[cc],
             'narrow_share':s,'narrow_share_pct':s*100,'itc_status':status,
             'original_score':float(sr['score']) if sr else '',
             'original_rank':scores.index(sr)+1 if sr else '',
             'customs_source_ids':'GACC-850811;GACC-85081110',
             'itc_source_ids':ir['source_ids'] if ir else '',
             'customs_accessed_at':'not_recorded_user_supplied_export',
             'period_evidence':'user_request;existing-share-by-country.csv;not_encoded_in_raw_csv'}
        countries.append(row)
        for hs,rows,total,loc,sid in [('850811',br,b,bl,'GACC-850811'),('85081110',nr,n,nl,'GACC-85081110')]:
            row_lineage.append({'iso3':iso,'market':zh,'hs_code':hs,'amount_cny':total[cc],
                                'source_id':sid,'raw_csv_physical_lines':';'.join(map(str,loc[cc])),
                                'source_row_count':len(loc[cc]),'aggregation':'sum CNY by partner across mutually exclusive registered province and trade mode',
                                'key':cc,'transformation_id':'CLEAN-CUSTOMS-'+hs})
        checks.append({'check':'country aggregate, ratio, source hashes, name join','iso3':iso,'passed':True,
                       'share_rounded_error':s-float(old['HS85081110占HS850811出口金额比重'])})
    countries.sort(key=lambda r:(r['original_rank'] if r['original_rank']!='' else 100, r['iso3']))
    sample=[r for r in countries if r['itc_status']=='ranked']
    model=[]
    for c in sample:
        r=next(r for r in raw if r['country_code']==c['itc_country_code'])
        model.append([float(r['imports_2025_usd_thousand']),float(r['import_cagr_2020_2025_pct']),
                      float(r['china_share_2025_pct']),float(r['untapped_potential_usd']),
                      float(r['untapped_potential_usd'])/float(r['epi_potential_usd'])])
    x=np.array(model)
    s=np.array([r['narrow_share'] for r in sample])
    orig=np.array([r['original_score'] for r in sample])
    ranks=np.array([r['original_rank'] for r in sample])
    assert len(sample)==11 and np.all(np.isfinite(x))
    return cfg,countries,sample,x,s,w,orig,ranks,row_lineage,checks

def topsis(x,w,extra=None):
    transformed=np.array(x,dtype=float,copy=True)
    transformed[:,[0,3]]=np.log1p(transformed[:,[0,3]])
    if extra is not None:
        transformed=np.column_stack([transformed,extra])
    lo,hi=transformed.min(0),transformed.max(0)
    assert np.all(hi>lo)
    z=(transformed-lo)/(hi-lo)
    v=z*w
    positive,negative=v.max(0),v.min(0)
    dp=np.sqrt(np.square(v-positive).sum(1))
    dm=np.sqrt(np.square(v-negative).sum(1))
    score=dm/(dp+dm)
    # None of the delivered scenarios has a score tie. Stop if this changes.
    assert len(np.unique(score))==len(score), 'Tie policy requires review'
    rank=rankdata(-score).astype(int)
    return score,rank,transformed,z,v,dp,dm

def independent_baseline(x,w):
    # Independent scalar implementation; no use of vectorized topsis helper.
    t=[[math.log1p(v) if j in (0,3) else v for j,v in enumerate(row)] for row in x.tolist()]
    lo=[min(r[j] for r in t) for j in range(5)]
    hi=[max(r[j] for r in t) for j in range(5)]
    v=[[float(w[j])*(r[j]-lo[j])/(hi[j]-lo[j]) for j in range(5)] for r in t]
    pos=[max(r[j] for r in v) for j in range(5)]
    neg=[min(r[j] for r in v) for j in range(5)]
    out=[]
    for r in v:
        dp=math.sqrt(math.fsum((r[j]-pos[j])**2 for j in range(5)))
        dm=math.sqrt(math.fsum((r[j]-neg[j])**2 for j in range(5)))
        out.append(dm/(dp+dm))
    return np.array(out)

def stats_tests(s,orig,seed,draws,boots,target='original_score'):
    rng=np.random.default_rng(seed)
    observed=association(s,orig)
    n=len(s)
    # Random ranks of independent continuous draws form uniform permutations.
    per_index=np.argsort(rng.random((draws,n)),axis=1,kind='stable')
    yp=orig[per_index]
    distributions={'pearson':pearson(s,yp),
                   'spearman':pearson(rankdata(s),rankdata(yp)),
                   'kendall_tau_b':kendall(s,yp)}
    rng=np.random.default_rng(seed+1)
    bi=rng.integers(0,n,size=(boots,n))
    bx,by=s[bi],orig[bi]
    bootstrap={'pearson':pearson(bx,by),
               'spearman':pearson(rankdata(bx),rankdata(by)),
               'kendall_tau_b':kendall(bx,by)}
    rows=[]
    for method,v in observed.items():
        extreme=int(np.count_nonzero(np.abs(distributions[method])>=abs(v)-1e-12))
        p=(extreme+1)/(draws+1)
        bd=bootstrap[method][np.isfinite(bootstrap[method])]
        lo,hi=np.quantile(bd,[.025,.975])
        rows.append({'analysis':'share_vs_'+target,'method':method,'n':n,'coefficient':v,
                     'p_value_permutation_two_sided':p,'permutation_extreme_count':extreme,
                     'permutation_draws':draws,'p_monte_carlo_standard_error':math.sqrt(p*(1-p)/(draws+1)),
                     'p_value_exact_no_ties':exact_kendall_p(s,orig) if method=='kendall_tau_b' else '',
                     'bootstrap_percentile_95_low':float(lo),'bootstrap_percentile_95_high':float(hi),
                     'bootstrap_draws':boots,'bootstrap_valid_draws':len(bd),
                     'ci_interpretation':'Exploratory country-resampling stability interval; countries are the modeled population, not a random sample',
                     'seed_permutation':seed,'seed_bootstrap':seed+1})
    # Holm family correction across three alternative association statistics.
    order=sorted(range(3),key=lambda i:rows[i]['p_value_permutation_two_sided'])
    last=0.
    for k,i in enumerate(order):
        last=max(last,min(1.,(3-k)*rows[i]['p_value_permutation_two_sided']))
        rows[i]['p_value_holm_3_tests']=last
    leave=[]
    for i in range(n):
        mask=np.arange(n)!=i
        for method,v in association(s[mask],orig[mask]).items():
            leave.append({'excluded_index':i,'method':method,'n':n-1,'coefficient':v})
    return rows,leave,distributions

def rank_comparison(base_scores,base_rank,new_scores,new_rank):
    n=len(base_rank)
    paira,pairb=np.triu_indices(n,1)
    discordant=int(np.count_nonzero((base_rank[paira]-base_rank[pairb])*(new_rank[paira]-new_rank[pairb])<0))
    a,b=set(np.flatnonzero(base_rank<=5)),set(np.flatnonzero(new_rank<=5))
    a3,b3=set(np.flatnonzero(base_rank<=3)),set(np.flatnonzero(new_rank<=3))
    return {'pearson_scores':float(pearson(base_scores,new_scores)),
            'pearson_numeric_ranks':float(pearson(base_rank,new_rank)),
            'spearman_ranks':float(pearson(rankdata(base_rank),rankdata(new_rank))),
            'kendall_tau_b_ranks':float(kendall(base_rank,new_rank)),
            'mean_absolute_rank_change':float(np.abs(new_rank-base_rank).mean()),
            'max_absolute_rank_change':int(np.abs(new_rank-base_rank).max()),
            'pairwise_reversals':discordant,'total_country_pairs':n*(n-1)//2,
            'top3_overlap_count':len(a3&b3),'top5_overlap_count':len(a&b),
            'top5_jaccard':len(a&b)/len(a|b),'top5_membership_changed':a!=b}

def make_scenarios(cfg,sample,x,s,w,orig,ranks):
    output=[];detail=[];matrices=[];weights=[]
    def add(sid,kind,param,y,ww,extra=None,direct=None,assumption=''):
        if direct is None:
            result=topsis(y,ww,extra)
            sc,rk,t,z,v,dp,dm=result
            cols=IND+(['customs_share'] if extra is not None else [])
            for i,c in enumerate(sample):
                for j,indicator in enumerate(cols):
                    matrices.append({'scenario':sid,'iso3':c['iso3'],'indicator':indicator,
                                     'input_raw':float(y[i,j]) if j<5 else float(extra[i]),
                                     'transformed':float(t[i,j]),'normalized':float(z[i,j]),
                                     'weighted':float(v[i,j]),'weight':float(ww[j]),
                                     'positive_ideal':float(v[:,j].max()),'negative_ideal':float(v[:,j].min()),
                                     'distance_positive':float(dp[i]),'distance_negative':float(dm[i])})
            for j,indicator in enumerate(cols):
                weights.append({'scenario':sid,'indicator':indicator,'weight':float(ww[j])})
        else:
            sc=direct
            rk=rankdata(-sc).astype(int)
        metrics=rank_comparison(orig,ranks,sc,rk)
        flags=[]
        if metrics['top5_membership_changed']: flags.append('top5_membership_changed')
        if metrics['max_absolute_rank_change']>=3: flags.append('max_rank_change_at_least_3')
        if metrics['spearman_ranks']<.9: flags.append('spearman_below_0.9')
        if metrics['kendall_tau_b_ranks']<.8: flags.append('kendall_below_0.8')
        top=';'.join(sample[i]['iso3'] for i in np.argsort(rk)[:5])
        output.append(dict(scenario=sid,scenario_family=kind,parameter=param,**metrics,
                           top5_order=top,practical_attention_flag=bool(flags),attention_reasons=';'.join(flags),
                           interpretation=assumption))
        for i,c in enumerate(sample):
            detail.append({'scenario':sid,'iso3':c['iso3'],'market':c['market'],'narrow_share':float(s[i]),
                           'original_score':float(orig[i]),'original_rank':int(ranks[i]),
                           'scenario_score':float(sc[i]),'scenario_rank':int(rk[i]),
                           'rank_change_positive_is_improvement':int(ranks[i]-rk[i]),
                           'top5_original':bool(ranks[i]<=5),'top5_scenario':bool(rk[i]<=5),
                           'estimate_type':'original_reproduction' if sid=='baseline' else 'researcher_stress_test_not_official_ITC'})
    add('baseline','original',0,x,w,assumption='Frozen original five-indicator TOPSIS reproduced, not a new official model')
    for weight in cfg['share_indicator_weights']:
        add(f'add_share_w{weight:.2f}','add_sixth_indicator',weight,x,np.r_[w*(1-weight),weight],extra=s,
            assumption='New analyst preference for Chinese export composition; original five weights proportionally scaled; not a measured market-size correction')
    for a in cfg['composition_exponents']:
        for family,cols in [('scale_untapped_only',[3]),('scale_size_and_untapped',[0,3])]:
            xx=x.copy()
            xx[:,cols]*=s[:,None]**a
            add(f'{family}_a{a:.2f}',family,a,xx,w,
                assumption='Assume destination Chinese export-mix share transfers to chosen broader ITC monetary measure(s), then original log1p/minmax/TOPSIS. Growth, China supply share, untapped ratio unchanged. Not measured narrow-HS imports/EPI')
    add('score_times_share','direct_score_multiplier',1,x,w,direct=orig*s,
        assumption='C_i * s_i is an intentionally strong linear composition penalty, not TOPSIS and not an official probability or EPI; numerical coefficients depend on both preference and composition')
    return output,detail,matrices,weights

def stress_grid(cfg,sample,x,s,w,orig,ranks):
    rows=[]
    step=cfg['stress_grid_step']
    for family,params in [('add_sixth_indicator',np.arange(0,.500001,step)),
                          ('scale_size_and_untapped',np.arange(0,2.000001,step)),
                          ('scale_untapped_only',np.arange(0,2.000001,step))]:
        for p in params:
            if family=='add_sixth_indicator':
                sc,rk=topsis(x,np.r_[w*(1-p),p],s)[:2]
            else:
                xx=x.copy();cols=[0,3] if family=='scale_size_and_untapped' else [3]
                xx[:,cols]*=s[:,None]**p
                sc,rk=topsis(xx,w)[:2]
            r=rank_comparison(orig,ranks,sc,rk)
            rows.append(dict(scenario_family=family,parameter=float(p),**r,
                             top5_order=';'.join(sample[i]['iso3'] for i in np.argsort(rk)[:5])))
    return rows

def unit_tests():
    tests=[]
    def check(name,ok):
        assert ok,name
        tests.append({'check':name,'passed':True})
    xx=np.array([1,2,3,4,5.])
    for method,v in association(xx,xx).items(): check(method+' self',abs(v-1)<1e-14)
    for method,v in association(xx,-xx).items(): check(method+' reversed',abs(v+1)<1e-14)
    check('average ranks ties',np.array_equal(rankdata([2,1,2,4]),[2.5,1,2.5,4]))
    check('tau-b tied fixture',abs(float(kendall([1,1,2],[1,2,3]))-math.sqrt(2/3))<1e-14)
    check('Pearson vs Python statistics.correlation',abs(float(pearson([1,3,2,6],[2,5,1,7]))-statistics.correlation([1,3,2,6],[2,5,1,7]))<1e-14)
    xx=np.arange(5);yy=np.array([3,0,4,2,1])
    cutoff=abs(float(kendall(xx,yy)))
    exact=sum(abs(float(kendall(xx,np.array(p))))>=cutoff-1e-12 for p in itertools.permutations(yy))/math.factorial(5)
    check('Kendall exact DP vs all 120 permutations',abs(exact-exact_kendall_p(xx,yy))<1e-14)
    return tests

def draw_figures(sample,s,orig,detail):
    # Pillow is bundled; matplotlib is unavailable. Fixed geometry / direct labels.
    from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version
    font_path=Path('C:/Windows/Fonts/msyh.ttc')
    assert font_path.is_file(), 'Chinese font not found'
    def font(size): return ImageFont.truetype(str(font_path),size)
    out=ROOT/'output/figures';out.mkdir(parents=True,exist_ok=True)
    im=Image.new('RGB',(1500,1000),'white');d=ImageDraw.Draw(im)
    d.text((80,35),'海关产品结构占比与原 ITC 模型得分',font=font(34),fill='#242424')
    d.text((80,90),'11 个完整样本市场；占比为 2026 年 1—8 月出口金额占比',font=font(22),fill='#555555')
    left,top,right,bottom=145,175,1400,805
    def px(a):return left+a/.7*(right-left)
    def py(a):return bottom-a*(bottom-top)
    for tick in np.arange(0,.71,.1):
        p=px(float(tick));d.line((p,top,p,bottom),fill='#e9e9e9',width=1)
        d.text((p-20,bottom+15),f'{tick:.0%}',font=font(21),fill='#333333')
    for tick in np.arange(0,1.01,.2):
        p=py(float(tick));d.line((left,p,right,p),fill='#e9e9e9',width=1)
        d.text((left-60,p-13),f'{tick:.1f}',font=font(21),fill='#333333')
    d.line((left,top,left,bottom,right,bottom),fill='#555555',width=2)
    for c,sv,cv in zip(sample,s,orig):
        p,q=px(float(sv)),py(float(cv))
        d.ellipse((p-7,q-7,p+7,q+7),fill='#416f91')
        # Label placements separate close Malaysia/Thailand and Japan/Indonesia.
        dy=-38 if c['iso3']=='MYS' else 14 if c['iso3']=='IDN' else 10 if c['iso3']=='THA' else -36 if c['iso3']=='JPN' else -30
        dx=-135 if c['iso3']=='IDN' else 13
        if c['iso3']=='IDN':
            d.line((p-3,q+7,p-18,q+21),fill='#777777',width=1)
        d.text((p+dx,q+dy),c['market'],font=font(23),fill='#242424')
    d.text((480,870),'HS85081110 / HS850811（人民币出口金额）',font=font(24),fill='#333333')
    d.text((80,145),'原 TOPSIS 得分',font=font(21),fill='#333333')
    d.text((80,930),'来源：GACC-850811、GACC-85081110；ITC 原模型 20261010T153053。期间不同，关系为描述性。',font=font(20),fill='#555555')
    im.save(out/'share_vs_score.png')
    im=Image.new('RGB',(1560,1030),'white');d=ImageDraw.Draw(im)
    d.text((70,30),'不同产品结构压力测试下的国家排名',font=font(34),fill='#242424')
    d.text((70,85),'每个单元格为排名；假设场景不替代原 ITC 模型或官方 EPI',font=font(22),fill='#555555')
    scenarios=['baseline','add_share_w0.10','add_share_w0.20','scale_untapped_only_a1.00','scale_size_and_untapped_a1.00','score_times_share']
    labels=['原模型','占比指标 10%','占比指标 20%','仅潜力金额 × 占比','规模及潜力 × 占比','原得分 × 占比']
    for j,label in enumerate(labels): d.text((220+j*205,150),label,font=font(19),fill='#333333')
    for i,c in enumerate(sample):
        yy=205+i*64;d.text((70,yy+15),c['market'],font=font(24),fill='#333333')
        for j,sid in enumerate(scenarios):
            r=next(r for r in detail if r['scenario']==sid and r['iso3']==c['iso3'])
            rank=r['scenario_rank'];xx=225+j*205
            intensity=(11-rank)/10
            color=tuple(round(244-intensity*t) for t in (90,67,45))
            d.rectangle((xx,yy,xx+180,yy+55),fill=color)
            text=f'{rank}'
            delta=r['rank_change_positive_is_improvement']
            if delta: text+=f' ({"+" if delta>0 else ""}{delta})'
            d.text((xx+50,yy+12),text,font=font(23),fill='#242424')
    d.text((70,930),'括号为相对原模型的名次变化；正数表示改善。颜色仅辅助读数，未表示统计显著性。',font=font(21),fill='#555555')
    d.text((70,972),'来源：本次 output/scenario_country_rankings.csv；海关 2026 年 1—8 月数据及冻结 ITC 原模型。',font=font(20),fill='#555555')
    im.save(out/'scenario_rank_comparison.png')
    return pillow_version

def run():
    started=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    cfg,countries,sample,x,s,w,orig,ranks,lineage,checks=load_data()
    baseline=topsis(x,w)
    independent=independent_baseline(x,w)
    err=float(np.max(np.abs(baseline[0]-orig)))
    assert err<1e-12 and np.max(np.abs(independent-orig))<1e-12
    assert np.array_equal(baseline[1],ranks)
    tests=unit_tests()
    tests.append({'check':'baseline scores vs archived ITC scores; tolerance 1e-12','passed':True,'max_absolute_error':err})
    tests.append({'check':'independent scalar model vs archived ITC scores; tolerance 1e-12','passed':True,'max_absolute_error':float(np.max(np.abs(independent-orig)))})
    writecsv('cleaned/customs_country_aggregates.csv',countries)
    writecsv('metadata/customs_row_lineage.csv',lineage)
    writecsv('metadata/country_crosswalk.csv',[dict(zip(['customs_partner_code','itc_country_code','iso3','country_name','market'],r)) for r in COUNTRIES])
    writecsv('input/matched_model_inputs.csv',[dict(c,**dict(zip(IND,map(float,x[i])))) for i,c in enumerate(sample)])
    writecsv('logs/data_quality_checks.csv',checks)
    writecsv('metadata/coverage.csv',[{'iso3':r['iso3'],'market':r['market'],'customs_status':'complete_value_ratio',
                                      'model_status':r['itc_status'],'reason':'ranked in frozen model' if r['itc_status']=='ranked' else
                                      'US retained as reference, not RCEP candidate' if r['iso3']=='USA' else
                                      'Original ITC model lacks 2025 imports/CAGR/China supply share; no imputation'} for r in countries])
    corrs,leave,dist=stats_tests(s,orig,cfg['random_seed'],cfg['permutation_draws'],cfg['bootstrap_draws'])
    writecsv('output/association_tests.csv',corrs)
    for r in leave:
        c=sample[r.pop('excluded_index')];r['excluded_iso3']=c['iso3'];r['excluded_market']=c['market']
    writecsv('output/leave_one_country_out.csv',leave)
    rankcorrs,_,rankdist=stats_tests(s,ranks,cfg['random_seed'],cfg['permutation_draws'],cfg['bootstrap_draws'],target='numeric_rank')
    for r in rankcorrs:
        r['interpretation']='Negative means higher share occurs with a better (smaller numbered) original rank; this is association, not reranking'
    writecsv('output/share_vs_numeric_rank.csv',rankcorrs)
    allcorrs=corrs+rankcorrs
    order=sorted(range(len(allcorrs)),key=lambda i:allcorrs[i]['p_value_permutation_two_sided'])
    adjusted={};last=0.
    for k,i in enumerate(order):
        last=max(last,min(1.,(len(allcorrs)-k)*allcorrs[i]['p_value_permutation_two_sided']))
        adjusted[i]=last
    writecsv('output/multiple_testing_six_tests.csv',[{'analysis':r['analysis'],'method':r['method'],
              'p_value_permutation_two_sided':r['p_value_permutation_two_sided'],
              'p_value_holm_6_tests':adjusted[i]} for i,r in enumerate(allcorrs)])
    (ROOT/'intermediate').mkdir(exist_ok=True)
    np.savez_compressed(ROOT/'intermediate/permutation_statistics.npz',**dist)
    np.savez_compressed(ROOT/'intermediate/numeric_rank_permutation_statistics.npz',**rankdist)
    scenarios,detail,mats,ww=make_scenarios(cfg,sample,x,s,w,orig,ranks)
    writecsv('output/scenario_summary.csv',scenarios)
    writecsv('output/scenario_country_rankings.csv',detail)
    writecsv('intermediate/scenario_matrices.csv',mats)
    writecsv('intermediate/scenario_weights.csv',ww)
    grid=stress_grid(cfg,sample,x,s,w,orig,ranks)
    writecsv('output/stress_parameter_grid.csv',grid)
    crossings=[]
    for family in sorted({r['scenario_family'] for r in grid}):
        items=[r for r in grid if r['scenario_family']==family]
        for name,predicate in [('first_top5_change',lambda r:r['top5_membership_changed']),
                               ('first_max_rank_shift_at_least_3',lambda r:r['max_absolute_rank_change']>=3),
                               ('first_spearman_below_0.9',lambda r:r['spearman_ranks']<.9),
                               ('first_kendall_below_0.8',lambda r:r['kendall_tau_b_ranks']<.8)]:
            selected=next((r for r in items if predicate(r)),None)
            p=selected['parameter'] if selected else None
            crossings.append({'scenario_family':family,'event':name,'first_grid_parameter':p,
                              'previous_grid_parameter':round(p-cfg['stress_grid_step'],6) if p else None,
                              'grid_resolution':cfg['stress_grid_step'],'searched_max':items[-1]['parameter'],
                              'top5_order_at_first_crossing':selected['top5_order'] if selected else '',
                              'interpretation':'First observed on fixed grid; not an exact mathematical threshold or a calibrated economic parameter'})
    writecsv('output/stress_first_crossings.csv',crossings)
    exportcomp=[]
    for scope,cs in [('ranked11',[c for c in countries if c['itc_status']=='ranked']),
                      ('all_RCEP14',[c for c in countries if c['iso3']!='USA'])]:
        b=np.array([c['broad_export_cny'] for c in cs]);n=np.array([c['narrow_export_cny'] for c in cs])
        br,nr=rankdata(-b).astype(int),rankdata(-n).astype(int)
        for i,c in enumerate(cs):
            exportcomp.append({'scope':scope,'iso3':c['iso3'],'market':c['market'],
                                'broad_export_cny':int(b[i]),'narrow_export_cny':int(n[i]),
                                'broad_export_rank':int(br[i]),'narrow_export_rank':int(nr[i]),
                                'rank_change_positive_is_improvement':int(br[i]-nr[i]),
                                'comparison':'Observed Customs value ranking, same 2026 Jan-Aug period; NOT ITC market-attractiveness ranking'})
    writecsv('output/observed_export_rank_comparison.csv',exportcomp)
    exportstats=[]
    for scope in ['ranked11','all_RCEP14']:
        rs=[r for r in exportcomp if r['scope']==scope]
        a=np.array([r['broad_export_rank'] for r in rs]);b=np.array([r['narrow_export_rank'] for r in rs])
        for method,v in association(a,b).items():exportstats.append({'scope':scope,'method':method,'n':len(rs),'coefficient':v})
    writecsv('output/observed_export_rank_correlations.csv',exportstats)
    pv=draw_figures(sample,s,orig,detail)
    # Trace all source fields, including the non-observed Customs access time.
    manifest=readcsv(ROOT/'metadata/input_file_manifest.csv')
    source_rows=[]
    for r in manifest:
        source_rows.append(dict(r,organization='General Administration of Customs of China' if r['source_id'].startswith('GACC') else
                                'International Trade Centre / local researcher model',
                                url='http://stats.customs.gov.cn/' if r['source_id'].startswith('GACC') else '',
                                accessed_at='not_recorded_user_supplied_export' if r['source_id'].startswith('GACC') else 'see official_itc_source_ledger.csv',
                                local_read_at=started,period=cfg['customs_period'] if r['source_id'].startswith('GACC') else '2020-2025 / EPM snapshot 2026-10-03',
                                hs_version='not_declared_in_user_export' if r['source_id'].startswith('GACC') else 'not declared in stored Trade Map response',
                                query_parameters='China exports; HS from filename; Jan-Aug 2026 per user and existing share table' if r['source_id'].startswith('GACC') else 'see official ledger and model source snapshots'))
    writecsv('metadata/source_ledger.csv',source_rows)
    writecsv('logs/cleaning_log.csv',[
        {'step':'CLEAN-CUSTOMS-850811','input':'raw/customs/2026-china-export-850811.csv','output':'cleaned/customs_country_aggregates.csv',
         'operation':'Decode GB18030; remove empty trailing header logically; validate HS; reject missing amounts/duplicate keys; sum integer CNY by partner',
         'data_changed':'No source values changed; thousands separators parsed only; source CSV physical rows preserved in lineage'},
        {'step':'CLEAN-CUSTOMS-85081110','input':'raw/customs/2026-china-export-85081110.csv','output':'cleaned/customs_country_aggregates.csv',
         'operation':'Same as broad series; retain quantity in raw but do not compute unsupported quantity ratio',
         'data_changed':'No source values changed'},
        {'step':'JOIN-COUNTRY','input':'Customs aggregates; raw/itc-model/model_inputs.csv','output':'input/matched_model_inputs.csv',
         'operation':'Explicit country crosswalk and name equality; 11 ranked sample; 3 missing ITC markets and US separately recorded',
         'data_changed':'None; no missing value imputation'},
        {'step':'RATIO-PRECISION','input':'integer aggregate numerator and denominator','output':'narrow_share',
         'operation':'Compute numerator/denominator before rounding; verify previous ratio within 5.01e-9',
         'data_changed':'Only restores numerical precision from exact source amounts, not a data revision'}])
    writejson('logs/validation.json',{'tests':tests,'all_passed':all(r['passed'] for r in tests),
                                     'source_files_unchanged':all(sha(ROOT/r['snapshot_path'])==r['sha256'] for r in manifest),
                                     'baseline_score_max_abs_error':err,'matched_countries':len(sample),
                                     'customs_countries':len(countries),'negative_numeric_rank_is_better':True})
    summary={'analysis_id':cfg['analysis_id'],'original_model_run_id':json.loads((ROOT/'raw/itc-model/run/run_manifest.json').read_text(encoding='utf-8'))['model_run_id'],
             'started_at':started,'python':sys.version,'numpy':np.__version__,'pillow':pv,'platform':platform.platform(),
             'dependencies_unavailable':['scipy','matplotlib','nbformat','nbclient','ipykernel'],
             'method_fallback':'NumPy/stdlib verified correlation, tie-aware ranks, exact Kendall inversion DP, permutation inference; Pillow figures; ordered Python cell notebook execution',
             'source_mode':'offline user-provided snapshots, no new web access','config':cfg,
             'original_score_max_abs_error':err,'association':corrs,'numeric_rank_association':rankcorrs,'scenario_count':len(scenarios),
             'first_crossings':crossings,'script_sha256':sha(__file__),'config_sha256':sha(ROOT/'config.json')}
    writejson('run/run_manifest.json',summary)
    print(json.dumps({'original_reproduced_max_error':err,'sample_size':len(sample),
                      'association':[{k:r[k] for k in ['method','coefficient','p_value_permutation_two_sided','p_value_holm_3_tests']} for r in corrs],
                      'scenarios':len(scenarios),'source_snapshots_unchanged':True},ensure_ascii=False,indent=2))
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path)
    args=parser.parse_args()
    if args.repo:snapshot(args.repo.resolve())
    run()
