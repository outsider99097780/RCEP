# HS85081110 产品结构与 ITC 国家排名验证

本目录独立检验：2026 年 1—8 月中国对各国出口中，HS85081110 占 HS850811 的金额比例，是否会改变现有 ITC 市场吸引力排序。原始海关文件、ITC-data、ITC-analysis-result 和报告正文均不修改。

先读 [验证结果与建议](output/验证结果与建议.md)，再读 [方法说明](methodology.md)。精确数值和来源分别保存在结果表与来源账本中。

## 文件结构

```text
ITC-model-verification/
├─ README.md
├─ methodology.md                     方法、假设和检验边界
├─ config.json                        检验前固定的参数和判读规则
├─ raw/
│  ├─ customs/                        两份海关原文件和已有占比表的逐字节快照
│  ├─ itc-model/                      原模型输入、权重、得分、来源链、方法和运行记录
│  ├─ itc-official/                   11 国对应的 22 份 ITC 官方原始响应快照
│  └─ method/                         原 ITC 分析技能，仅作方法参考
├─ cleaned/customs_country_aggregates.csv
├─ input/matched_model_inputs.csv      精确金额占比与 11 国模型输入的匹配表
├─ intermediate/
│  ├─ scenario_matrices.csv           变换、标准化、权重、理想解和距离
│  ├─ scenario_weights.csv
│  └─ *permutation_statistics.npz     可审计的随机置换统计量
├─ output/
│  ├─ 验证结果与建议.md
│  ├─ association_tests.csv           占比与原得分的三种相关检验
│  ├─ share_vs_numeric_rank.csv        占比与原名次的三种相关检验
│  ├─ multiple_testing_six_tests.csv   六项检验的 Holm 校正
│  ├─ leave_one_country_out.csv        留一国稳定性诊断
│  ├─ scenario_summary.csv            12 个场景的总体比较
│  ├─ scenario_country_rankings.csv    各国逐场景得分、名次和变化
│  ├─ stress_parameter_grid.csv        903 个参数网格结果
│  ├─ stress_first_crossings.csv       首次触发前五变化等事件的位置
│  ├─ observed_export_rank_*.csv       同期海关宽/窄编码出口金额排名的直接比较
│  └─ figures/                        两张图及数据说明
├─ metadata/                          来源、文件哈希、国家对照、逐行追溯及事实索引
├─ logs/                              清洗记录、数据检查和独立验算
├─ code/verify_model.py                完整离线分析入口
├─ code/build_notebook.py              顺序执行与保存 notebook 的入口
├─ verification.ipynb                 保存结果和图像的可重复分析笔记
└─ run/                               运行环境、参数、时间及全包校验清单
```

## 重跑

在本目录依次运行 `python code/verify_model.py` 和 `python code/build_notebook.py`。第一步只读取本目录冻结快照，重新生成派生结果；第二步更新事实索引、顺序执行笔记代码单元并刷新全包校验清单。需要 Python 3.12、NumPy、Pillow；图中文字采用 Windows 微软雅黑。

需要从项目重新取快照时，才使用 `python code/verify_model.py --repo <RCEP项目根目录>`。已存在的快照只校验、不覆盖；若源文件变更导致哈希不同，应新建验证批次，不能混用本批结果。

本环境没有 SciPy、Matplotlib 或 Jupyter 内核。相关系数、并列秩和置换检验用 NumPy/标准库实现并执行了独立测试。笔记通过顺序 Python 执行器运行，不声称已经通过 Jupyter 内核执行或交互式查看；普通结果表、源代码和 PNG 可直接使用。详见 `logs/notebook_execution.json`。

## 引用与来源

海关来源主体：中华人民共和国海关总署，在线查询平台 <http://stats.customs.gov.cn/>。原始文件由用户提供，实际下载日期、筛选页和完整查询 URL 未随文件保存，账本标为未记录，不用文件修改时间冒充访问日期。2026 年 1—8 月期间依据用户说明及已有占比表；源 CSV 没有日期列。

ITC 数据沿用原获取日期 2026-10-03，不把本次本地读取日期写成重新访问网站的日期。官方查询、原始文件和哈希见 `metadata/official_itc_source_ledger.csv`；原模型字段级追溯见 `raw/itc-model/model/input/input_lineage.csv`。本次计算事实见 `metadata/fact_registry.csv`，引用时保留验证批次编号和对应输出行键。

`raw/` 中的文件只作冻结证据。所有清洗、占比、情景金额和新分数都在其外部保存。情景得分不称为官方 EPI 或正式窄编码市场排名。
