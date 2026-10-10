执行新西兰机器人扫地机零售竞争SKU数据采集。

研究市场：
New Zealand / NZL

数据源：
PriceSpy New Zealand
https://pricespy.co.nz/

研究品牌：

- Roborock
- Ecovacs
- Xiaomi
- Dreame
- Narwal

====================================
一、合规与访问规则
==================

开始前重新检查：

- PriceSpy Privacy Policy
- Rules and Guidelines
- Disclaimer
- Terms
- robots.txt（如果可以访问）

如果最新robots或条款明确禁止自动访问目标页面：
停止自动化并记录。

禁止：

- 绕过验证码
- 绕过访问频率限制
- 隐藏API调用
- 内部接口逆向
- 登录账号
- 创建PriceSpy账户
- 批量复制页面内容
- 保存图片
- 保存评论全文
- 镜像PriceSpy数据库

只采集研究所需事实字段。

采用低频访问。

出现：
403
429
CAPTCHA
bot challenge

立即停止。

====================================
二、研究范围
============

优先从：

Robot Vacuum Cleaners category

进入。

只采集：

Roborock
Ecovacs
Xiaomi
Dreame
Narwal

机器人扫地/扫拖一体产品。

排除：

window cleaners
robot lawn mowers
stick vacuums
handheld vacuums
accessories
consumables
used products
refurbished products

必须确认：

Category = Robot Vacuum Cleaners

====================================
三、产品字段
============

每个有效SKU记录：

country = New Zealand
country_iso3 = NZL
currency = NZD
source_site = PriceSpy

brand_raw
brand_std

model_name_raw
model_name_normalized
variant_raw

category

lowest_new_price
active_offer_count

representative_price
representative_price_method

site_popularity_rank

rating
review_count

product_url
category_url

accessed_at
snapshot_date
source_id

如果公开提供：

suction_pa
noise_db

mop_function
dock_included
self_emptying
automatic_mop_drying

obstacle_sensing
app_control
voice_control

lidar
navigation_method

threshold_height_cm

runtime_min
battery_capacity_mah

dust_capacity_robot_l
dust_capacity_base_l
water_capacity_l

robot_height_mm
weight_kg

缺失字段 = NA。

====================================
四、PriceSpy Rank解释
=====================

PriceSpy Rank 只能记录为：

site_popularity_rank

其含义：

PriceSpy站内基于用户流量形成的产品关注度排名。

禁止：

sales_rank
market_share_rank
NZ_market_sales_rank

禁止把Rank解释为真实新西兰销量排名。

====================================
五、零售报价
============

打开产品公开Prices页面。

记录所有当前新品正常报价：

retailer
price
currency

stock_status

shipping_cost
price_with_shipping

partner_store_flag
international_store_flag
used_flag

offer_url
source_id
accessed_at

PriceSpy自身说明价格表按价格排序，
合作付费商家不会因为合作关系获得更高的价格排序位置。

仍然保留：
partner_store_flag

供来源透明度审计。

====================================
六、国际商家处理
================

主分析只使用：

New Zealand domestic / nationally listed retailers

如果页面显示International Stores：

可以另存，
但不得进入新西兰主流零售价计算。

字段：

international_store_flag = true

主分析：

international_store_flag = false

====================================
七、代表价格计算
================

若有效新西兰本地新品报价 >= 3：

representative_price =
median(valid NZ retailer prices)

如果只有2个：

median(two prices)

如果只有1个：

single price

记录：

representative_price_method

不要简单使用最低价作为所有产品的代表价。

同时保留：

lowest_new_price

用于价格竞争分析。

====================================
八、运费
========

如果PriceSpy公开提供：

Price incl. delivery cost

则：

优先记录：

price_with_shipping

但必须同时保留商品裸价。

字段：

product_price
shipping_cost
price_with_shipping

如果无法确认运费：

shipping_cost = NA

不得推算。

====================================
九、Price History
=================

PriceSpy公开产品页提供Price History。

