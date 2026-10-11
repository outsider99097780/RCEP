"""Independent integrity and numerical reconciliation for the saved package."""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path
import numpy as np

sys.dont_write_bytecode=True
import verify_model as v

def validate(check_originals=True):
    root=Path(__file__).resolve().parents[1]
    cfg,countries,sample,x,s,w,orig,ranks,_,_=v.load_data()
    manifest=v.readcsv(root/'metadata/input_file_manifest.csv')
    for row in manifest:
        assert v.sha(root/row['snapshot_path'])==row['sha256']
        if check_originals:
            assert v.sha(row['original_absolute_path'])==row['sha256'],row['original_absolute_path']
    correlations=v.readcsv(root/'output/association_tests.csv')
    observed=v.association(s,orig)
    perm=np.load(root/'intermediate/permutation_statistics.npz')
    for row in correlations:
        key=row['method'];n=int(row['permutation_draws'])
        assert abs(float(row['coefficient'])-observed[key])<1e-14
        extreme=sum(np.abs(perm[key])>=abs(observed[key])-1e-12)
        assert int(extreme)==int(row['permutation_extreme_count'])
        assert abs((int(extreme)+1)/(n+1)-float(row['p_value_permutation_two_sided']))<1e-15
    details=v.readcsv(root/'output/scenario_country_rankings.csv')
    summaries=v.readcsv(root/'output/scenario_summary.csv')
    for summary in summaries:
        rows=[r for r in details if r['scenario']==summary['scenario']]
        assert len(rows)==11 and {int(r['scenario_rank']) for r in rows}==set(range(1,12))
        # Independent rank formula, discordance count and top-five set comparison.
        rs=np.array([int(r['scenario_rank']) for r in rows])
        ro=np.array([int(r['original_rank']) for r in rows])
        d=rs-ro
        rho=1-6*int(np.square(d).sum())/(11*(11**2-1))
        inversions=sum((int(a['scenario_rank'])-int(b['scenario_rank']))*(int(a['original_rank'])-int(b['original_rank']))<0
                       for i,a in enumerate(rows) for b in rows[i+1:])
        tau=1-2*inversions/55
        assert abs(rho-float(summary['spearman_ranks']))<1e-14
        assert abs(tau-float(summary['kendall_tau_b_ranks']))<1e-14
        original5={r['iso3'] for r in rows if int(r['original_rank'])<=5}
        new5={r['iso3'] for r in rows if int(r['scenario_rank'])<=5}
        assert len(original5&new5)==int(summary['top5_overlap_count'])
        assert int(np.abs(d).max())==int(summary['max_absolute_rank_change'])
        assert summary['top5_order']==';'.join(r['iso3'] for r in sorted(rows,key=lambda r:int(r['scenario_rank']))[:5])
    grid=v.readcsv(root/'output/stress_parameter_grid.csv')
    assert len(grid)==903
    for family in ['scale_untapped_only','scale_size_and_untapped']:
        assert all(float(r['spearman_ranks'])==1 for r in grid if r['scenario_family']==family)
    registry=v.readcsv(root/'metadata/fact_registry.csv')
    ids={r['fact_id'] for r in registry}
    assert len(ids)==len(registry)
    text=(root/'output/验证结果与建议.md').read_text(encoding='utf-8')
    referenced=set(re.findall(r'\b(?:V-\d{3}|S-[A-Z]{3})\b',text))
    assert referenced<=ids,referenced-ids
    for row in registry:
        p=root/row['output_locator'].split('#')[0]
        assert p.is_file() and v.sha(p)==row['output_sha256'],row['fact_id']
    for row in v.readcsv(root/'metadata/official_itc_source_ledger.csv'):
        assert row['source_id'] and row['url'] and row['accessed_at']
        assert v.sha(root/row['snapshot_path'])==row['sha256']
    nb=json.loads((root/'verification.ipynb').read_text(encoding='utf-8'))
    codes=[c for c in nb['cells'] if c['cell_type']=='code']
    assert [c['execution_count'] for c in codes]==list(range(1,len(codes)+1))
    for cell in codes:
        assert cell['outputs'] and all(o['output_type']!='error' for o in cell['outputs'])
    checksum_rows=v.readcsv(root/'run/checksums.csv')
    for row in checksum_rows:
        assert v.sha(root/row['relative_path'])==row['sha256'],row['relative_path']
    result={'all_checks_passed':True,'original_files_checked_unchanged':len(manifest) if check_originals else None,
            'correlations_independently_reconciled':len(correlations),
            'scenario_rankings_independently_checked':len(summaries),'stress_grid_rows':len(grid),
            'fact_registry_rows':len(registry),'notebook_code_cells_executed':len(codes),
            'package_checksums_verified':len(checksum_rows),
            'jupyter_kernel_execution':'not performed; ordered Python executor used',
            'visual_review':'both PNGs manually inspected; notebooks not opened in Jupyter viewer'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    result=validate('--snapshots-only' not in sys.argv)
    if '--save' in sys.argv:
        v.writejson('logs/package_validation.json',result)
