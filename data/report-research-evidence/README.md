# 石头科技年报与券商研报：分类证据库

本库按项目 instruction.md 的七类要求新增，未改动原有 data 及 sources。资料读取日期：2026-10-09。它是可引用的证据整理，不是报告正文，也不重新建模。

## 从哪里开始

- `evidence/02_target_markets/`：日本、韩国、澳大利亚，分别使用 TARGET_JAPAN / TARGET_KOREA / TARGET_AUSTRALIA。
- `evidence/03_mature_overseas_cases/`：美国、加拿大及欧洲各国的成熟海外经验，不进入目标市场TOPSIS排名。
- 其他五类分别为行业基础、产品技术、竞争、国际化能力、约束与失败经验；每类再按国家分支。
- `indexes/by-country.json`：按国家找到全部信息类别。
- `country-notes/`：便于人工浏览的逐国Markdown证据清单。
- `indexes/target-market-coverage.json`：三国所需字段的覆盖及缺口；未找到不是0。
- `evidence/all-records.json` / `.jsonl`：完整可调用记录；JSONL便于逐条读取。分类文件是同一 record_id 的视图，合并时按 record_id 去重。

## 地理范围

能明确归属国家的记录按国家存储。global、europe-regional、north-america-regional、overseas-regional 等保留真正的全球/区域口径，不将北美数值强行赋给美国或加拿大。中国台湾、香港标为地区。越南、马来西亚的产能证据说明供应链，不代表当地市场需求。

## 记录与引用

每条含 record_id、国家/研究角色、类别、时期、品牌、渠道、statement_zh、claim_type、report_use、metrics、notes 和 citation。

citation 含提供主体、报告标题、封面日期（年报另列报告期）、PDF物理页和印刷页、图表/文字定位、原文件名路径、SHA-256、读取日期、上游提供者、原文锚点与摘录。`sources/source-ledger.json` 登记全部17份PDF；原文页保存在 `sources/page-text/`，视觉核对的关键图表页在 `sources/page-renders/`。

本轮使用用户提供的本地文件，没有联网。下载URL及上游数据库深链接未核实的字段明确为null，绝不虚构网站链接。引用这些记录时应引用“年报/券商研报转引IDC、欧睿等”，不能假装直接查询过IDC或欧睿。年报发布日期未核验时也为null，报告年度不等于发布年度。

引用时可直接读取 `citations/record-citations.json` 的 citation_zh。PDF物理页采用1起始；2024年报的印刷页较物理页少1，已分开标识。

## 使用边界

- company_disclosure：公司披露，并非全部经审计的经营事实；secondary_statistic：年报或研报二次引述。
- broker_observation：券商观察或采样；broker_interpretation：券商解释；broker_estimate / broker_forecast：估计/预测，不能写成已实现事实。
- risk_disclosure：风险提示不等于风险已经发生。
- blocked_pending_resolution：内部冲突，禁止直接用于数值分析。
- superseded_body_value_audit_only / conflict_audit_only：不采用的原文值/差异，只供审计，不当作可报告数值。
- official_verification_required：高影响监管断言仅为待核验线索，不作现行法规结论。
- 全市场份额、Amazon份额、门店展位份额、公司发货份额不能混用。未说明销量/销额分母的份额不自行补定义。
- 渗透率原文未完整披露分母，保留该缺口；不要与“扫地机销量占吸尘器销量”拼接。
- 黑五/Prime Day促销战报不能当全年市场增速。全品类数据不得当作扫地机单品类。
- 价格为历史门店样本，不是目标三国现价；不把list price擅称官方MSRP。北欧/波兰欧元价格沿用研报列示，不重新换汇。
- metrics.value_raw用字符串保留精度、单位和取整；“/”另存 missing_marker_raw，数值为null。
- 不抽财务报表和券商盈利预测/估值表；零售销量、GMV、价格与经营渠道信息属于本轮市场和策略证据。

## 已识别的重点核验事项

1. 依用户图表优先规则采用：马来西亚2024销售额图42的0.20亿美元，正文0.32只保留审计。
2. 德国2025Q4科沃斯份额采用图33标题19%，不采用正文18%；中国石头图19曲线明确标注35%，优先于同图标题37%。美国公司线上线下80/20顺序无同口径图可裁决，仍隔离。
3. 2026年9月研报欧洲份额正文与图注对上游来源（卖家精灵/魔镜）归因不同。
4. 波兰Saros 10/10R型号正文与表格不同，不合并。
5. 2026年9月研报FCC机器人管制叙述未提供官方原文；已单独标记，不作为确定法规、禁售或合规要求。
6. Best Buy 2026年初限制与后续Q2重新入驻按时间保留，不覆盖历史。

日本完整市场规模、三国全品牌份额、全年销量、零售结构及本地完整价格带仍有缺口，见coverage文件。本库不从曲线像素猜测没有明确标注的历史点，也不以公司行业代表性代替企业对每个市场的适配证据。

## 审计与重复使用

audit/extraction-log.json记录指令哈希、范围和处理规则；baseline-existing-file-hashes.json是新增前所有既有data文件及本轮sources文件的指纹。交付前核验这些文件均未变化。新增目录不覆盖现有文件。

## 2026-10-10：扩展至五个目标市场

02_target_markets新增malaysia（TARGET_MALAYSIA）与new-zealand（TARGET_NEW_ZEALAND）。马来西亚归集已有市场/竞争/供应链记录，新增两条研报线索；新西兰经17份PDF、1283页可提取全文检索仍未发现专门记录，空数组与缺口说明明确保留。coverage与by-country索引同步扩展。

原三国和其他国家的事实对象不变，所有旧record_id和源PDF均保留。马来西亚规模继续按图42优先；新增16%五年CAGR因区间与同段口径问题隔离，不用于数值分析。图43主引用页更正为PDF29页，旧28页定位保留审计。两国零售价格采集不混入本年报/研报证据库。
