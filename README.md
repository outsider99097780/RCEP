# 石头科技扫地机器人 RCEP 国际市场开拓项目

这份 README 写给负责路演和答辩的队友。它不替代报告正文，而是说明项目中的数据从哪里来、模型怎样计算、RCEP规则怎样进入市场判断，以及答辩时应当引用哪一版结果。

## 先记住结论

研究对象是石头科技扫地机器人。项目按用户确认的中国海关申报码 `85098090.00` 开展，跨国比较使用 ITC 六位产品组 `HS 850980`。候选市场为中国以外的14个RCEP成员：东盟十国、澳大利亚、新西兰、日本和韩国。

最终采用五指标战略权重 TOPSIS。进入模型的11个市场中，前三名是：

| 排名 | 市场 | TOPSIS得分 | 为什么入选 |
|---:|---|---:|---|
| 1 | 韩国 | 0.733 | 进口规模较大、五年增长为正，未实现潜力高 |
| 2 | 日本 | 0.719 | 候选市场中进口规模和未实现潜力最大 |
| 3 | 澳大利亚 | 0.661 | 规模、增长和中国供应份额较均衡，适合验证英语市场复制 |

老挝、缅甸和越南仍有 EPI 数据，但2025年目的国直接进口数据不完整，因此没有补零，也没有进入 TOPSIS 排名。

这套结果回答的是“哪些国家值得优先验证”，不是 Roborock 的品牌销量预测。ITC 的 `HS 850980` 也不是扫地机器人专属统计项。

## 从哪里开始看

- 最终报告：[main/main.pdf](main/main.pdf)
- LaTeX 正文：[main/main.tex](main/main.tex)
- 答辩 PPT：[main/石头科技RCEP市场开拓答辩.pptx](main/石头科技RCEP市场开拓答辩.pptx)
- PPT 源稿：[main/石头科技RCEP市场开拓答辩.md](main/石头科技RCEP市场开拓答辩.md)
- 七分钟讲稿：[main/石头科技RCEP市场开拓答辩讲稿.md](main/石头科技RCEP市场开拓答辩讲稿.md)
- 最终模型结果：[sources/20260905-CHN-Roborock-HS85098090-rcep-v01/market_ranking_recalculated.csv](sources/20260905-CHN-Roborock-HS85098090-rcep-v01/market_ranking_recalculated.csv)
- ITC 原始数据说明：[raw-material/ITC-data/README.md](raw-material/ITC-data/README.md)
- RCEP 分析指南：[RCEP-rules/05-analysis/RCEP-trade-analysis-guide-HS850980.md](RCEP-rules/05-analysis/RCEP-trade-analysis-guide-HS850980.md)
- 产品矩阵：[raw-material/other-search/roborock-product-matrix/roborock_product_matrix.md](raw-material/other-search/roborock-product-matrix/roborock_product_matrix.md)
- 竞赛硬性要求：[output-restrictions/附件4.2026年RCEP国际市场开拓策划赛道实施细则.md](output-restrictions/附件4.2026年RCEP国际市场开拓策划赛道实施细则.md)

## 项目结构

```text
RCEP/
├─ README.md                         # 本文件：给答辩队友的总说明
├─ main/                             # 最终报告、PPT、讲稿与图表
│  ├─ main.tex / main.pdf
│  ├─ 石头科技RCEP市场开拓答辩.md / .pptx
│  ├─ 石头科技RCEP市场开拓答辩讲稿.md
│  ├─ build-ppt.ps1
│  └─ graphics/                     # ITC模型和竞争结构图
├─ raw-material/                     # 外部资料与ITC数据
│  ├─ ITC-data/                     # ITC三套工具的原始响应、派生表和来源账本
│  ├─ company-report/               # 石头科技及对照企业年度报告
│  ├─ other-search/                 # 联合搜索结果与官网产品矩阵
│  ├─ roborock_products_hs.json     # HS查询试验结果
│  └─ 开源证券·.md及研报资料         # 行业和公司背景材料
├─ sources/
│  └─ 20260905-...-rcep-v01/       # 模型输入、脚本、中间结果、排名与敏感性分析
├─ RCEP-rules/                       # RCEP官方文本、关税表、原产地规则与提取表
│  ├─ 01-agreement/                 # 第2、3、4、6、7章等中英文原文
│  ├─ 02-origin/                    # PSR、证明格式、实施指南
│  ├─ 03-tariff-schedules/          # 14个目的国关税承诺表
│  └─ 05-analysis/                  # HS850980行级提取与分析指南
├─ output-restrictions/              # 竞赛结构、字数、文风约束
├─ workflow-skills/                  # ITC分析与HS查询工作流
├─ basic-skills/                     # 联合搜索、市场规模、竞争分析等辅助能力
├─ package.json                      # Marp版本与PPT编译命令
└─ .vscode/                          # VS Code中的Marp编译和PPT预览配置
```

