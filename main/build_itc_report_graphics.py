"""Refresh report-local figures from saved HS850811 results; never refit the model."""
import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import pypdfium2 as pdfium

parser = argparse.ArgumentParser()
parser.add_argument('--project-root', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root, out = args.project_root, args.output
out.mkdir(parents=True, exist_ok=True)
model = root / 'data/macro-market/ITC/ITC-analysis-result'
raw = root / 'data/macro-market/ITC/ITC-data'
pdfmetrics.registerFont(TTFont('ITC-CJK', r'C:\Windows\Fonts\simhei.ttf'))
BLUE, ORANGE, GREY, TEXT = '#32658A', '#C57630', '#D6DCE2', '#27313A'
NAMES = {'036':'澳大利亚','096':'文莱','116':'柬埔寨','360':'印度尼西亚','392':'日本','410':'韩国',
         '418':'老挝','104':'缅甸','458':'马来西亚','554':'新西兰','608':'菲律宾','702':'新加坡','764':'泰国','704':'越南'}
COUNTRIES = {'410':'south-korea','036':'australia','458':'malaysia','554':'new-zealand','392':'japan'}
TOP = list(COUNTRIES)
used_sources = set()

def read(path):
    used_sources.add(path)
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def save_csv(name, rows):
    with (out/name).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def label(c, x, y, value, size=10, align='left', color=TEXT):
    c.setFont('ITC-CJK', size)
    c.setFillColor(HexColor(color))
    getattr(c, {'left':'drawString','right':'drawRightString','center':'drawCentredString'}[align])(x, y, str(value))

def rectangle(c, x, y, w, h, color):
    c.setFillColor(HexColor(color))
    c.rect(x, y, max(w, 0), h, stroke=0, fill=1)

def haxis(c, x, y, w, h, maximum, ticks, unit):
    c.setLineWidth(.5)
    for tick in ticks:
        xx = x + w*tick/maximum
        c.setStrokeColor(HexColor('#E3E7EB'))
        c.line(xx, y, xx, y+h)
        label(c, xx, y-17, f'{tick:g}', 9, 'center')
    c.setStrokeColor(HexColor('#858A91'))
    c.line(x, y, x+w, y)
    label(c, x+w/2, y-37, unit, 10, 'center')

def finish(c, name):
    c.save()
    document = pdfium.PdfDocument(out/(name+'.pdf'))
    image = document[0].render(scale=2.5).to_pil()
    image.save(out/(name+'.png'))
    document.close()

inputs = read(model/'model_inputs.csv')
epm = read(model/'cleaned/epi.csv')
annual = read(model/'cleaned/trade_annual.csv')
ranking = read(model/'strategy_topsis_scores.csv')
ranks = read(model/'model/intermediate/monte_carlo_ranks.csv')
weights = read(model/'model_weights.csv')
normalized = read(model/'model_normalized.csv')
used_sources.add(model/'methodology.md')
manifest = json.loads((model/'run/run_manifest.json').read_text(encoding='utf-8'))
used_sources.add(model/'run/run_manifest.json')
assert len(ranks) == 5000
assert [r['market'] for r in ranking[:5]] == [NAMES[code] for code in TOP]
assert all(abs(sum(float(r[k]) for r in weights)-1) < 1e-10 for k in ['strategy_weight','equal_weight','entropy_weight'])
by_name = {r['country_name']:r for r in inputs}
by_code = {r['country_code']:r for r in inputs}
epi_by_code = {r['country_code']:r for r in epm}

# 1. Import size and growth: retain the logarithmic size axis, not a new model.
scatter = []
for r in inputs:
    if not r['imports_2025_usd_thousand'] or not r['import_cagr_2020_2025_pct'] or not r['china_share_2025_pct']:
        continue
    scatter.append({'country_code':r['country_code'],'market':NAMES[r['country_code']],
                    'imports_2025_usd_thousand':float(r['imports_2025_usd_thousand']),
                    'import_cagr_2020_2025_pct':float(r['import_cagr_2020_2025_pct']),
                    'china_share_2025_pct':float(r['china_share_2025_pct']), 'source_ids':r['source_ids']})
assert len(scatter) == 11
save_csv('itc_market_size_growth_data.csv', scatter)
c = canvas.Canvas(str(out/'market_size_growth.pdf'), pagesize=(540,320))
x0,y0,w,h = 70,65,405,205
logmin,logmax = -2,3
for tick in [.01,.1,1,10,100,1000]:
    xx = x0+w*(math.log10(tick)-logmin)/(logmax-logmin)
    c.setStrokeColor(HexColor('#E3E7EB'));c.setLineWidth(.5);c.line(xx,y0,xx,y0+h)
    label(c,xx,y0-17,f'{tick:g}',9,'center')
for tick in [-20,-10,0,10,20,30]:
    yy = y0+h*(tick+25)/55
    c.setStrokeColor(HexColor('#BAC2CB') if tick==0 else HexColor('#E3E7EB'))
    c.line(x0,yy,x0+w,yy);label(c,x0-10,yy-3,str(tick),9,'right')
label(c,14,292,'CAGR（%）',10)
label(c,x0+w/2,20,'2025年进口额（百万美元，对数刻度）',10,'center')
label(c,70,292,'● 前五重点市场',10,color=ORANGE)
label(c,225,292,'● 其余市场（气泡面积：中国份额）',10,color=BLUE)
offsets={'410':(-42,13),'036':(-17,-19),'458':(12,3),'554':(-53,-16),'392':(-38,-19),
         '116':(10,-10),'360':(-65,-3),'608':(8,10),'702':(-55,9),'764':(-35,13),'096':(8,9)}
for r in scatter:
    xx=x0+w*(math.log10(r['imports_2025_usd_thousand']/1000)-logmin)/(logmax-logmin)
    yy=y0+h*(r['import_cagr_2020_2025_pct']+25)/55
    color=ORANGE if r['country_code'] in TOP else BLUE
    c.setFillColor(HexColor(color));c.circle(xx,yy,math.sqrt(r['china_share_2025_pct'])*.9,stroke=0,fill=1)
    dx,dy=offsets[r['country_code']];label(c,xx+dx,yy+dy,r['market'],9)
finish(c,'market_size_growth')

# 2. EPI and untapped amount, all 14 saved markets including the excluded three.
epi_rows = []
for r in sorted(epm,key=lambda r:float(r['epi_potential_usd']),reverse=True):
    epi_rows.append({'country_code':r['country_code'],'market':NAMES[r['country_code']],
                     'epi_potential_usd':float(r['epi_potential_usd']), 'baseline_exports_usd':float(r['baseline_exports_usd']),
                     'untapped_potential_usd':float(r['untapped_potential_usd']), 'source_id':r['source_id']})
save_csv('itc_epi_untapped_data.csv',epi_rows)
c=canvas.Canvas(str(out/'epi_untapped.pdf'),pagesize=(540,420))
haxis(c,85,55,365,325,700,[0,100,200,300,400,500,600,700],'金额（百万美元）')
rectangle(c,89,397,11,7,BLUE);label(c,105,395,'EPI潜在额',10)
rectangle(c,241,397,11,7,ORANGE);label(c,257,395,'未实现潜力金额',10)
for i,r in enumerate(epi_rows):
    y=365-i*23
    label(c,74,y-2,r['market'],10,'right')
    for offset,key,color in [(3,'epi_potential_usd',BLUE),(-5,'untapped_potential_usd',ORANGE)]:
        value=r[key]/1e6
        rectangle(c,85,y+offset,365*value/700,6,color)
    label(c,459,y-1,f"{r['epi_potential_usd']/1e6:.1f} / {r['untapped_potential_usd']/1e6:.1f}",9)
finish(c,'epi_untapped')

# 3. Strategy ranking, unchanged score values; retain five highlighted rows.
score_rows=[]
for i,r in enumerate(ranking):
    source=by_name[r['country_name']]
    score_rows.append({'rank':i+1,'country_code':source['country_code'],'market':r['market'],'score':float(r['score'])})
save_csv('itc_market_score_data.csv',score_rows)
c=canvas.Canvas(str(out/'market_score.pdf'),pagesize=(540,350))
haxis(c,105,55,350,260,1,[0,.2,.4,.6,.8,1],'战略权重TOPSIS得分')
for i,r in enumerate(score_rows):
    y=297-i*22
    label(c,93,y+3,f"{r['rank']}. {r['market']}",10,'right')
    rectangle(c,105,y,350*r['score'],13,ORANGE if r['country_code'] in TOP else BLUE)
    label(c,112+350*r['score'],y+2,f"{r['score']:.4f}",9)
finish(c,'market_score')

# 4. Top-five frequency from the already stored draws: no resampling.
frequency=[]
for r in score_rows:
    code=r['country_code']; count=sum(int(draw[code])<=5 for draw in ranks)
    frequency.append({'country_code':code,'market':r['market'],'base_rank':r['rank'],
                      'top5_count':count,'draw_count':len(ranks),'top5_share':count/len(ranks),'top5_pct':count/len(ranks)*100,
                      'source_file':'model/intermediate/monte_carlo_ranks.csv'})
assert sum(r['top5_count'] for r in frequency)==5000*5
save_csv('itc_ranking_sensitivity_data.csv',frequency)
c=canvas.Canvas(str(out/'ranking_sensitivity.pdf'),pagesize=(540,350))
haxis(c,105,55,345,260,100,[0,20,40,60,80,100],'进入前五名的情景比例（%）')
for i,r in enumerate(frequency):
    y=297-i*22
    label(c,94,y+3,r['market'],10,'right')
    rectangle(c,105,y,345*r['top5_share'],13,ORANGE if r['country_code'] in TOP else BLUE)
    label(c,112+345*r['top5_share'],y+2,f"{r['top5_pct']:.2f}%",9)
finish(c,'ranking_sensitivity')

# 5. Macro supplier composition is not brand market share.
suppliers=[]
for code,folder in COUNTRIES.items():
    records=read(raw/folder/'derived/top_suppliers_2025.csv')
    first,second=records[:2]
    assert first['supplier_code']=='156'
    a,b=float(first['share_2025_pct']),float(second['share_2025_pct'])
    suppliers.append({'country_code':code,'market':NAMES[code],'china_share_pct':a,
                       'second_supplier':second['supplier_name'],'second_supplier_share_pct':b,'others_share_pct':100-a-b,
                       'share_gap_pp':a-b,'source_ids':first['source_ids']})
save_csv('itc_supplier_concentration_data.csv',suppliers)
c=canvas.Canvas(str(out/'supplier_concentration.pdf'),pagesize=(540,260))
haxis(c,85,55,390,150,100,[0,20,40,60,80,100],'占目标市场进口额的比例（%）')
for i,(name,color) in enumerate([('中国',BLUE),('第二供应国',ORANGE),('其余来源',GREY)]):
    rectangle(c,85+i*135,233,10,8,color);label(c,100+i*135,232,name,10)
for i,r in enumerate(suppliers):
    y=187-i*29;label(c,74,y+5,r['market'],10,'right');left=85
    for key,color in [('china_share_pct',BLUE),('second_supplier_share_pct',ORANGE),('others_share_pct',GREY)]:
        value=r[key];width=390*value/100
        rectangle(c,left,y,width,20,color)
        if value>=10:
            label(c,left+width/2,y+6,f'{value:.1f}%',9,'center', '#FFFFFF' if color in [BLUE,ORANGE] else TEXT)
        left+=width
finish(c,'supplier_concentration')

# Preserve the small, exact arithmetic supporting country interpretations.
interpretations=[]
for code in TOP:
    start=next(r for r in annual if r['country_code']==code and r['year']=='2020')
    end=next(r for r in annual if r['country_code']==code and r['year']=='2025')
    e=epi_by_code[code]
    a,b=float(start['world_imports_usd_thousand']),float(end['world_imports_usd_thousand'])
    ca,cb=float(start['imports_from_china_usd_thousand']),float(end['imports_from_china_usd_thousand'])
    potential,baseline=float(e['epi_potential_usd']),float(e['baseline_exports_usd'])
    interpretations.append({'country_code':code,'market':NAMES[code],'world_imports_2020_usd_thousand':a,
         'world_imports_2025_usd_thousand':b,'china_imports_2020_usd_thousand':ca,'china_imports_2025_usd_thousand':cb,
         'china_share_2020_pct':ca/a*100,'china_share_2025_pct':cb/b*100,
         'other_origins_change_usd_thousand':(b-cb)-(a-ca), 'epi_potential_usd':potential,'baseline_exports_usd':baseline,
         'realized_ratio_pct':baseline/potential*100,'untapped_ratio_pct':max(potential-baseline,0)/potential*100,
         'trade_source_id':start['import_source_id'],'epi_source_id':e['source_id']})
save_csv('itc_country_interpretation_data.csv',interpretations)
provenance={'generated_at':datetime.now(timezone.utc).isoformat(),'model_run_id':manifest['model_run_id'],
            'source_access_date':'2026-10-03','hs_code':'850811','model_refit':False,'weight_change':False,
            'historical_random_seed':850980,
            'top5_rule':'base strategy ranking first five; scenario frequency = count(saved rank <= 5) / 5000',
            'sources':[{'file':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(used_sources)],
            'outputs':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.glob('itc_*_data.csv'))],
            'checks':{'rank_order_matches_saved_scores':True,'monte_carlo_draw_count':len(ranks),'top5_total_memberships':25000,
                      'complete_import_markets':len(scatter),'epi_markets':len(epi_rows)},
            'scope':'Only report-local charts and arithmetic companions; raw ITC data and model output files are read-only.'}
(out/'itc_model_figures_provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'model_run_id':manifest['model_run_id'],'top5':TOP,'frequency':frequency,'interpretations':interpretations},ensure_ascii=False))
