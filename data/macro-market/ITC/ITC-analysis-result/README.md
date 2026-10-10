# 更新后的 ITC 市场分析结果

本目录仅包含基于当前 HS6 **850811** 数据的重算结果；旧分析数据已经全量替换，不保留归档副本。数据来源仍在只读的 `../ITC-data`。

主方法保留五指标战略权重 TOPSIS（30%/10%/10%/30%/20%），保留等权、熵权及 5,000 组随机权重检验。主结果前三：韩国（0.896282）、澳大利亚（0.846239）、马来西亚（0.793578）。14 个候选市场中 11 个参与排名，另外 3 个保留缺口记录。

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

旧文档的等权初筛叙述与正式代码不一致，现统一以原五指标 TOPSIS 计算为准。随机种子 850980 原样保留，数字只是随机参数。旧图表脚本硬编码旧研究路径且会写入报告图表目录，本次移除；未生成或替换报告图表。没有重下数据，来源访问时间为 2026-10-03，运行时间另记。

Trade Map 2020—2025（千美元）；EPM 当前快照（美元）；税率及 NTM 各自保存参考年份。关税、NTM 不参与五指标评分。HS850811 包含非机器人吸尘器；本结果不是石头科技经营判断。详情见 `methodology.md` 与 `limitations.md`。

审计笔记本的 3 个计算单元已顺序执行并通过；本机未安装 Jupyter 内核组件，使用普通 Python 执行。浏览器安全策略不允许打开本地 HTML，未做界面预览；此限制不影响数值及来源核验。