`.uv-cache`、`.uv-python`、`.npm-cache`、`node_modules` 和 `.tools` 是运行环境或依赖缓存，不是研究证据，也不用提交。

## ITC体系在本项目中做什么

ITC 是联合国国际贸易中心。本项目使用三套 Market Analysis Tools，它们回答的问题不同。

| ITC工具 | 本项目读取的数据 | 回答的问题 | 不能直接说明什么 |
|---|---|---|---|
| Trade Map | 2020—2025年进口额、数量、增长率、供应国份额和排名 | 市场有多大、增长如何、中国供给处在什么位置 | 不能识别 Roborock 品牌、型号和零售销量 |
| Export Potential Map | EPI、基准出口额、未实现潜力 | 在供给、需求和双边贸易便利度共同作用下，还有多少拓展空间 | 不是销量承诺，也不是市场容量上限 |
| Market Access Map | 目的国税则线、实际适用税率、NTM记录 | 进入市场时面临什么税率和制度要求 | NTM条目数不等于认证成本；最低税率也不一定适用于每个型号 |

### Trade Map 的两个贸易口径

项目同时保存了中国报告的出口数据和目的国报告的进口数据。

- 中国出口通常按 FOB 计价，用于观察中国的目的地结构。
- 目的国进口通常按 CIF 计价，用于计算目标市场规模和中国供应份额。
- 两者还会受到运输时点、转口和统计制度影响，因此数值不要求完全相等。

市场模型使用目的国进口口径。以2025年为例，中国报告的对日、韩、澳出口额，与三国报告的自中国进口额并不相同；正文没有把两套数据相互覆盖。

### EPI 和未实现潜力

ITC 的出口潜力指标为：

$$
EPI_{ijk}=Supply_{ik}\times Ease_{ij}\times Demand_{ijk}
$$

其中，$i$ 是出口国，$j$ 是目标市场，$k$ 是产品。三个部分分别吸收出口国供给能力、双边贸易便利度和目标市场需求。

未实现潜力按每个“中国—目标国—产品”组合计算：

$$
Untapped_{ijk}=\max(EPI_{ijk}-ActualExports_{ijk},0)
$$

本项目的原始 EPM 文件同时保存 `epi_potential_usd`、`baseline_exports_usd` 和 `untapped_potential_usd`。计算时先逐国取非负差额，再进行比较；不能让一个已超额实现的市场抵消另一个市场的未实现空间。

EPI 的作用是补足历史贸易数据的局限。日本过去五年进口增长为负，但进口池和未实现潜力仍然很大；如果只看 CAGR，日本会被过早排除。

### ITC数据的保存方式

[raw-material/ITC-data](raw-material/ITC-data) 是官方数据证据区，按国家和工具组织：

```text
ITC-data/{country}/
├─ trade-map/                 # 原始JSON：贸易额与数量
├─ market-access-map/         # 原始JSON：税则线、税率和NTM
├─ export-potential-map/      # 原始JSON：官方EPI记录
└─ derived/                   # 从原始文件抽取或计算的CSV
```

另外还有四组横向文件：

