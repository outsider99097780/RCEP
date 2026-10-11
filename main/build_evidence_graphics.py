"""Generate report-local figures; all input files remain read-only."""
import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
import pypdfium2 as pdfium
from pypdf import PdfReader

parser = argparse.ArgumentParser()
parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parent.parent)
parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'graphics')
parser.add_argument('--only-retail', action='store_true')
args = parser.parse_args()
ROOT, OUT = args.project_root, args.output
OUT.mkdir(parents=True, exist_ok=True)
DATA = ROOT / 'data'
RETAIL = DATA/'macro-market/competition/retail-website-data'
pdfmetrics.registerFont(TTFont('CJK',r'C:\Windows\Fonts\simhei.ttf'))
BLUE, ORANGE = '#32658A', '#C57630'

def load_csv(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def hash_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save_csv(name, rows):
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def text(c,x,y,s,size=10,color='#27313a'):
    c.setFillColor(HexColor(color));c.setFont('CJK',size);c.drawString(x,y,str(s))

def axis(c,x,y,w,h,maxval,ticks,unit):
    c.setLineWidth(.5)
    for tick in ticks:
        xx=x+w*tick/maxval
        c.setStrokeColor(HexColor('#e4e7eb'));c.line(xx,y,xx,y+h)
        text(c,xx-6,y-16,f'{tick:g}',9)
    c.setStrokeColor(HexColor('#858a91'));c.line(x,y,x+w,y);c.line(x,y,x,y+h)
    text(c,x+w/2-30,y-37,unit,10)

def bar(c,x,y,w,h,color):
    c.setFillColor(HexColor(color));c.rect(x,y,w,h,stroke=0,fill=1)

def png(name):
    doc=pdfium.PdfDocument(OUT/(name+'.pdf'))
    doc[0].render(scale=2.5).to_pil().save(OUT/(name+'.png'))

summary_path=next((DATA/'roborock-company/wind-financial-data').glob('*财务摘要*.json'))
summary=json.loads(summary_path.read_text(encoding='utf-8-sig'))
values=summary['values']
headers=values[0][1:]
financial=[]
for i, date in sorted(enumerate(headers),key=lambda t:t[1]):
    row={'year':date[:4]}
    for name, label in [('revenue','营业总收入'),('parent_net_profit','归属母公司股东的净利润'),
                        ('operating_cash_flow','经营活动现金净流量')]:
        j=next(j for j,v in enumerate(values) if v[0] and v[0].strip()==label)
        row[name+'_cny_100m']=values[j][i+1]/10000
        row[name+'_cell']=f'{chr(66+i)}{j+1}'
    row['source_file']=str(summary_path.relative_to(ROOT))
    financial.append(row)
primary_path=ROOT/'sources/report/石头科技2025年度报告.pdf'
primary_page=PdfReader(primary_path).pages[9].extract_text()
for x in financial:
    for key in ['revenue','parent_net_profit','operating_cash_flow']:
        # Wind is rounded to CNY10k with 2 decimal places; compare its values to primary table.
        expected=round(x[key+'_cny_100m']*1e8)
        import re
        nums=[int(n.replace(',','')) for n in re.findall(r'\d{1,3}(?:,\d{3}){2,}',primary_page)]
        if not any(abs(n-expected)<=60 for n in nums):
            raise ValueError((x['year'],key,'not reconciled with primary annual report'))
if not args.only_retail:
    save_csv('company_financial_trend_data.csv',financial)
    c=canvas.Canvas(str(OUT/'company_financial_trend.pdf'),pagesize=(480,245))
    axis(c,45,55,145,145,225,[0,50,100,150,200],'亿元人民币')
    axis(c,280,55,168,145,26,[0,5,10,15,20,25],'亿元人民币')
    text(c,90,226,'营业收入',12);text(c,318,226,'利润与现金回收',12)
    for i,r in enumerate(financial):
        y=178-i*50
        text(c,12,y+2,r['year'],9);text(c,245,y+2,r['year'],9)
        v=r['revenue_cny_100m'];bar(c,45,y-6,145*v/225,23,BLUE);text(c,49+145*v/225,y,f'{v:.2f}',9)
        for j,(key,color) in enumerate([('parent_net_profit_cny_100m',BLUE),('operating_cash_flow_cny_100m',ORANGE)]):
            yy=y+9-j*18;v=r[key];bar(c,280,yy,168*v/26,13,color);text(c,284+168*v/26,yy+2,f'{v:.2f}',8.5)
    bar(c,278,207,7,7,BLUE);text(c,289,207,'归母净利润',8)
    bar(c,374,207,7,7,ORANGE);text(c,385,207,'经营现金净流量',8)
    c.save();png('company_financial_trend')

products=load_csv(RETAIL/'cleaned/products.csv')
ledger=load_csv(RETAIL/'metadata/source_ledger.csv')
ledger_by={x['source_ledger_id']:x for x in ledger}
brands=['Roborock','Ecovacs','Xiaomi','Dreame','Narwal']
market_info={'JPN':('日本',10000,'万日元'),'KOR':('韩国',10000,'万韩元'),
             'AUS':('澳大利亚',1,'澳元'),'NZL':('新西兰',1,'新西兰元')}
nz_products=load_csv(RETAIL/'cleaned/products_NZL_detailed.csv')
nz_ledger=load_csv(RETAIL/'metadata/source_ledger_NZL.csv')
ledger_by.update({x['source_ledger_id']:x for x in nz_ledger})
price_inputs=[]
price_rows=[]
for code,(name,scale,unit) in market_info.items():
    for brand in brands:
        source_products=nz_products if code=='NZL' else products
        eligible=[x for x in source_products if x['country_code']==code and x['brand']==brand and x['purchase_type']!='overseas_purchase' and x['representative_price']]
        price_inputs.extend(eligible)
        strict=[x for x in eligible if int(x['normal_offer_count'])>=3]
        price_rows.append({'country_code':code,'brand':brand,'currency':eligible[0]['currency'] if eligible else None,
          'n_all_priced':len(eligible),'median_all':float(statistics.median(Decimal(x['representative_price']) for x in eligible)) if eligible else None,
          'n_ge3_normal_offers':len(strict),'median_ge3_normal_offers':float(statistics.median(Decimal(x['representative_price']) for x in strict)) if strict else None,
          'source_ledger_ids':';'.join(x['source_ledger_id'] for x in eligible),
          'source_data_file':'cleaned/products_NZL_detailed.csv' if code=='NZL' else 'cleaned/products.csv',
          'source_ledger_file':'metadata/source_ledger_NZL.csv' if code=='NZL' else 'metadata/source_ledger.csv',
          'snapshot_date':'2026-10-10' if code=='NZL' else '2026-10-02',
          'representative_price_rule':'median of at least two eligible new offers; single quote retained; stock-unconfirmed offers included' if code=='NZL' else 'median of at least three normal offers, otherwise minimum normal offer'})
save_csv('retail_brand_price_data.csv',price_rows)
c=canvas.Canvas(str(OUT/'retail_brand_price_comparison.pdf'),pagesize=(600,470))
def price_label(value,scale,code):
    number=Decimal(str(value))/Decimal(scale)
    quantum=Decimal('0.1') if code=='AUS' else Decimal('0.01')
    return format(number.quantize(quantum,rounding=ROUND_HALF_UP),',.1f' if code=='AUS' else ',.2f')
for panel,(code,(name,scale,unit)) in enumerate(market_info.items()):
    rr=[x for x in price_rows if x['country_code']==code]
    ox,oy=(14+(panel%2)*300,250-(panel//2)*230)
    x0,y0,width,height=ox+82,oy+42,150,155
    mx={'JPN':12,'KOR':220,'AUS':2400,'NZL':3000}[code]
    ticks={'JPN':[0,4,8,12],'KOR':[0,50,100,150,200],'AUS':[0,800,1600,2400],'NZL':[0,1000,2000,3000]}[code]
    c.setLineWidth(.5)
    for tick in ticks:
        xx=x0+width*tick/mx
        c.setStrokeColor(HexColor('#e4e7eb'));c.line(xx,y0,xx,y0+height)
        c.setFillColor(HexColor('#27313a'));c.setFont('CJK',10.5);c.drawCentredString(xx,y0-17,str(tick))
    c.setStrokeColor(HexColor('#858a91'));c.line(x0,y0,x0+width,y0);c.line(x0,y0,x0,y0+height)
    c.setFont('CJK',11);c.drawCentredString(x0+width/2,y0-36,unit)
    text(c,ox+82,oy+203,name,14)
    text(c,ox+153,oy+204,'PriceSpy 2026-10-10' if code=='NZL' else {'JPN':'Kakaku','KOR':'Danawa','AUS':'GetPrice'}[code]+' 2026-10-02',9.5)
    for i,r in enumerate(rr):
        y=oy+180-i*30
        text(c,ox,y+3,r['brand'],11.5)
        text(c,ox,y-9,f"n={r['n_all_priced']}",9.5,color='#666666')
        if r['median_all'] is None:
            text(c,x0+4,y,'无合格新品报价' if code=='NZL' else '未采得样本',11,'#777777')
            continue
        v=r['median_all']/scale
        bar(c,x0,y-5,width*v/mx,18,ORANGE if r['brand']=='Roborock' else BLUE)
        text(c,x0+width*v/mx+3,y,price_label(r['median_all'],scale,code),10.5)
c.save();png('retail_brand_price_comparison')

manifest={'generated_at':datetime.now(timezone.utc).isoformat(),'source_access_dates':{'retail_JPN_KOR_AUS':'2026-10-02','retail_NZL':'2026-10-10','local_report_review':'2026-10-11'},
 'financial':{'data':'company_financial_trend_data.csv','unit_conversion':'Wind万元 /10000 = 亿元人民币','source_sha256':hash_file(summary_path),
   'crosscheck':{'file':str(primary_path.relative_to(ROOT)),'pdf_page':10,'sha256':hash_file(primary_path),'tolerance_cny':60},
   'excluded_conflict':'Wind地区表缺少显式金额单位，且2025国外收入与年报分地区主营收入不同；正文分地区数值采用年报第54--55页，不用于本图。'},
 'retail':{'data':'retail_brand_price_data.csv','source_file':str((RETAIL/'cleaned/products.csv').relative_to(ROOT)),
   'source_sha256':hash_file(RETAIL/'cleaned/products.csv'),'ledger_sha256':hash_file(RETAIL/'metadata/source_ledger.csv'),
   'grain':'一条网站产品ID/变体；不按销量加权，不跨国汇率折算，不推断全市场品牌份额',
   'selection_by_market':{'JPN_KOR_AUS':'排除韩国海外购与缺失价格；正常报价至少3条取中位数，否则取最低正常报价',
                          'NZL':'使用分国明细的合格新品代表价：至少两条取中位数，单报价照录；保留库存未确认报价，排除明确无货、二手和错型号'},
   'sensitivity':'同品牌另算normal_offer_count>=3子样本中位数；对NZL此列为至少三条合格新品报价子样本，不改变至少两条取中位数的原代表价规则；不是置信区间',
   'rows_by_market':dict(Counter(x['country_code'] for x in products)),
   'priced_rows_in_figure_by_market':dict(Counter(x['country_code'] for x in price_inputs)),
   'excluded_overseas_purchase_KOR':sum(x['country_code']=='KOR' and x['purchase_type']=='overseas_purchase' for x in products),
   'missing_observations':'AUS Xiaomi/Narwal未采得样本；NZL Narwal两页无合格报价，均不能解释为没有市场销售',
   'MYS_exclusion':'44个缓存产品页及历史报道未构成可核验当期报价，不计算当期品牌中位价；正文继续单独说明PriceShop发表时价格。',
   'additional_sources':[{'file':str(p.relative_to(ROOT)), 'sha256':hash_file(p)} for p in [
       RETAIL/'cleaned/products_NZL_detailed.csv', RETAIL/'metadata/source_ledger_NZL.csv',
       RETAIL/'cleaned/products_MYS_detailed.csv', RETAIL/'cleaned/historical_price_evidence_MYS.csv',
       RETAIL/'metadata/source_ledger_MYS.csv']],
   'rounding':'数值标签先按当地币种缩放，再以Decimal ROUND_HALF_UP舍入；品牌中位数使用未缩放的原代表价计算。',
   'product_citations':[{'ledger_id':x['source_ledger_id'],
       'url':ledger_by[x['source_ledger_id']].get('query_or_product_url') or x['product_url'],
       'accessed_at':ledger_by[x['source_ledger_id']].get('accessed_at') or x['first_seen_at'],
       'raw_record_path':x['raw_record_path'], 'raw_sha256':hash_file(RETAIL/x['raw_record_path'])} for x in price_inputs],
   'outputs':[{'file':name,'sha256':hash_file(OUT/name)} for name in [
       'retail_brand_price_comparison.pdf','retail_brand_price_comparison.png','retail_brand_price_data.csv']]}}
(OUT/'new_figures_provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'financial':financial,'retail':price_rows},ensure_ascii=False,indent=2))
