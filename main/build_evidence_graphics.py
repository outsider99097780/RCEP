"""Generate report-local figures; all input files remain read-only."""
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
import pypdfium2 as pdfium
from pypdf import PdfReader

ROOT = (Path(__file__).resolve().parent.parent if Path(__file__).resolve().parent.name == 'main'
        else Path(r'C:\Users\99097\Documents\GitHub\RCEP'))
OUT = Path(__file__).resolve().parent / 'graphics'
OUT.mkdir(exist_ok=True)
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
market_info={'JPN':('日本',10000,'万日元'),'KOR':('韩国',10000,'万韩元'),'AUS':('澳大利亚',1,'澳元')}
price_rows=[]
for code,(name,scale,unit) in market_info.items():
    for brand in brands:
        eligible=[x for x in products if x['country_code']==code and x['brand']==brand and x['purchase_type']!='overseas_purchase' and x['representative_price']]
        strict=[x for x in eligible if int(x['normal_offer_count'])>=3]
        price_rows.append({'country_code':code,'brand':brand,'currency':eligible[0]['currency'] if eligible else None,
          'n_all_priced':len(eligible),'median_all':statistics.median(float(x['representative_price']) for x in eligible) if eligible else None,
          'n_ge3_normal_offers':len(strict),'median_ge3_normal_offers':statistics.median(float(x['representative_price']) for x in strict) if strict else None,
          'source_ledger_ids':';'.join(x['source_ledger_id'] for x in eligible)})
save_csv('retail_brand_price_data.csv',price_rows)
c=canvas.Canvas(str(OUT/'retail_brand_price_comparison.pdf'),pagesize=(480,250))
for panel,(code,(name,scale,unit)) in enumerate(market_info.items()):
    rr=[x for x in price_rows if x['country_code']==code]
    x0=panel*138+57
    mx={'JPN':12,'KOR':220,'AUS':2400}[code]
    ticks={'JPN':[0,4,8,12],'KOR':[0,50,100,150,200],'AUS':[0,800,1600,2400]}[code]
    axis(c,x0,50,105,165,mx,ticks,unit)
    text(c,panel*138+86,229,name,12)
    for i,r in enumerate(rr):
        y=198-i*30
        if panel==0:text(c,6,y,r['brand'],9)
        if r['median_all'] is None:
            text(c,x0+4,y,'未采得样本',8.5,'#777777')
            continue
        v=r['median_all']/scale
        bar(c,x0,y-5,105*v/mx,18,ORANGE if r['brand']=='Roborock' else BLUE)
        text(c,x0+105*v/mx+3,y,f'{v:.2f}' if scale>1 else f'{v:,.1f}',8.5)
c.save();png('retail_brand_price_comparison')

manifest={'generated_at':'2026-10-10','source_access_dates':{'retail':'2026-10-02','local_report_review':'2026-10-10'},
 'financial':{'data':'company_financial_trend_data.csv','unit_conversion':'Wind万元 /10000 = 亿元人民币','source_sha256':hash_file(summary_path),
   'crosscheck':{'file':str(primary_path.relative_to(ROOT)),'pdf_page':10,'sha256':hash_file(primary_path),'tolerance_cny':60},
   'excluded_conflict':'Wind地区表缺少显式金额单位，且2025国外收入与年报分地区主营收入不同；正文分地区数值采用年报第54--55页，不用于本图。'},
 'retail':{'data':'retail_brand_price_data.csv','source_file':str((RETAIL/'cleaned/products.csv').relative_to(ROOT)),
   'source_sha256':hash_file(RETAIL/'cleaned/products.csv'),'ledger_sha256':hash_file(RETAIL/'metadata/source_ledger.csv'),
   'grain':'一条网站产品ID/变体；不按销量加权，不跨国汇率折算，不推断全市场品牌份额',
   'selection':'排除韩国海外购与缺失价格；代表价沿用清洗层：正常报价至少3条取中位数，否则取最低正常报价',
   'sensitivity':'同品牌另算normal_offer_count>=3子样本中位数，见CSV；不是置信区间',
   'rows_by_market':dict(Counter(x['country_code'] for x in products)),
   'missing_observations':'AU Xiaomi/Narwal为未采得样本，不能解释为没有市场销售',
   'product_citations':[{'ledger_id':x['source_ledger_id'],'url':x['product_url'],'accessed_at':x['first_seen_at'],'raw_record_path':x['raw_record_path']} for x in products if x['purchase_type']!='overseas_purchase' and x['representative_price']]}}
(OUT/'new_figures_provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'financial':financial,'retail':price_rows},ensure_ascii=False,indent=2))