| 数据集群 | 内容 | 使用方式 |
|---|---|---|
| `_shared/` | 中国对世界贸易、ITC国家代码、EPM全市场响应和产品参考表 | 处理跨国共用字段 |
| `_modeling-output/` | 14国拼接后的模型输入 | 是派生数据，不是原始响应 |
| `source-ledger*.csv` | 来源ID、查询URL、参数、访问时间、原始文件和SHA-256 | 从结论反查来源 |
| `file-inventory-sha256.csv` | 文件大小与哈希 | 检查原始文件是否被改动 |

数据覆盖见 [raw-material/ITC-data/data-availability.csv](raw-material/ITC-data/data-availability.csv)：14国均有官方 EPI；11国有完整的2020—2025目的国进口数据；老挝、缅甸、越南缺少2025年目的国直接进口值。

## 每个数据集群的来源和作用

### 1. ITC贸易、潜力和准入数据

位置：[raw-material/ITC-data](raw-material/ITC-data)

来源是 ITC Trade Map、Export Potential Map 和 Market Access Map，访问日期集中在2026年9月5日。原始 JSON 只保存，不在原文件上清洗；派生指标写入各国 `derived/` 和 `_modeling-output/`。

这是市场筛选模型的主要证据。报告中的进口额、CAGR、中国份额、EPI、未实现潜力和适用税率都应从这一集群引用。

### 2. RCEP法律和制度数据

位置：[RCEP-rules](RCEP-rules)

主要来源包括商务部自由贸易区服务网、RCEP秘书处、海关总署及RCEP附件一关税承诺表。目录保留原始 PDF、文件哈希、PDF质量检查、机器提取行和分析指南。

该集群解释“入选市场在什么规则下可以进入”：关税是否减让、产品如何取得原产资格、是否可以区域累积、需要什么原产地证明，以及通关和技术法规仍有哪些要求。

### 3. 公司报告与行业背景

位置：[raw-material/company-report](raw-material/company-report)

包括石头科技2022—2025年年度报告、2026年一季报，以及科沃斯2025年年度报告。石头科技报告用于说明产品能力、海外业务、全价格段布局、研发和销售季节性；科沃斯报告用于理解行业竞争，不进入 TOPSIS 分数。

证券研究资料位于 `raw-material` 根目录。它们只承担行业和公司背景说明，权威级别低于公司公告、ITC和RCEP原文。

### 4. 官网产品和联合搜索资料

位置：[raw-material/other-search](raw-material/other-search)

`rcep_roborock_search_*.json` 保存 union-search 原始响应和搜索摘要；摘要只能作为发现线索。具体型号、功能和图片已经回到石头科技官网核验，整理在 [roborock-product-matrix](raw-material/other-search/roborock-product-matrix)。该矩阵包含20个型号或系列、20张官方产品图、产品页面、图片URL和访问日期。

这部分支持报告和PPT的产品介绍，不进入国家市场排名。

### 5. HS编码查询资料

位置：[raw-material/roborock_products_hs.json](raw-material/roborock_products_hs.json)

该文件来自本地 `mcp-hs-code-query` 的备用查询源，记录了扫地机器人、洗地机和手持产品的试查结果。模型只采用用户确认的扫地机器人输入 `85098090.00`；文件中其他品类的自动匹配结果没有进入报告。

这里最容易被问到的是产品边界。中国10位码 `85098090.00` 在 ITC 中只能按六位 `850980` 比较，而该六位组的官方品名是“其他未列名机电家用器具”，并非 Roborock 或扫地机器人专属类别。答辩时应说“HS850980产品组的市场环境”，不要说“Roborock品牌市场规模”。详细说明见 [HS-CORRESPONDENCE.md](raw-material/ITC-data/HS-CORRESPONDENCE.md)。

### 6. 模型工作底稿

位置：[sources/20260905-CHN-Roborock-HS85098090-rcep-v01](sources/20260905-CHN-Roborock-HS85098090-rcep-v01)

该目录承接 ITC 派生输入，保存变换、标准化、权重、TOPSIS排序和敏感性分析。每一行模型输入都保留 `source_ids`，可连接回 ITC 来源账本。

### 7. 最终交付物

位置：[main](main)