允许记录公开页面直接展示的：

lowest_new_price_now
3_month_low
3_month_high
price_trend_status

如果历史价格以网页文本或公开表格形式直接出现，
可以保存。

禁止：

- 调用隐藏price-history API
- 读取内部JS数据
- 逆向图表请求

如果只能看到交互式图形且无法通过公开HTML读取：

跳过完整时间序列。

不要为了得到历史数据突破接口限制。

====================================
十、新品与二手
==============

PriceSpy会区分新品与二手。

本研究：

只使用新品。

used_flag = false

所有二手报价：
不进入retail competition dataset。

====================================
十一、五品牌覆盖检查
====================

特别检查：

Roborock
Ecovacs
Xiaomi
Dreame
Narwal

当前PriceSpy中：

如果某品牌存在产品页但无active listing：

保留SKU存在记录：

currently_sold = false
active_offer_count = 0

但是：

representative_price = NA

不要把历史价格作为当前价格。

Narwal必须特别检查active listing情况，
因为部分旧型号可能仍有产品页但当前无报价。

# 十二、保存文件

raw/NZL-PriceSpy/

cleaned/products_NZL.csv
cleaned/retailer_offers_NZL.csv
cleaned/price_history_NZL.csv

metadata/source_ledger_NZL.csv

logs/crawl_NZL.csv

# 十三、完成后的检查

输出：

- 各品牌有效SKU数量
- 当前有售SKU数量
- 无当前报价SKU数量
- 每SKU平均零售商数量
- 单零售商SKU比例
- 价格历史覆盖率
- 规格缺失率
- 国际商家报价比例
- 疑似重复SKU
- 区域版本问题
- 需要人工核实的异常价格

最后只做描述性统计。
不要形成市场进入建议。






执行马来西亚机器人扫地机零售竞争数据采集。

研究市场：
Malaysia / MYS

研究品牌：

- Roborock
- Ecovacs
- Xiaomi
- Dreame
- Narwal

主数据源：
PriceMe Malaysia
https://my.priceme.com/

机器人扫地机分类：
Robot Vacuum Cleaners

补充数据源：
PriceShop Malaysia
https://my.priceshop.com/

====================================
一、合规与访问要求
==================

开始任何采集前：

1. 重新检查：

   - PriceMe Terms of Service
   - PriceMe Privacy Policy
   - robots.txt（如果可以访问）
   - PriceShop Terms of Use
   - PriceShop Privacy Policy
   - robots.txt（如果可以访问）
2. 如果 robots.txt 或最新条款明确禁止本任务涉及的自动访问路径：
   停止该路径采集，并记录：
   manual_intervention_required = true
3. 禁止：

   - 绕过验证码
   - 绕过 Cloudflare / CAPTCHA / anti-bot
   - 模拟登录
   - 创建账户
   - 使用价格提醒账户
   - 调用隐藏API
   - 逆向XHR/GraphQL/内部接口
   - 高并发请求
   - 镜像网站
   - 保存完整网站数据库
4. 只提取完成学术/竞赛市场研究所需的最小字段集合。
5. 访问频率保持低频。
   页面访问之间加入合理间隔。
   如果出现429、403、验证码或明显访问限制，立即停止自动访问。
6. 不保存用户评论全文、个人信息、商家联系人个人信息等无关字段。

====================================
二、PriceMe 主采集
==================

优先使用 PriceMe Malaysia 的：

Robot Vacuum Cleaners

类别页面和公开产品详情页。

不要依赖动态品牌过滤接口完成全量抓取；
如果分类页面动态加载失败：

优先：

1. 从类别页获取产品链接；
2. 使用公开搜索引擎/site search定位具体产品页；
3. 访问静态公开产品详情页。

不得逆向动态加载接口。

研究对象必须同时满足：

category = Robot Vacuum Cleaners

并且 brand 属于：

Roborock
Ecovacs
Xiaomi
Dreame
Narwal

排除：

