先说结论：我刚核过这三个站点目前的公开页面。**日本 価格.com、韩国 Danawa、澳大利亚 GetPrice 都没有在普通商品列表/详情页强制验证码，我没有发现哪个需要直接排除。** 但三者都不适合“高速全站爬取”；尤其 価格.com 和 Danawa 对内容复制/加工有明确限制，因此 Codex 应采取**低频、定向、只抓本研究需要字段、遇到拒绝立即停止**的方式，并在每次运行前重新检查 robots.txt / 使用条款。価格.com 的 robots.txt 目前并未整体禁止机器人扫地机的 `itemlist.aspx` 商品列表，但禁止 `/ksearch/`、价格历史接口等若干路径；其使用条款也限制未经同意复制、保存和再分发站内信息。[kakaku.com](https://kakaku.com/robots.txt) Danawa 同样明确标注其商品内容受保护、未经同意禁止复制和加工。[丹娜瓦客服中心](https://help.danawa.com/serviceHelpList.php?cate1=5&cate2=0&utm_source=chatgpt.com)

所以我建议让 Codex 做的不是“网站镜像式爬虫”，而是一个**竞争 SKU 数据采集器**。

------

# 一、先固定研究口径

三个国家：

| 国家     | 价格比较网站      | 币种 |
| -------- | ----------------- | ---- |
| 日本     | 価格.com / Kakaku | JPY  |
| 韩国     | Danawa            | KRW  |
| 澳大利亚 | GetPrice          | AUD  |

五个品牌统一标准化为：

| `brand_std` | 中文   | 日本搜索名             | 韩国搜索名 | 澳大利亚 |
| ----------- | ------ | ---------------------- | ---------- | -------- |
| `roborock`  | 石头   | Roborock               | 로보락     | Roborock |
| `ecovacs`   | 科沃斯 | エコバックス / ECOVACS | 에코백스   | Ecovacs  |
| `xiaomi`    | 小米   | Xiaomi / シャオミ      | 샤오미     | Xiaomi   |
| `dreame`    | 追觅   | Dreame / ドリーミー    | 드리미     | Dreame   |
| `narwal`    | 云鲸   | Narwal / ナーワル      | 나르왈     | Narwal   |

日本 価格.com 当前机器人扫地机分类确实覆盖这五个品牌；公开列表目前显示 Roborock、ECOVACS、Dreame、Xiaomi、Narwal 都有独立厂商筛选。[kakaku.com](https://kakaku.com/kaden/robot-cleaner/itemlist.aspx?utm_source=chatgpt.com) 韩国 Danawa 也能查到这五个品牌的商品详情页，例如 Roborock S8、ECOVACS T50 Pro Omni、Dreame L10 Ultra、Xiaomi S20、Narwal Freo Z10 Ultra。[비교하고 잘 사는, 다나와 : 가격비교 사이트](https://prod.danawa.com/info/?pcode=19702361&utm_source=chatgpt.com) 澳大利亚 GetPrice 同样有五个品牌，包括 Narwal 和 Xiaomi。[Getprice](https://www.getprice.com.au/search/robot-vacuum?utm_source=chatgpt.com)

------

# 二、不要把所有数据塞进一个 CSV

我建议 Codex 建这个目录：

```
retail_competition/
│
├── README.md
│
├── config/
│   ├── brands.yaml
│   └── collection_rules.yaml
│
├── raw/
│   ├── JP_Kakaku/
│   ├── KR_Danawa/
│   └── AU_GetPrice/
│
├── metadata/
│   ├── source_ledger.csv
│   ├── crawl_log.csv
│   └── model_crosswalk.csv
│
├── cleaned/
│   ├── products.csv
│   ├── retailer_offers.csv
│   └── specifications.csv
│
└── analysis/
    ├── price_positioning.csv
    ├── brand_summary.csv
    └── data_quality_report.md
```

这里最关键的是：

> **原始抓取 → 清洗后的SKU → 价格分析**

必须分开。

------

# 三、统一产品表格式

`cleaned/products.csv` 一行代表一个**国家市场中的一个SKU/变体**。

至少固定这些字段：

```
observation_id
snapshot_date
accessed_at
country
country_iso3
source_site

brand_std
brand_raw

model_name_raw
model_name_normalized
variant_raw
color
purchase_type

product_scope
is_robot_vacuum
is_currently_sold

currency

lowest_price
highest_price
representative_price
representative_price_method
rrp
seller_count

site_rank
site_rank_type
rating
review_count

release_date
registration_date

suction_pa
cleaning_mode

auto_empty
mop_wash
hot_water_mop_wash
mop_dry
auto_water_refill
mop_lift
obstacle_avoidance
camera
lidar
dock_included

robot_height_mm

product_url
listing_url
source_id

price_basis
promotion_flag
data_quality_flag
notes
```

**缺失必须为空值，不得填 0。**

例如网站没给吸力：

```
suction_pa = NA
```

不是：

```
suction_pa = 0
```

------

# 四、价格统一规则

这是三个网站比较时最重要的一点。

不要直接把“全网最低价”当市场价格。每个SKU保留：

\[ P_{\min},\quad P_{\max},\quad P_{\text{representative}} \]

如果商品详情页有至少3个正常零售商报价：

\[ P_{\text{representative}} = Median(P_1,\ldots,P_n) \]

如果只有1–2个零售商：

```
representative_price = lowest normal retail price
representative_price_method = "lowest_available_<3_offers"
```

同时**排除或单独标记**：

- 会员专属价
- 信用卡优惠价
- 优惠券后价格
- 积分抵扣价
- 二手
- 翻新
- 配件
- 海淘/海外购，除非研究目的明确需要
- 异常清仓

之后价格带分析才在 `analysis/` 中进行。

------

# 五、日本：価格.com

这里的数据质量其实最好之一。

目前机器人扫地机页面直接提供：

- 最低价
- 畅销/关注排名
- 评论评分
- 评论数量
- 登记日期
- 发售日期
- 清洁类型
- 自动回充等参数

而且单独存在品牌页。[kakaku.com](https://kakaku.com/kaden/robot-cleaner/itemlist.aspx?utm_source=chatgpt.com)

但要特别注意：

**不要使用 `/ksearch/`，不要自动调用价格历史隐藏接口。** 这些路径目前被 robots.txt 明确限制。[kakaku.com](https://kakaku.com/robots.txt)

另外：

- `売れ筋ランキング` 可以存；
- 但只能叫 **Kakaku站内排名**；
- 绝不能表述成“日本市场销量排名”。

### 给 Codex 的日本提示词

```
执行日本机器人扫地机竞争SKU采集。

研究网站：
https://kakaku.com/kaden/robot-cleaner/

研究市场：
Japan / JPN

研究品牌：
- Roborock
- ECOVACS / エコバックス
- Xiaomi / シャオミ
- Dreame / ドリーミー
- Narwal / ナーワル

目标：
建立五个品牌当前在日本市场销售的机器人扫地机SKU、零售价和核心规格数据库。

在开始采集前：
1. 检查当前 robots.txt 和网站使用条款。
2. 禁止访问 robots.txt 明确 Disallow 的路径，包括 /ksearch/、价格历史相关内部路径、jump等。
3. 不调用隐藏API、不逆向工程内部接口。
4. 不绕过验证码、反爬或访问限制。
5. 如果网站拒绝自动访问，立即停止并记录 manual_intervention_required。
6. 低频访问，仅采集完成研究所需的公开商品列表和商品详情页。

采集范围：
只保留“地面机器人扫地机”。

排除：
- 窗户清洁机器人
- 手持吸尘器
- 洗地机
- 配件
- 耗材
- 二手
- 无当前报价且明显停售的旧SKU

品牌筛选优先通过机器人扫地机分类下的manufacturer过滤页面完成，不使用站内/ksearch/。

对于每个品牌：
1. 打开品牌机器人扫地机列表。
2. 收集所有仍有至少一个当前零售报价的SKU。
3. 对每个SKU访问公开商品详情页。
4. 保存以下字段：

brand_raw
model_name_raw
variant_raw
lowest_price
seller_count
site_rank
site_rank_type
rating
review_count
registration_date
release_date
cleaning_mode
suction_pa（若提供）
dock_included
auto_empty
mop_wash
mop_dry
mop_lift
obstacle_avoidance
camera
lidar
robot_height_mm
product_url
listing_url

价格：
- currency = JPY
- 保留网页显示的最低价；
- 若详情页公开多个零售商价格，则额外保存 retailer_offers.csv；
- 会员、信用卡、积分、优惠券价格不得覆盖普通零售价；
- 如存在メーカー直販モデル，设置 direct_sale_model=true；
- 同一型号不同颜色不要直接视为不同产品系列，保留variant但建立model family。

排名：
价格.com的売れ筋/注目排名只能记录为site_rank。
不得解释为日本市场销售份额或真实销量排名。

重复处理：
同一型号不同颜色、直营版、套餐版分别保留原始行；
在model_name_normalized层建立基础型号映射。

每条数据必须保存：
source_id
product_url
listing_url
accessed_at
snapshot_date

不要保存完整网页镜像。
如运行环境允许且网站条款允许，可保存用于内部审计的局部截图；
否则只保存字段、URL、访问时间和页面标题。

输出：
raw/JP_Kakaku/
metadata/source_ledger.csv
cleaned/products_JPN.csv
cleaned/retailer_offers_JPN.csv
logs/crawl_JPN.csv

完成后生成：
1. 五品牌SKU数量
2. 数据缺失率
3. 无法自动获取的字段
4. 疑似重复型号
5. 需要人工复核的页面
```

------

# 六、韩国：Danawa

Danawa 的优势是**规格特别完整**。

目前公开商品页会直接显示：

- 吸力 Pa
- 传感器
- AI识别
- 障碍物规避
- 越障能力
- 基站功能
- 热水洗拖布
- 烘干
- 清洁剂投放
- 尺寸
- 重量
- 最低价和不同商家报价

例如 Narwal Freo Z10 Ultra 页面目前就同时提供 18,000 Pa、传感器、基站功能和多家零售报价。[비교하고 잘 사는, 다나와 : 가격비교 사이트](https://prod.danawa.com/info/?pcode=78234203&utm_source=chatgpt.com)

### 最大的坑：`일반구매` 和 `해외구매`

Danawa 会把：

> **韩国正常渠道购买**

和

> **海外购买/平行进口**

分开。

例如同一个 Narwal Freo 就同时存在 일반구매 和 해외구매，价格差异巨大。[비교하고 잘 사는, 다나와 : 가격비교 사이트](https://prod.danawa.com/info/?pcode=17974391&utm_source=chatgpt.com)

因此主分析：

> **只使用 일반구매 / 韩国正常销售渠道。**

海外购另存：

```
purchase_type = overseas_purchase
```

但不能混进韩国市场主流零售价。

另外 Danawa 会展示：

> 멤버십/카드결제 최대 혜택가

也就是会员/信用卡最大优惠。

**绝对不能把这个当普通市场价格。**

### 给 Codex 的韩国提示词

```
执行韩国机器人扫地机竞争SKU采集。

研究网站：
Danawa
https://prod.danawa.com/

市场：
South Korea / KOR

品牌：
- 로보락 / Roborock
- 에코백스 / ECOVACS
- 샤오미 / Xiaomi
- 드리미 / Dreame
- 나르왈 / Narwal

执行前：
1. 检查网站当前使用条款、robots政策和公开访问状态。
2. 不调用隐藏接口。
3. 不绕过登录、验证码或访问限制。
4. 低频访问。
5. 如果页面阻止自动访问，停止该页面并写入manual_interventions.csv。

目标：
建立韩国本地正常零售渠道中的五品牌机器人扫地机SKU、价格和功能参数数据库。

产品范围：
仅机器人扫地机/扫拖机器人。

排除：
- 창문청소机器人
- 手持/立式吸尘器
- 洗地机
- 商用机器人
- 配件
- 耗材
- 二手商品

非常重要：
Danawa可能同时提供：
일반구매
해외구매

主数据集只使用：
purchase_type = general_purchase

海外购买商品：
purchase_type = overseas_purchase
单独保存，但不得进入韩国主流零售价分析。

对于每个SKU采集：

brand_raw
model_name_raw
purchase_type
registration_month

normal_lowest_price
member_card_price
price_min
price_max
seller_count

suction_pa
cleaning_mode

sensor_lidar
sensor_tof
camera
ai_object_recognition
obstacle_avoidance

threshold_height_cm
robot_height_mm

auto_empty
mop_wash
hot_water_mop_wash
mop_dry
detergent_auto_feed
auto_water_refill
direct_water_connection
station_self_cleaning

battery_runtime
weight
dimensions

product_url
source_id
accessed_at

价格标准：
currency = KRW

主价格不得使用：
- 네이버플러스积分抵扣后的“体感价格”
- 멤버십最大优惠价
- 信用卡特定优惠价

normal_lowest_price 应使用Danawa显示的普通最低购买价格。

若有多个普通商城报价：
全部保存到 retailer_offers.csv。

至少保存：
retailer
price
shipping
price_with_shipping
promotion_type
membership_required
offer_url（如公开）

若Danawa明确显示배송비 포함，
记录：
price_basis = shipping_included

否则：
price_basis = product_only 或 unknown。

价格历史：
本轮不强制抓取动态图。
如果网页通过公开可见文本提供1/3/6/12个月价格序列，可以保存；
如果依赖内部接口或动态图表，则跳过，不逆向抓取。

产品规格优先保留Danawa原始韩文：
spec_raw

再生成标准化字段。

输出：
raw/KR_Danawa/
metadata/source_ledger.csv
cleaned/products_KOR.csv
cleaned/retailer_offers_KOR.csv
logs/crawl_KOR.csv

完成后报告：
- 一般购买SKU数量
- 海外购买SKU数量
- 五品牌覆盖情况
- 规格字段缺失率
- 重复SKU
- 异常价格
- 需要人工检查的记录
```

Danawa 自己的帮助页面还明确说明，可以通过关键词排除 `병행수입`、`해외구매`，所以这个过滤逻辑是站点本身支持的。[丹娜瓦客服中心](https://help.danawa.com/serviceHelpList.php?cate1=5&utm_source=chatgpt.com)

------

# 七、澳大利亚：GetPrice

GetPrice技术上反而最好处理。

目前五品牌都有结果，而且商品详情页可以提供：

- 当前价格区间
- 最低价
- 零售商
- 产品加入数据库时间
- 部分规格

例如 Roborock Qrevo C Pro 页面目前列出三家零售商及其价格；Xiaomi X20 Plus 页面则只有一家。[Getprice](https://www.getprice.com.au/product/roborock-qrevo-c-pro-robotic-vacuum-cleaner?utm_source=chatgpt.com)

但 GetPrice 有一个**非常重要的问题**：

> **不要使用搜索结果排列顺序衡量畅销程度。**

GetPrice 自己对商户说明，在很多类别中，商户 CPC 出价会影响页面排名。[Getprice](https://www.getprice.com.au/signup?utm_source=chatgpt.com)

因此：

```
GetPrice rank ≠ popularity
GetPrice rank ≠ sales rank
```

这里主要获取：

> **SKU + 商家报价 + 价格范围**

就够了。

### 给 Codex 的澳大利亚提示词

```
执行澳大利亚机器人扫地机竞争SKU采集。

网站：
https://www.getprice.com.au/

市场：
Australia / AUS

品牌：
- Roborock
- Ecovacs
- Xiaomi
- Dreame
- Narwal

运行前：
1. 检查网站当前Terms、robots政策和公开访问状态。
2. 不使用未公开API。
3. 不绕过验证码、访问限制或登录。
4. 使用低频页面访问。
5. 如出现阻止自动化的页面，停止并记录。

分别搜索：
roborock
ecovacs
xiaomi
dreame
narwal

不要仅依赖“robot vacuum”总搜索，因为搜索结果会混入大量：
- accessories
- spare parts
- wet/dry vacuums
- stick vacuums
- window robots
- lawn robots

只保留：
category = Vacuum Cleaners
且
Type / title 明确属于 Robotic Vacuum / Robot Vacuum and Mop。

产品必须至少存在一个当前可购买零售报价。

对于每个SKU保存：

brand_raw
model_name_raw
model_name_normalized

lowest_price
highest_price
seller_count
rrp（若明确提供）

currency = AUD

retailer
retailer_price
shipping
stock_status

product_type
suction_pa（若有）
dock_included
auto_empty
mop_wash
mop_dry
mop_lift
obstacle_avoidance

date_added
product_url
search_url

promotion_flag
promoted_offer_flag

source_id
accessed_at

非常重要：
GetPrice存在Promoted offer和affiliate listing。

任何带：
Promoted
Sponsored
coupon
exclusive discount

的报价必须标记。

不得把promoted listing的出现顺序解释为：
- 销量排名
- 市场份额
- 流行度
- 品牌排名

site_rank字段对GetPrice设为NA。

如果一个SKU至少有3个普通零售报价：

representative_price =
median(normal non-membership retailer prices)

如果少于3个：

representative_price =
lowest normal available price

并记录：
representative_price_method

排除：
- refurbished
- used
- accessory-only
- replacement part
- window cleaner
- wet/dry stick vacuum
- lawn mower robot
- commercial floor robot

对于Amazon等平台报价：
若只提供平台市场报价而无法确定seller质量，
保留offer，
但设置：
seller_quality_flag = marketplace_unverified

输出：
raw/AU_GetPrice/
metadata/source_ledger.csv
cleaned/products_AUS.csv
cleaned/retailer_offers_AUS.csv
logs/crawl_AUS.csv

最终生成：
- 五品牌有效SKU数量
- 每品牌价格中位数
- 每品牌Q1/Q3
- 价格覆盖范围
- 零售商数量
- 数据缺失情况
- promoted offer比例
```

------

# 八、三国数据合并时还有一道非常重要的“型号标准化”

不要直接按照字符串合并。

例如：

```
Roborock Qrevo Curv
Roborock Qrevo Curv 2
Roborock Qrevo Curv 2 Flow
```

绝对不能让 Codex 因为名字相似就认定为同一个SKU。

建立：

```
metadata/model_crosswalk.csv
```

格式：

| brand | country | model_raw | model_family | global_equivalent | confidence | evidence |
| ----- | ------- | --------- | ------------ | ----------------- | ---------- | -------- |
|       |         |           |              |                   |            |          |

只有：

- 官方型号完全一致，或
- 品牌官网明确证明为同一国际型号

才能：

```
global_equivalent = same
```

否则：

```
global_equivalent = uncertain
```

这对日本/韩国尤其重要，因为品牌经常有地区专供型号。

------

# 九、最终价格分析统一这样算

**永远保留本币价格。**

也就是说：

```
JPY
KRW
AUD
```

是原始研究数据。

如果之后想画：

> 日本 vs 韩国 vs 澳大利亚价格定位

再建立派生字段：

```
representative_price_cny
```

并单独保存：

```
fx_rate
fx_source
fx_date
```

不要把汇率换算后的人民币覆盖原始零售价。

------

# 十、最后可以给 Codex 一个总控 Prompt

等三个站点的 prompt 都跑通后，用：

```
按照 retail_competition 数据规范，对日本、韩国和澳大利亚的机器人扫地机竞争SKU进行完整采集。

研究品牌固定为：
Roborock
Ecovacs
Xiaomi
Dreame
Narwal

市场：
JPN
KOR
AUS

数据源：
Japan -> Kakaku
Korea -> Danawa
Australia -> GetPrice

分别严格遵守三个网站对应的采集规则。

目标不是全站爬虫，而是建立一个可用于学术案例研究的：
country × brand × SKU × retail price × specification
数据集。

必须保证：
1. 原始字段和标准化字段分离；
2. 所有记录都有source URL和accessed_at；
3. 价格优惠类型单独标记；
4. 海外购与正常本地销售分离；
5. 配件、手持吸尘器、窗户机器人等全部剔除；
6. 不使用GetPrice排列顺序作为销量排名；
7. 不把Kakaku站内排名解释为市场销量；
8. 不跨国自动合并名称相似但未经核验的SKU；
9. 不绕过验证码、robots限制或技术保护；
10. 任何失败都进入crawl_log，不得编造缺失数据。

完成采集后：
生成统一的：
cleaned/products_all_markets.csv
cleaned/retailer_offers_all_markets.csv
metadata/source_ledger.csv
metadata/model_crosswalk.csv

然后计算每一个 country × brand 的：
- valid SKU count
- median representative price
- Q1
- Q3
- minimum
- maximum

只进行描述性统计，不进行市场策略判断。
```

这样跑完以后，你们实际上就拥有了一个相当不错的：

\[ 3\ countries\times5\ brands\times SKU \]

**扫地机器人竞争产品数据库**。

而且这批数据不仅能做附件4要求的“价格定位分析”，后面还可以进一步做**价格—功能散点图、品牌价格带分布、功能配置聚类，以及石头科技相对竞品的 hedonic price / 性价比分析**。这时候你们案例研究会比单纯拿几个电商价格做表格扎实很多。