- `main.tex` 是报告唯一正文源文件；`main.pdf` 是提交版本。
- `graphics/` 保存市场规模、EPI、TOPSIS、敏感性和供应国结构图。
- Marp Markdown 是 PPT 的源文件，`.pptx` 是编译结果。
- 讲稿按 PPT 页码组织，长度约为七分钟。

### 8. 输出约束和写作规则

位置：[output-restrictions](output-restrictions)

竞赛要求报告参考 ITC 国际市场研究模板，涵盖产品概况、全球贸易、国家出口业绩、市场筛选、目标市场特性和前景分析等内容，中文撰写，字数建议在1万字以内。`humanizer-zh` 用于压缩套话、模糊归因和不推进论证的句子。

## 数学建模：从14国数据到前三市场

### 第一步：建立14国输入表

模型输入见 [model_inputs.csv](sources/20260905-CHN-Roborock-HS85098090-rcep-v01/model_inputs.csv)。每个国家一行，拼接三个 ITC 工具：

1. Trade Map 提供进口规模、CAGR、中国份额和供应商排名。
2. Export Potential Map 提供 EPI、基准出口额和未实现潜力。
3. Market Access Map 提供目的国税则线、适用税率和 NTM 记录。

只有进口额、CAGR、中国份额、EPI和未实现潜力均完整的市场进入主模型，因此样本从14国变为11国。

### 第二步：构造五个评分指标

| 指标 | 公式或字段 | 方向 | 战略权重 | 它说明什么 |
|---|---|---:|---:|---|
| 市场规模 | 2025年目的国自全球进口额 | 正向 | 30% | 当前可争取的需求池有多大 |
| 市场增长 | $CAGR=(M_{2025}/M_{2020})^{1/5}-1$ | 正向 | 10% | 需求是在扩张还是收缩；小基数市场可能出现高增速 |
| 中国供应份额 | 自中国进口额÷自全球进口额 | 正向 | 10% | 中国供给在当地是否已有渠道和接受基础；高份额也意味着中国品牌竞争更强 |
| 未实现潜力金额 | $\max(EPI-Baseline,0)$ | 正向 | 30% | 绝对可拓展空间有多大 |
| 未实现潜力比例 | 未实现潜力÷EPI | 正向 | 20% | EPI中还有多大比例尚未实现，避免只奖励已经充分开发的大市场 |

EPI本身没有再作为第六项直接计权，因为未实现潜力金额和比例已经吸收了 EPI 信息。中国供应商排名在11个完整市场中均为第1，适用关税也均为0%，两者没有横向区分度，因此保留为解释和审计字段，不进入最终五指标分数。NTM记录覆盖不完整，且条目数不能直接代表合规成本，也没有进入主模型。

### 第三步：变换和标准化

进口额和未实现潜力金额跨度大，先做对数变换：

$$
x'_{ij}=\ln(1+x_{ij})
$$

这样仍保留“大市场更优”的方向，同时减少日本、韩国等大体量市场对距离计算的压制。

五项指标均为正向指标，再做 Min—Max 标准化：

$$
z_{ij}=\frac{x_{ij}-\min(x_j)}{\max(x_j)-\min(x_j)}
$$

标准化后每个指标位于0到1之间。完整矩阵见 [model_normalized.csv](sources/20260905-CHN-Roborock-HS85098090-rcep-v01/model_normalized.csv)。

### 第四步：赋权

最终报告采用战略权重：市场规模30%、增长10%、中国份额10%、未实现潜力金额30%、未实现潜力比例20%。这套权重把“足够大的需求池”和“可拓展的绝对空间”放在首位。

项目另外计算了两套对照：

- 等权：五项各20%，观察结论是否依赖人工偏好。
- 熵权：根据指标在11国之间的信息差异自动赋权。当前熵权分别为18.72%、21.79%、18.13%、15.10%和26.27%。它会提高增长率和未实现比例这类离散度较高指标的影响。

权重文件见 [model_weights.csv](sources/20260905-CHN-Roborock-HS85098090-rcep-v01/model_weights.csv)。

### 第五步：TOPSIS计算

加权标准化值为：