- stick vacuum
- handheld vacuum
- wet/dry floor washer
- window robot
- lawn robot
- commercial robot
- accessories
- replacement parts
- cleaning solution
- dust bags
- brushes
- used/refurbished products

====================================
三、PriceMe 产品字段
====================

对每一个有效SKU提取：

country = Malaysia
country_iso3 = MYS
currency = MYR
source_site = PriceMe

brand_raw
brand_std

model_name_raw
model_name_normalized
variant_raw

category
current_stock_status

lowest_price
highest_active_price
active_offer_count

representative_price
representative_price_method

list_date_on_priceme

product_url
category_url

accessed_at
snapshot_date
source_id

如果公开页面提供，则进一步采集：

suction_pa
noise_db
runtime_min
dust_capacity_l
battery_capacity_mah

mop_function
dock_included
auto_empty
mop_wash
hot_water_mop_wash
mop_dry
auto_water_refill
mop_lift
obstacle_avoidance
camera
lidar
robot_height_mm

规格缺失：
使用 NA
不得填0。

====================================
四、零售商报价
==============

对于每一个SKU，将所有公开可见的当前报价另存到：

retailer_offers_MYS.csv

字段：

observation_id
brand_std
model_name_normalized

retailer
price
currency

stock_status
shipping_cost
price_with_shipping

offer_type
promotion_flag

marketplace_flag
official_store_flag

offer_url
product_url

accessed_at
source_id

如果页面只有一个报价：
仍保留该产品，但设置：

offer_count = 1
price_coverage_flag = low

====================================
五、马来西亚价格代表值
======================

若有效普通零售报价 >= 3：

representative_price =
median(all valid normal retail prices)

若有效报价 = 2：

representative_price =
median(two prices)

若有效报价 = 1：

representative_price =
single available price

并设置：

representative_price_method =
median_3plus
median_2
single_offer

不得把：

- 信用卡返现
- 积分价格
- 优惠券后价格
- 会员价
- 捆绑赠品折算价格

直接替代普通零售价。

====================================
六、PriceMe 历史价格
====================

PriceMe产品页面如果公开显示：

Price trend -> Show as table

则允许直接采集该公开表格中的：

date
retailer
lowest_price
price_change

保存到：

price_history_MYS.csv

禁止：

- 调用内部价格历史API
- 逆向图表数据接口

只读取页面上直接公开的表格数据。

====================================
七、Narwal 缺口处理
===================

PriceMe当前可能无法完整覆盖Narwal。

如果PriceMe类别中找不到Narwal：

不得把 Narwal 记为“马来西亚无销售”。

执行第二层验证：

PriceShop Malaysia
+
Narwal Malaysia官方销售渠道

PriceShop只作为补充来源。

优先提取：

model_name
official/list price
promotion price
launch_date
official availability
official sales channels

PriceShop中的新闻或发布内容不得用于估计
“市场代表性价格”。

对于Narwal：

若只能得到官方售价：

representative_price = NA
official_price = 实际值
price_source_type = official_or_launch_price

不要把官方首发价和PriceMe市场最低价混为同一指标。

例如：
Narwal在马来西亚的正式上市记录、Shopee和线下渠道信息可作为availability证据。

====================================
八、Source Ledger
=================

每一个页面都登记：

source_id
source_site
page_type
page_title
url
accessed_at

country
brand
model

source_type:
price_comparison
official_launch
official_store
retailer

不得只保存CSV而丢失来源URL。

====================================
九、质量检查
============

完成后输出：

1. 五品牌各自有效SKU数
2. PriceMe品牌覆盖率
3. Narwal是否需要补充源
4. 每个SKU有效报价数量
5. 单报价SKU比例
6. 价格历史覆盖率
7. 异常价格
8. 可能重复SKU
9. 需要人工确认的区域版/国际版型号
10. 所有访问失败和停止原因

不要进行市场策略判断。

只完成：
采集
清洗
标准化
来源登记
基础描述性统计
