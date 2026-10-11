"""Build and execute a notebook companion without installing a Jupyter runtime.

Every code cell is executed in order in a fresh shared Python namespace. The
result is a standard nbformat-4 JSON notebook with saved stream/image outputs.
This is NOT a Jupyter-kernel or nbclient execution claim.
"""
from __future__ import annotations
import base64
import contextlib
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
import verify_model as v

def facts():
    cfg,countries,sample,x,s,w,orig,ranks,lineage,checks=v.load_data()
    corr=v.readcsv(ROOT/'output/association_tests.csv')
    numeric=v.readcsv(ROOT/'output/share_vs_numeric_rank.csv')
    sc=v.readcsv(ROOT/'output/scenario_summary.csv')
    detail=v.readcsv(ROOT/'output/scenario_country_rankings.csv')
    rows=[]
    def add(fid,metric,value,loc,sources,unit='unitless',status='verified_calculation_scope_limited'):
        path=loc.split('#')[0]
        rows.append({'fact_id':fid,'metric_name':metric,'value_json':json.dumps(value,ensure_ascii=False),
                     'unit':unit,'output_locator':loc,'output_sha256':v.sha(ROOT/path),
                     'source_ids':sources,'source_lookup':'metadata/source_ledger.csv;metadata/official_itc_source_ledger.csv',
                     'analysis_id':cfg['analysis_id'],'period':'Customs 2026 Jan-Aug; ITC trade 2020-2025 and EPM 2026-10-03 snapshot',
                     'status':status,'citation_label':f'[HS85081110-ITC验证,{cfg["analysis_id"]},{fid}]'})
    add('V-001','matched sample / excluded scope',{'n':len(sample),'excluded':['VNM','LAO','MMR'],'reference':'USA'},
        'metadata/coverage.csv#model_status','GACC-850811;GACC-85081110;ITC-MODEL-model_inputs.csv')
    val=json.loads((ROOT/'logs/validation.json').read_text(encoding='utf-8'))
    add('V-002','baseline reproduction',val,'logs/validation.json#baseline_score_max_abs_error','ITC-MODEL-strategy_topsis_scores.csv;ITC-MODEL-model_inputs.csv;ITC-MODEL-model_weights.csv')
    for fid,r in zip(['V-010','V-011','V-012'],corr):
        add(fid,'share versus score '+r['method'],r,'output/association_tests.csv#method='+r['method'],'GACC-850811;GACC-85081110;ITC-MODEL-strategy_topsis_scores.csv')
    add('V-013','Holm and exact Kendall p',[{k:r[k] for k in ['method','p_value_holm_3_tests','p_value_exact_no_ties']} for r in corr],
        'output/association_tests.csv#method','GACC-850811;GACC-85081110;ITC-MODEL-strategy_topsis_scores.csv')
    add('V-014','share versus numeric rank',numeric,'output/share_vs_numeric_rank.csv#method','GACC-850811;GACC-85081110;ITC-MODEL-strategy_topsis_scores.csv')
    leave=v.readcsv(ROOT/'output/leave_one_country_out.csv')
    add('V-015','leave one country out',[r for r in leave if r['method']=='pearson' and r['excluded_iso3'] in ['BRN','SGP']],
        'output/leave_one_country_out.csv#method=pearson;excluded_iso3=BRN|SGP','GACC-850811;GACC-85081110;ITC-MODEL-strategy_topsis_scores.csv')
    add('V-016','bootstrap country-resampling intervals',[{k:r[k] for k in ['method','bootstrap_percentile_95_low','bootstrap_percentile_95_high']} for r in corr],
        'output/association_tests.csv#method','GACC-850811;GACC-85081110;ITC-MODEL-strategy_topsis_scores.csv')
    add('V-020','monetary proxy scenarios',[r for r in sc if r['scenario_family'].startswith('scale_')],
        'output/scenario_summary.csv#scenario_family=scale_*','GACC-850811;GACC-85081110;ITC-MODEL-model_inputs.csv;ITC-MODEL-model_weights.csv',status='verified_conditional_stress_test_not_official_ITC')
    add('V-021','sixth indicator scenarios',[r for r in sc if r['scenario_family']=='add_sixth_indicator'],
        'output/scenario_summary.csv#scenario_family=add_sixth_indicator','GACC-850811;GACC-85081110;ITC-MODEL-model_inputs.csv;ITC-MODEL-model_weights.csv',status='verified_conditional_stress_test_not_official_ITC')
    add('V-022','direct score-times-share diagnostic',[r for r in detail if r['scenario']=='score_times_share'],
        'output/scenario_country_rankings.csv#scenario=score_times_share','GACC-850811;GACC-85081110;ITC-MODEL-strategy_topsis_scores.csv',status='verified_conditional_stress_test_not_official_ITC')
    add('V-023','first grid crossing',v.readcsv(ROOT/'output/stress_first_crossings.csv'),
        'output/stress_first_crossings.csv#scenario_family;event','GACC-850811;GACC-85081110;ITC-MODEL-model_inputs.csv;ITC-MODEL-model_weights.csv',status='verified_conditional_stress_test_not_official_ITC')
    add('V-024','Japan / Indonesia monetary-scaling boundary',[r for r in detail if r['scenario'] in ['baseline','scale_size_and_untapped_a1.00'] and r['iso3'] in ['JPN','IDN']],
        'output/scenario_country_rankings.csv#iso3=JPN|IDN;scenario=baseline|scale_size_and_untapped_a1.00','GACC-850811;GACC-85081110;ITC-MODEL-model_inputs.csv;ITC-MODEL-model_weights.csv',status='verified_conditional_stress_test_not_official_ITC')
    add('V-025','original normalization anchors',[r for r in v.readcsv(ROOT/'raw/itc-model/model_inputs.csv') if r['country_code'] in ['096','702']],
        'raw/itc-model/model_inputs.csv#country_code=096|702','TM-096-target_import_imports_by_supplier-VAL;EPM-096;TM-702-target_import_imports_by_supplier-VAL;EPM-702')
    add('V-030','observed same-period broad / narrow export rankings',
        {'correlations':v.readcsv(ROOT/'output/observed_export_rank_correlations.csv'),
         'rankings':v.readcsv(ROOT/'output/observed_export_rank_comparison.csv')},
        'output/observed_export_rank_comparison.csv#scope=all_RCEP14;iso3','GACC-850811;GACC-85081110',unit='rank')
    for c in countries:
        add('S-'+c['iso3'],'customs value ratio',c['narrow_share'],
            'cleaned/customs_country_aggregates.csv#iso3='+c['iso3'],'GACC-850811;GACC-85081110',unit='fraction')
    v.writecsv('metadata/fact_registry.csv',rows)
    field_rows=[]
    old=v.readcsv(ROOT/'raw/itc-model/model/input/input_lineage.csv')
    for c in sample:
        for field,original in [('market_size','imports_2025_usd_thousand'),('market_growth','import_cagr_2020_2025_pct'),
                               ('china_share','china_share_2025_pct'),('untapped_amount','untapped_potential_usd'),
                               ('untapped_ratio','untapped_potential_usd')]:
            r=next(r for r in old if r['country_code']==c['itc_country_code'] and r['field']==original)
            field_rows.append({'iso3':c['iso3'],'field':field,'source_ids':r['source_ids'],
                               'raw_locator':r['raw_locators'],'formula':r['formula'] if field!='untapped_ratio' else 'untapped_potential_usd / epi_potential_usd',
                               'period':r['period'],'unit':r['unit'] if field!='untapped_ratio' else 'fraction',
                               'accessed_at':r['accessed_at'],'query_urls':r['query_urls'],'source_sha256':r['source_sha256']})
        field_rows.append({'iso3':c['iso3'],'field':'narrow_share','source_ids':'GACC-850811;GACC-85081110',
                           'raw_locator':'metadata/customs_row_lineage.csv#iso3='+c['iso3'],
                           'formula':'sum(narrow CNY)/sum(broad CNY), no pre-rounding','period':cfg['customs_period'],
                           'unit':'fraction','accessed_at':'not_recorded_user_supplied_export','query_urls':'http://stats.customs.gov.cn/',
                           'source_sha256':v.sha(ROOT/'raw/customs/2026-china-export-850811.csv')+';'+v.sha(ROOT/'raw/customs/2026-china-export-85081110.csv')})
    v.writecsv('metadata/model_input_lineage.csv',field_rows)
    figures=[{'figure':p.name,'data_source':'input/matched_model_inputs.csv' if p.name=='share_vs_score.png' else 'output/scenario_country_rankings.csv',
              'source_ids':'GACC-850811;GACC-85081110;ITC-MODEL-strategy_topsis_scores.csv;ITC-MODEL-model_inputs.csv',
              'sha256':v.sha(p),'renderer':'Pillow, editable drawing code in code/verify_model.py',
              'scope':'11 modeled countries; Customs Jan-Aug 2026 value ratio; frozen ITC model',
              'visual_qa':'Inspected both PNGs; Japan/Indonesia label collision corrected before final review'} for p in sorted((ROOT/'output/figures').glob('*.png'))]
    v.writejson('output/figures/figure_sources.json',figures)