$$
v_{ij}=w_jz_{ij}
$$

对每个指标取最优值和最差值，计算市场到正理想解、负理想解的欧氏距离：

$$
D_i^+=\sqrt{\sum_j(v_{ij}-v_j^+)^2},\qquad
D_i^-=\sqrt{\sum_j(v_{ij}-v_j^-)^2}
$$

TOPSIS贴近度为：

$$
C_i=\frac{D_i^-}{D_i^++D_i^-}
$$

$C_i$ 越高，表示该市场越接近“规模大、增长快、中国供应基础强、未实现空间大”的理想组合。它是相对分数，不是成功概率。

计算脚本见 [recalculate_model.ps1](sources/20260905-CHN-Roborock-HS85098090-rcep-v01/recalculate_model.ps1)。

### 第六步：敏感性分析

项目做了两层检查。

第一层比较战略权重、等权和熵权：

| 权重情景 | 前三名 | 说明 |
|---|---|---|
| 战略权重 | 韩国、日本、澳大利亚 | 强调市场规模和绝对未实现空间，是正文采用的情景 |
| 等权TOPSIS | 韩国、印度尼西亚、澳大利亚 | 中国份额和相对潜力获得更均衡影响，日本降至第4 |
| 熵权TOPSIS | 柬埔寨、新西兰、印度尼西亚 | 高增长和高未实现比例被放大，小市场明显上升 |

第二层以战略权重为均值，从 `Dirichlet(40w)` 分布随机生成5,000组权重，随机种子为 `850980`。每组权重都重新运行 TOPSIS，再统计进入前三的比例：

| 市场 | 进入前三的比例 | 解释 |
|---|---:|---|
| 韩国 | 98.9% | 对权重扰动最稳定 |
| 日本 | 90.6% | 规模和潜力优势使其多数情况下仍入选 |
| 澳大利亚 | 62.9% | 能入选，但属于边界市场 |
| 新西兰 | 30.6% | 是澳大利亚最主要的替代项 |
| 印度尼西亚 | 15.5% | 中国份额高，但规模、增长和潜力组合不及前三稳定 |

澳大利亚最终保留，是因为其2025年进口规模约为新西兰的7.3倍，且进口增长率和中国供应份额更高。敏感性结果见 [monte_carlo_sensitivity.csv](sources/20260905-CHN-Roborock-HS85098090-rcep-v01/monte_carlo_sensitivity.csv)。

## 结果怎样解读

### 韩国：优先验证增长

韩国2025年进口额为3.073亿美元，2020—2025年 CAGR 为7.12%，EPI为4.593亿美元，未实现潜力为1.601亿美元，中国供应份额为84.12%。它没有日本的绝对规模，但规模、增长和潜力同时处于较高水平，因此战略权重情景排第一。

进入重点是旗舰和全能基站产品，同时先落实售后合作、备件仓和维修时效。高中国份额说明市场接受中国供给，也说明零售页面上的功能和服务比较会很直接。

### 日本：争取最大需求池

日本2025年进口额为5.313亿美元，EPI为6.433亿美元，未实现潜力为2.172亿美元，三项绝对规模指标均为候选市场最高；五年 CAGR 为 -3.57%。日本机会主要来自存量替换和品牌份额转移，而不是市场自然增长。

产品组合应强调低矮通行、导航准确、低维护、耗材供应和售后稳定，中高端主力款承担销量，旗舰款建立技术认知。

### 澳大利亚：验证英语市场复制

澳大利亚2025年进口额为2.031亿美元，五年 CAGR 为6.10%，EPI为2.092亿美元，未实现潜力为6,316万美元，中国供应份额为85.12%。它的战略得分低于日韩，但规模明显大于新西兰。

适合测试大户型、地毯、毛发和长续航场景，并统一零售、电商与官网的保修、耗材和退换货规则。

## RCEP体系在本项目中做什么

ITC完成“市场筛选”，RCEP完成“规则落地”。RCEP资料按以下层次使用：

