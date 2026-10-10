# 原方法重算说明

本轮读取更新后的 `../ITC-data`，使用 HS6 `850811`、2020—2025 年贸易数据及 2026-10-03 保存的 EPM/Market Access Map 快照。未联网、未修改原始数据，未加入公司适配指标。

## 方法优先级

用户要求保留原方法，故基准以原 `recalculate_model.ps1` 五指标正式计算及 `build_report_charts.py` 的随机权重实现为准。旧 README 所述“等权主排名”及旧 `market_ranking.csv` 的简单平均筛选与正式 TOPSIS 代码不一致，本轮统一为战略权重 TOPSIS；两个排名文件指向同一套新结果，不并存第二套主排名。没有改用技能的默认 hybrid，也没有伪造 AHP 判断矩阵。

## 输入与样本

完整保留当前横向输入表的数值；将 `MACMAP rows linked by raw_source_file` 占位文本解析成真实来源 ID。逐国复核原始 Trade Map `aggregateRecords`，不重复累加不同 HS 版本子记录；以进口国自报世界进口额衡量需求。中国直接出口额单列在 `cleaned/trade_annual.csv`，不与进口国 CIF 口径混为同一序列。输入 CAGR 与中国份额保持既有 4 位小数，不通过额外精度改变主排名。

14 个市场中 11 个有完整主指标；老挝、缅甸、越南缺少 2025 年进口数据，不插补、不补零。文莱与新加坡的未实现潜力是有依据的零，保留在样本中。

## 五指标与公式

顺序为市场规模、市场增长、中国供应份额、未实现潜力金额、未实现潜力比例，战略权重依次为 0.30、0.10、0.10、0.30、0.20，全部正向。金额分别在千美元（进口额）与美元（EPM）原有单位上做 `ln(1+x)`，不能先换单位再声称同一模型。增长为 `((M2025/M2020)^(1/5)-1)*100`；潜力比例为 `max(EPI-baseline,0)/EPI`。

在共同完整样本中做 Min-Max：`z=(x-min)/(max-min)`，`v=z*w`；理想解逐列取最大/最小，`D+=sqrt(sum((v-v+)^2))`、`D-=sqrt(sum((v-v-)^2))`，`C=D-/(D++D-)`。按未舍入得分降序排名，展示 6 位小数。

熵权由 `p=z/sum(z)`、`e=-sum(p*ln(p))/ln(n)`、`w=(1-e)/sum(1-e)` 得到；约定 `0*ln(0)=0`。等权为每项 0.2。无机械缩尾；小样本极端值通过敏感性呈现。

关税最低返回值仅作审计字段，不是具体扫地机器人型号的实际适用税率，不进入评分；完整样本最低返回值均为零，但越南为 5%，已保留且未进入完整样本。NTM 只作审计，空响应不作零，条目数不等于合规成本；供应国排名并非全部第一名，也不据此改动原五指标。

## 稳健性

保留战略/等权/熵权方案；蒙特卡洛严格沿用 `np.random.default_rng(850980)`、`Dirichlet(strategy_weight*40)`、5000 次。种子数字是历史随机参数，不是本轮 HS。保存全部抽样权重和排名。补充单项权重 ±20% 后归一化、留一指标、金额不用 log1p、2022—2025 三年 CAGR，仅作为诊断，不取代主结果。无有效 AHP，alpha 场景不适用；机器可读 EPM 不需粗显示舍入场景；无同口径镜像全球需求，相关场景列为不可用。

## 审计与重跑

从本目录运行 `python rebuild_itc_model.py --raw ../ITC-data --output .`，需要 Python 与 NumPy。不会删除文件；全量替换前应按 README 清单移除旧结果。`model/input/input_lineage.csv` 保存字段级来源与计算，`logs/validation_log.csv` 保存数值复核，`run/run_manifest.json` 记录版本及源文件哈希。原计算脚本 `recalculate_model.ps1` 仅为公式一致性核验入口，完整重建应使用 Python 入口。

`source_ledger*.csv` 的 `raw_file` 均相对 `../ITC-data`；`metadata/source_ledger.csv` 另提供可解析的相对路径。原始账本复用部分 Market Access Map 编号，新结果按“国家＋响应类型＋税则线”构造唯一编号，`original_source_id` 和 `metadata/source_id_aliases.csv` 保留原始对应关系，不修改原账本。访问时间沿用原获取时间，重算时间单独记录，不把重算写成重新下载。原始 Trade Map 响应未声明确切 HS 修订年份，事实登记为 `source_verified_scope_limited`，不虚标 `report_ready`。EPM 2030 地平线仅见已存界面说明，原记录无该字段，明确标注证据状态。