def notebook():
    cells=[]
    def md(text):cells.append({'cell_type':'markdown','metadata':{},'source':text})
    def code(text):cells.append({'cell_type':'code','metadata':{},'source':text,'execution_count':None,'outputs':[]})
    md('# 海关产品结构与 ITC 国家排名验证\n\n## tl;dr\n\n原算法下调整金额指标没有改变 11 国排序。占比作为第六项指标、权重 20% 时，前五成员不变；直接乘原得分的强化诊断让泰国替换日本。完整解读见 `output/验证结果与建议.md`。原数据、原 ITC 结果与 main.tex 均未改动。')
    md('## Context & Methods\n\n海关为 2026 年 1—8 月中国出口金额占比，ITC 主要为 2025 年需求和 2020—2025 年增长。不是台数占比。原模型五权重 0.30/0.10/0.10/0.30/0.20。\n\n### Key Assumptions\n\n中国出口结构不能直接代表目的地全部进口结构；迁移仅是压力测试。排名样本 11 国，越南/老挝/缅甸不补值，美国只保留参照。置换 p 值是标签交换参照，不是因果证据。\n\n执行说明：此笔记由顺序 Python 代码单元执行器运行并保存输出；当前环境没有 Jupyter 内核、nbclient、nbformat。')
    code("from pathlib import Path\nimport sys, json\nROOT = Path.cwd()\nassert (ROOT / 'config.json').is_file(), '请在 ITC-model-verification 目录运行'\nsys.dont_write_bytecode = True\nsys.path.insert(0, str(ROOT / 'code'))\nimport verify_model as v\nimport numpy as np\nprint(json.dumps(json.loads((ROOT/'config.json').read_text(encoding='utf-8')), ensure_ascii=False, indent=2))")
    md('## Data\n\n### 1. 检查冻结输入与国家连接\n\n原始来源和查询见 `metadata/source_ledger.csv` 与 `metadata/official_itc_source_ledger.csv`；按源文件字节 SHA-256 核验。')
    code("cfg,countries,sample,x,s,w,orig,ranks,lineage,checks = v.load_data()\nmanifest = v.readcsv(ROOT/'metadata/input_file_manifest.csv')\nassert all(v.sha(ROOT/r['snapshot_path']) == r['sha256'] for r in manifest)\nprint('国家  占比  原得分  原名次')\nfor c in sample:\n    print(f\"{c['market']}: {c['narrow_share']:.2%}, {c['original_score']:.6f}, {c['original_rank']}\")\nprint('已匹配国家:',len(sample),'；海关覆盖:',len(countries),'；源快照:',len(manifest))")
    md('### 2. 独立复现原模型\n\n同时核对向量实现和不依赖该计算函数的标量实现。')
    code("baseline = v.topsis(x,w)\nassert np.array_equal(baseline[1], ranks)\nassert np.max(np.abs(baseline[0]-orig)) < 1e-12\nassert np.max(np.abs(v.independent_baseline(x,w)-orig)) < 1e-12\nprint('原模型最大得分误差:',float(np.max(np.abs(baseline[0]-orig))))\nprint('独立方法单元测试:',len(v.unit_tests()),'项通过')")
    md('## Results\n\n### 3. 相关检验、置换与重抽样\n\nPearson/Spearman/Kendall 分别检验线性、单调及国家对次序关联。多重检验校正后，不能把单项 p<0.05 写成确定结论。')
    code("correlations, leave_one, _ = v.stats_tests(s,orig,cfg['random_seed'],cfg['permutation_draws'],cfg['bootstrap_draws'])\nfor row in correlations:\n    print(f\"{row['method']}: coef={row['coefficient']:.6f}, permutation p={row['p_value_permutation_two_sided']:.6f}, Holm p={row['p_value_holm_3_tests']:.6f}, country-resampling interval=[{row['bootstrap_percentile_95_low']:.4f},{row['bootstrap_percentile_95_high']:.4f}]\")\nprint('剔除文莱的 Pearson:',next(r['coefficient'] for r in leave_one if r['method']=='pearson' and sample[r['excluded_index']]['iso3']=='BRN'))")
    md('### 4. 占比与原得分图\n\n图源：海关逐国人民币金额及冻结原模型得分，不做跨年度金额合并。')
    code("def show_image(path):\n    if '__record_image' in globals():\n        __record_image(path)\n    else:\n        try:\n            from IPython.display import display, Image\n            display(Image(filename=str(path)))\n        except ImportError:\n            print('图像文件:',path)\nplot_details = v.make_scenarios(cfg,sample,x,s,w,orig,ranks)[1]\nv.draw_figures(sample,s,orig,plot_details)\nshow_image(ROOT/'output/figures/share_vs_score.png')")
    md('### 5. 占比情景下的名次变化\n\n同时看总体秩相关及前五成员替换。原名次越小越好；括号中的正数表示名次改善。')
    code("scenarios, detail, matrices, weights = v.make_scenarios(cfg,sample,x,s,w,orig,ranks)\nfor row in scenarios:\n    print(f\"{row['scenario']}: Spearman={row['spearman_ranks']:.4f}, Kendall={row['kendall_tau_b_ranks']:.4f}, max shift={row['max_absolute_rank_change']}, Top5 overlap={row['top5_overlap_count']}/5, {row['top5_order']}\")\nshow_image(ROOT/'output/figures/scenario_rank_comparison.png')")
    md('### 6. 同期宽/窄出口金额排名的直接比较\n\n这个比较无需把占比迁移到进口需求，但它只检验中国现有出口规模排序，不是市场吸引力排序。')
    code("observed = v.readcsv(ROOT/'output/observed_export_rank_comparison.csv')\nall14 = [r for r in observed if r['scope']=='all_RCEP14']\na = np.array([int(r['broad_export_rank']) for r in all14])\nb = np.array([int(r['narrow_export_rank']) for r in all14])\nprint('14 国同期出口金额排名关联:',v.association(a,b))\nfor row in sorted(all14,key=lambda r:int(r['narrow_export_rank']))[:5]:\n    print(row['market'],row['broad_export_rank'],'→',row['narrow_export_rank'])")
    md('## Takeaways\n\n现有五国可保留为研究范围，不能将其写成已确认的窄编码官方排名。日本是强结构偏好下的边界敏感市场，泰国可作备选。越南占比较高但缺原模型主指标，不能把缺名次当作低吸引力。完整公式、敏感网格、来源与访问日期缺口见 `methodology.md` 和 `metadata/`。')
    namespace={};execution=0;records=[]
    os.chdir(ROOT)
    for i,cell in enumerate(cells):
        cell['id']=f"{cell['cell_type']}-{i:02d}"
        if cell['cell_type']!='code':continue
        execution+=1;outs=[]
        def record_image(path):
            outs.append({'output_type':'display_data','metadata':{},'data':{'image/png':base64.b64encode(Path(path).read_bytes()).decode('ascii'),'text/plain':Path(path).name}})
        namespace['__record_image']=record_image
        stream=io.StringIO();start=time.perf_counter()
        with contextlib.redirect_stdout(stream):exec(compile(cell['source'],f'verification.ipynb:cell-{i}','exec'),namespace)
        text=stream.getvalue()
        if text:outs.insert(0,{'output_type':'stream','name':'stdout','text':text})
        cell['outputs']=outs;cell['execution_count']=execution
        records.append({'cell_id':cell['id'],'execution_count':execution,'status':'passed','elapsed_seconds':round(time.perf_counter()-start,4),'output_count':len(outs)})
    nb={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
         'language_info':{'name':'python','version':sys.version.split()[0]},
         'execution_engine':'Sequential Python executor; not Jupyter/nbclient','source_mode':'offline frozen evidence'},'cells':cells}
    v.writejson('verification.ipynb',nb)
    # Validate the notebook's essential v4 cell / output structure without nbformat.
    saved=json.loads((ROOT/'verification.ipynb').read_text(encoding='utf-8'))
    assert saved['nbformat']==4 and len({c['id'] for c in saved['cells']})==len(saved['cells'])
    executed=[c for c in saved['cells'] if c['cell_type']=='code']
    assert [c['execution_count'] for c in executed]==list(range(1,len(executed)+1))
    assert all(c['outputs'] and all(o['output_type']!='error' for o in c['outputs']) for c in executed)
    assert sum('image/png' in o.get('data',{}) for c in executed for o in c['outputs'])==2
    v.writejson('logs/notebook_execution.json',{'all_code_cells_executed':True,'engine':'Sequential Python executor, fresh namespace, top-to-bottom',
                 'jupyter_kernel_execution':'not available: ipykernel, nbclient and nbformat not installed',
                 'notebook_viewer_inspection':'not performed; both saved PNGs inspected separately and essential JSON structure checked',
                 'saved_png_outputs':2,'cells':records,'structural_validation':'essential nbformat-4 fields and saved outputs checked; formal nbformat library validation unavailable'})
    print('Saved notebook:',len(executed),'executed code cells; 2 embedded PNG outputs.')

if __name__=='__main__':
    facts()
    notebook()
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.relative_to(ROOT).as_posix() not in ['run/checksums.csv','run/checksums.sha256']:
            files.append({'relative_path':p.relative_to(ROOT).as_posix(),'sha256':v.sha(p),'file_size_bytes':p.stat().st_size})
    v.writecsv('run/checksums.csv',files)
    (ROOT/'run/checksums.sha256').write_text(''.join(r['sha256']+'  '+r['relative_path']+'\n' for r in files),encoding='utf-8')