| 法律层次 | 项目关注点 | 对方案的影响 |
|---|---|---|
| 第2章与附件一 | 货物贸易、关税减让、税则差异和HS转版 | 核对承诺税率与目的国税则线 |
| 第3章与附件3A、3B | 原产资格、累积、RVC、证明文件 | 决定产品能否享受RCEP优惠 |
| 第4章 | 预裁定、放行、风险管理和海关合作 | 降低归类和通关的不确定性 |
| 第6章 | 标准、技术法规和合格评定 | 指向电器安全、EMC、无线、电池和标签合规 |
| 第7章 | 保障、反倾销和反补贴 | 说明零关税之外仍有贸易救济风险 |

### 三国关税结论

| 市场 | RCEP税则线 | 附件一承诺 | ITC本次返回的适用税率 |
|---|---|---|---:|
| 日本 | 850980.000 | `Free` | 0% |
| 韩国 | 8509.80.90.00 | 对中国表基准8%，第一年起0% | 0% |
| 澳大利亚 | 8509.80.90 | 基准及所列年度均为0% | 0% |

三国在本次查询中均为0%，因此关税没有拉开 TOPSIS 得分。关税数据转而支持经营判断：竞争重点落在产品、渠道和售后，而不是三个市场之间的税差。

承诺表与实际适用税率不是同一个概念。承诺表给出协定降税路径；实际报关还要匹配目的国税则线、当期税率和原产资格。本项目用 RCEP 原文解释制度，用 ITC Market Access Map 核对访问日税率。

### 原产地规则

RCEP HS2022 产品特定原产地规则对 `8509.80 Other appliances` 规定：

```text
CTSH or RVC40
```

两条路径任选其一：

- `CTSH`：所有非原产材料在生产后发生六位子目改变。
- `RVC40`：区域价值成分不低于40%。

RVC常用扣减法可以写为：

$$
RVC=\frac{FOB-VNM}{FOB}\times100\%
$$

其中 `VNM` 是非原产材料价值。正式计算需要 BOM、材料原产国和HS、采购凭证、FOB、汇率及生产记录，不能用“国产化率”替代。

第3.4条允许区域累积。来自其他RCEP成员方、并已取得原产资格的材料，可以计入中国生产中的原产成分。这使电机、传感器、芯片、电池等区域采购既能服务供应链效率，也可能改善 RVC40 结果。

原产地证明和运输证据见 [origin-proof-checklist.md](RCEP-rules/05-analysis/origin-proof-checklist.md)。

## ITC和RCEP怎样组成一条论证链

```text
产品与HS边界
      ↓
Trade Map：规模、增长、中国供应位置
      ↓
Export Potential Map：EPI与未实现空间
      ↓
TOPSIS：把11个完整市场压缩为优先级
      ↓
敏感性分析：检查前三名是否依赖单一权重
      ↓
Market Access Map：核对实际适用税率与NTM
      ↓
RCEP附件一：核对关税承诺路径
      ↓
RCEP第3章：判断CTSH/RVC40、累积和证明路线
      ↓
产品、渠道、售后与试销安排
```

ITC不是RCEP规则的替代品，RCEP也不负责判断哪个市场需求最大。前者给出可比较的市场证据，后者把市场选择转化为可执行的关税、原产地和通关方案。

## 来源追踪和引用

项目采用下面的引用链：

```text
报告中的事实
→ fact_registry.csv 的 fact_id
→ source_id
→ source_ledger-master.csv 的查询URL、参数和访问时间
→ raw_file
→ file-inventory-sha256.csv 的文件哈希
```

主要文件：

- [fact_registry.csv](sources/20260905-CHN-Roborock-HS85098090-rcep-v01/fact_registry.csv)
- [source_ledger_master.csv](sources/20260905-CHN-Roborock-HS85098090-rcep-v01/source_ledger_master.csv)
- [ITC file-inventory-sha256.csv](raw-material/ITC-data/file-inventory-sha256.csv)
- [RCEP source-ledger.csv](RCEP-rules/source-ledger.csv)
- [RCEP analysis-lineage.csv](RCEP-rules/00-index/analysis-lineage.csv)

对外提交的 PDF 尾注不写本地文件路径，但内部工作底稿保留路径和哈希，便于复核。

## 哪些模型文件可以引用

`sources` 目录保留了早期试算和最终重算。正文、PPT和讲稿采用2026年9月6日以后形成的五指标战略权重版本。

| 文件 | 状态 | 用途 |
|---|---|---|
| `model_inputs.csv` | 当前 | 14国原始模型输入和来源ID |
| `model_normalized.csv` | 当前 | 11国五指标标准化矩阵 |
| `model_weights.csv` | 当前 | 战略、等权、熵权三套权重 |
| `market_ranking_recalculated.csv` | **最终主结果** | 战略权重排名及两套对照排名 |
| `strategy_topsis_scores.csv` | 当前 | 图表使用的战略TOPSIS得分 |
| `sensitivity_results.csv` | 当前 | 三套权重情景的完整排名 |
| `monte_carlo_sensitivity.csv` | 当前 | 5,000次权重扰动结果 |
| `market_ranking.csv` | 历史版本 | 早期等权筛选，含重复行，不用于最终答辩 |
| `equal_weight_scores.csv` | 历史试算 | 与最终重算口径不同，不用于引用 |
| 该子目录原 `README.md` | 早期说明 | 仍描述等权主模型；以本总README和最终结果文件为准 |

如果队友只需要一个排名文件，请打开 `market_ranking_recalculated.csv`。

## 复现与编译

### 重算模型

在项目根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File sources\20260905-CHN-Roborock-HS85098090-rcep-v01\recalculate_model.ps1
```

该脚本重建标准化矩阵、三套权重结果和最终战略排名。

### 编译PPT

安装 Node.js 依赖后运行：

```powershell
npm install
npm run ppt:build
```

Marp 版本固定为4.5.1，编译脚本会调用本机 Chrome 或 Edge。

### 编译报告

进入 `main` 后使用 XeLaTeX 至少编译两遍，以生成目录和尾注引用：

```powershell
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex
```

`build_report_charts.py` 是图表生成脚本。当前脚本中的供应国图仍保留一处历史目录引用；直接重跑全部图表前，应先把该处路径核对为根目录下的 `raw-material/ITC-data/.../derived/top_suppliers_2025.csv`。现有 `main/graphics` 图表已经可以用于报告和PPT。

## 答辩时统一使用的表述

- 说“按中国申报码85098090.00研究，在ITC中使用HS6 850980产品组”，不要把六位组说成扫地机器人专属市场。
- 说“TOPSIS市场吸引力得分”，不要说“ITC官方排名”。ITC提供输入数据，排名由本组计算。
- 说“EPI是供给、需求和双边条件形成的前瞻性基准”，不要把它说成未来销售额。
- 说“中国供应份额高说明供给基础强，同时意味着中国品牌竞争集中”，不要只把高份额解释为进入容易。
- 说“三国当前返回适用税率均为0%，关税不构成横向区分”，不要把零关税说成零合规成本。
- 说“8509.80的PSR为CTSH或RVC40，二者任选其一”，不要说成必须同时满足。
- 说“韩国和日本入选稳定，澳大利亚是边界选择”；澳大利亚依靠更大的进口池击败新西兰。

## 一分钟答辩版

我们先用 Trade Map 比较14个RCEP候选市场的进口规模、五年增长和中国供应位置，再用 Export Potential Map 加入 EPI 与未实现潜力。老挝、缅甸和越南缺少2025年目的国直接进口值，因此11国进入模型。五项指标经过对数变换和 Min—Max 标准化后，按30%、10%、10%、30%、20%的战略权重进入 TOPSIS。韩国、日本和澳大利亚分别得到0.733、0.719和0.661。5,000组权重扰动中，韩国和日本进入前三的比例为98.9%和90.6%，澳大利亚为62.9%，所以澳大利亚是边界市场。随后用 Market Access Map 与RCEP附件一核对税率，三国本次返回适用税率均为0%；HS8509.80的原产地规则是CTSH或RVC40，并可使用区域累积。由此形成韩国验证增长、日本争取最大需求池、澳大利亚验证英语市场复制的进入组合。
