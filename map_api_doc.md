地理编码
地理编码 API 服务地址
URL

请求方式

https://restapi.amap.com/v3/geocode/geo?parameters

GET

parameters 代表的参数包括必填参数和可选参数。所有参数均使用和号字符(&)进行分隔。下面的列表枚举了这些参数及其使用规则。
请求参数
参数名

含义

规则说明

是否必须

缺省值

key

高德Key

用户在高德地图官网 申请 Web 服务 API 类型 Key

必填

无

address

结构化地址信息

规则遵循：国家、省份、城市、区县、城镇、乡村、街道、门牌号码、屋邨、大厦，如：北京市朝阳区阜通东大街6号。

必填

无

city

指定查询的城市

可选输入内容包括：指定城市的中文（如北京）、指定城市的中文全拼（beijing）、citycode（010）、adcode（110000），不支持县级市。当指定城市查询内容为空时，会进行全国范围内的地址转换检索。

adcode 信息可参考 城市编码表 获取

可选

无，会进行全国范围内搜索

sig

数字签名

请参考 数字签名获取和使用方法

可选

无

output

返回数据格式类型

可选输入内容包括：JSON，XML。设置 JSON 返回结果数据将会以 JSON 结构构成；如果设置 XML 返回结果数据将以 XML 结构构成。

可选

JSON

callback

回调函数

callback 值是用户定义的函数名称，此参数只在 output 参数设置为 JSON 时有效。

可选

无

返回结果参数说明
响应结果的格式可以通过请求参数 output 指定，默认为 JSON 形式。

以下是返回参数说明：

名称

含义

规则说明

status

返回结果状态值

返回值为 0 或 1，0 表示请求失败；1 表示请求成功。

count

返回结果数目

返回结果的个数。

info

返回状态说明

当 status 为 0 时，info 会返回具体错误原因，否则返回“OK”。详情可以参阅 info 状态表

geocodes

地理编码信息列表

结果对象列表，包括下述字段：


country

国家

国内地址默认返回中国

province

地址所在的省份名

例如：北京市。此处需要注意的是，中国的四大直辖市也算作省级单位。

city

地址所在的城市名

例如：北京市

citycode

城市编码

例如：010

district

地址所在的区

例如：朝阳区

street

街道

例如：阜通东大街

number

门牌

例如：6号

adcode

区域编码

例如：110101

location

坐标点

经度，纬度

level

匹配级别

参见下方的地理编码匹配级别列表


提示
部分返回值当返回值存在时，将以字符串类型返回；当返回值不存在时，则以数组类型返回。

服务示例
https://restapi.amap.com/v3/geocode/geo?address=北京市朝阳区阜通东大街6号&output=XML&key=<用户的key>
参数

值

备注

必选

address

北京市朝阳区阜通东大街6号
填写结构化地址信息:省份＋城市＋区县＋城镇＋乡村＋街道＋门牌号码

是

city

北京
查询城市，可选：城市中文、中文全拼、citycode、adcode

否

运行
示例说明
address 是需要获取坐标的结构化地址，output（XML）用于指定返回数据的格式，Key 是用户请求数据的身份标识，详细可以参考上方的请求参数说明。

逆地理编码
逆地理编码 API 服务地址
URL

请求方式

https://restapi.amap.com/v3/geocode/regeo?parameters

GET

parameters 代表的参数包括必填参数和可选参数。所有参数均使用和号字符(&)进行分隔。下面的列表枚举了这些参数及其使用规则。
请求参数
参数名

含义

规则说明

是否必须

缺省值

key

高德Key

用户在高德地图官网 申请 Web 服务 API 类型 Key

必填

无

location

经纬度坐标

传入内容规则：经度在前，纬度在后，经纬度间以“,”分割，经纬度小数点后不要超过 6 位。

必填

无

poitype

返回附近 POI 类型

以下内容需要 extensions 参数为 all 时才生效。

逆地理编码在进行坐标解析之后不仅可以返回地址描述，也可以返回经纬度附近符合限定要求的 POI 内容（在 extensions 字段值为 all 时才会返回 POI 内容）。设置 POI 类型参数相当于为上述操作限定要求。参数仅支持传入 POI TYPECODE，可以传入多个 POI TYPECODE，相互之间用“|”分隔。获取 POI TYPECODE 可以参考 POI 分类码表

可选

无

radius

搜索半径

radius 取值范围：0~3000，默认值：1000。单位：米

可选

1000

extensions

返回结果控制

extensions 参数默认取值是 base，也就是返回基本地址信息；

extensions 参数取值为 all 时会返回基本地址信息、附近 POI 内容、道路信息以及道路交叉口信息。

可选

base

roadlevel

道路等级

以下内容需要 extensions 参数为 all 时才生效。

可选值：0，1  当 roadlevel=0时，显示所有道路 ； 当 roadlevel=1时，过滤非主干道路，仅输出主干道路数据 

可选

无

sig

数字签名

请参考 数字签名获取和使用方法

可选

无

output

返回数据格式类型

可选输入内容包括：JSON，XML。设置 JSON 返回结果数据将会以 JSON 结构构成；如果设置 XML 返回结果数据将以 XML 结构构成。

可选

JSON

callback

回调函数

callback 值是用户定义的函数名称，此参数只在 output 参数设置为 JSON 时有效。

可选

无

homeorcorp

是否优化 POI 返回顺序

以下内容需要 extensions 参数为 all 时才生效。

homeorcorp 参数的设置可以影响召回 POI 内容的排序策略，目前提供三个可选参数：

0：不对召回的排序策略进行干扰。

1：综合大数据分析将居家相关的 POI 内容优先返回，即优化返回结果中 pois 字段的poi 顺序。

2：综合大数据分析将公司相关的 POI 内容优先返回，即优化返回结果中 pois 字段的poi 顺序。

可选

0

返回结果参数说明
逆地理编码的响应结果的格式由请求参数 output 指定。

名称

含义

规则说明

status

返回结果状态值

返回值为 0 或 1，0 表示请求失败；1 表示请求成功。

info

返回状态说明

当 status 为 0 时，info 会返回具体错误原因，否则返回“OK”。详情可以参考 info 状态表

regeocode

逆地理编码列表

返回 regeocode 对象；regeocode 对象包含的数据如下：


addressComponent

地址元素列表



country

坐标点所在国家名称

例如：中国

 

province

 坐标点所在省名称 

 例如：北京市 

city

坐标点所在城市名称

请注意：当城市是省直辖县时返回为空，以及城市为北京、上海、天津、重庆四个直辖市时，该字段返回为空；省直辖县列表

citycode

城市编码

例如：010

district

坐标点所在区

例如：海淀区

adcode

行政区编码

例如：110108

township

坐标点所在乡镇/街道（此街道为社区街道，不是道路信息）

例如：燕园街道

towncode

乡镇街道编码

例如：110101001000

neighborhood

社区信息列表



name

社区名称

例如：北京大学

type

POI 类型

例如：科教文化服务;学校;高等院校


building

楼信息列表



name

建筑名称

例如：万达广场

type

类型

例如：科教文化服务;学校;高等院校

streetNumber

门牌信息列表



street

街道名称

例如：中关村北二条

number

门牌号

例如：3号

location

坐标点

经纬度坐标点：经度，纬度

direction

方向

坐标点所处街道方位

distance

门牌地址到请求坐标的距离

单位：米

seaArea

所属海域信息

例如：渤海

businessAreas

经纬度所属商圈列表



businessArea

商圈信息


location

商圈中心点经纬度


name

 商圈名称 

 例如：颐和园 

id

 商圈所在区域的 adcode 

 例如：朝阳区/海淀区 


roads

道路信息列表

请求参数 extensions 为 all 时返回如下内容


road

道路信息



id

道路 id


name

道路名称


distance

道路到请求坐标的距离

单位：米

direction

方位

输入点和此路的相对方位

location

坐标点



roadinters

道路交叉口列表

请求参数 extensions 为 all 时返回如下内容


roadinter

道路交叉口



distance

交叉路口到请求坐标的距离

单位：米

direction

方位

输入点相对路口的方位

location

路口经纬度


first_id

第一条道路 id


first_name

第一条道路名称


second_id

第二条道路 id


second_name

第二条道路名称



pois

poi 信息列表

请求参数 extensions 为 all 时返回如下内容


poi

poi 信息列表



id

poi 的 id


name

poi 点名称


type

poi 类型


tel

电话


distance

该 POI 的中心点到请求坐标的距离

单位：米

direction

方向

相对于输入点的方位

address

poi 地址信息


location

坐标点


businessarea

poi 所在商圈名称


aois

aoi 信息列表

请求参数 extensions 为 all 时返回如下内容


aoi

aoi 信息



id

所属 aoi 的 id


name

所属 aoi 名称


adcode

所属 aoi 所在区域编码


location

所属 aoi 中心点坐标


area

所属 aoi 点面积

单位：平方米

distance

输入经纬度是否在 aoi 面之中

 0，代表在 aoi 内

其余整数代表距离 AOI 的距离

type

所属 aoi 类型



提示
部分返回值当返回值存在时，将以字符串类型返回；当返回值不存在时，则以数组类型返回。

服务示例
https://restapi.amap.com/v3/geocode/regeo?output=xml&location=116.310003,39.991957&key=<用户的key>&radius=1000&extensions=all 
参数

值

备注

必选

location

116.481488,39.990464
经纬度坐标

是

poitype

商务写字楼
支持传入 POI TYPECODE 及名称；支持传入多个 POI 类型，多值间用“|”分隔

否

radius

1000
查询 POI 的半径范围。取值范围：0~3000,单位：米

否

extensions


all
返回结果控制

否

roadlevel

0
可选值：1，当 roadlevel=1时，过滤非主干道路，仅输出主干道路数据

否

运行
说明
location(116.310003,39.991957) 是所需要转换的坐标点经纬度，radius（1000）为返回的附近 POI 的范围，单位：米，extensions(all)为返回的数据内容，output（XML）用于指定返回数据的格式，Key 是高德 Web 服务 Key。详细可以参考上方的请求参数说明。

地理编码匹配级别列表
匹配级别

示例

国家

中国

省

河北省、北京市

市

 宁波市  

区县

北京市朝阳区

 开发区  

 亦庄经济开发区  

 乡镇  

 回龙观镇  

 村庄  

 三元村  

 热点商圈  

 上海市黄浦区老西门  

 道路  

 北京市朝阳区阜通东大街  

 道路交叉路口  

 北四环西路辅路/善缘街  

 兴趣点  

 北京市朝阳区奥林匹克公园(南门)  

 门牌号  

 朝阳区阜通东大街6号  

 单元号  

 望京西园四区5号楼2单元  

 楼层  

 保留字段，建议兼容

 房间  

 保留字段，建议兼容

 公交地铁站点  

 海淀黄庄站 A1西北口  

 门址  （新增）

 北京市朝阳区阜荣街10号  

 小巷（新增）  

 保留字段，建议兼容

 住宅区（新增）  

 广西壮族自治区柳州市鱼峰区德润路华润凯旋门  

 未知  

 未确认级别的 POI  

 路径规划2.0
最后更新时间: 2025年11月12日
产品介绍
路线规划接口2.0是一类 Web API 接口服务，以 HTTP/HTTPS 形式提供了多种路线规划服务。支持驾车、公交、步行、骑行、电动车路线规划。

功能介绍 
驾车路线规划：开发者可根据起终点坐标检索符合条件的驾车路线规划方案，支持一次请求返回多条路线结果、支持传入多个途经点、支持传入车牌规避限行、支持根据不同业务场景设置不同的算路策略等。

步行路线规划：开发者可根据起终点坐标检索符合条件的步行路线规划方案。

公交路线规划：开发者可根据起终点坐标检索符合条件的公共交通路线规划方案，支持结合业务场景设置不同的公交换乘策略。

骑行路线规划：开发者可根据起终点坐标检索符合条件的骑行路线规划方案。

电动车路线规划：开发者可根据起终点坐标检索符合条件的电动车路线规划方案，与骑行略有不同的是会考虑限行等条件。

流量限制
服务调用量的限制请点击 这里 查阅。

使用说明
1
第一步
申请 【Web服务API】密钥（Key）
2
第二步
拼接 HTTP 请求 URL，第一步申请的 Key 需作为必填参数一同发送
3
第三步
接收 HTTP 请求返回的数据（JSON 或 XML 格式），解析数据
如无特殊声明，接口的输入参数和输出数据编码全部统一为 UTF-8。
成为开发者并创建 Key 
为了正常调用 Web 服务 API ，请先注册成为高德开放平台开发者，并申请 Web 服务的 key ，点击具体操作。

驾车路线规划
驾车路线规划 API 服务地址
URL

请求方式

https://restapi.amap.com/v5/direction/driving?parameters

GET，当参数过长导致请求失败时，需要使用 POST 方式请求

parameters 代表的参数包括必填参数和可选参数。所有参数均使用和号字符(&)进行分隔。下面的列表枚举了这些参数及其使用规则。
请求参数
参数名

含义

规则说明

是否必须

缺省值

key

高德Key

用户在高德地图官网申请 Web 服务 API 类型 Key

必填

无

origin

起点经纬度

经度在前，纬度在后，经度和纬度用","分割，经纬度小数点后不得超过6位。

必填

无

destination

目的地

经度在前，纬度在后，经度和纬度用","分割，经纬度小数点后不得超过6位。

必填

无

destination_type

终点的 poi 类别

当用户知道终点 POI 的类别时候，建议填充此值

否

无

origin_id

起点 POI ID

起点为 POI 时，建议填充此值，可提升路线规划准确性

可选

无

destination_id

目的地 POI ID

目的地为 POI 时，建议填充此值，可提升路径规划准确性

可选

无

strategy

驾车算路策略

0：速度优先（只返回一条路线），此路线不一定距离最短

1：费用优先（只返回一条路线），不走收费路段，且耗时最少的路线

2：常规最快（只返回一条路线）综合距离/耗时规划结果

32：默认，高德推荐，同高德地图APP默认

33：躲避拥堵

34：高速优先

35：不走高速

36：少收费

37：大路优先

38：速度最快

39：躲避拥堵＋高速优先

40：躲避拥堵＋不走高速

41：躲避拥堵＋少收费

42：少收费＋不走高速

43：躲避拥堵＋少收费＋不走高速

44：躲避拥堵＋大路优先

45：躲避拥堵＋速度最快

可选

32

waypoints

途经点

途径点坐标串，默认支持1个有序途径点。多个途径点坐标按顺序以英文分号;分隔。最大支持16个途经点。

可选

无

avoidpolygons

避让区域

区域避让，默认支持1个避让区域，每个区域最多可有16个顶点；多个区域坐标按顺序以英文竖线符号“|”分隔，如果是四边形则有四个坐标点，如果是五边形则有五个坐标点；最大支持32个避让区域。

每个避让区域不能超过81平方公里，否则避让区域会失效。

可选

无

plate

车牌号码

车牌号，如 京AHA322，支持6位传统车牌和7位新能源车牌，用于判断限行相关。

可选

无

cartype

车辆类型

0：普通燃油汽车

1：纯电动汽车

2：插电式混动汽车

可选

0

ferry

是否使用轮渡

0:使用渡轮

1:不使用渡轮 

可选

0

show_fields

返回结果控制

show_fields 用来筛选 response 结果中可选字段。show_fields的使用需要遵循如下规则：

1、具体可指定返回的字段类请见下方返回结果说明中的“show_fields”内字段类型；

2、多个字段间采用“,”进行分割；

3、show_fields 未设置时，只返回基础信息类内字段；

可选

空

sig

数字签名

请参考 数字签名获取和使用方法

可选

无

output

返回结果格式类型

可选值：JSON

可选

json

callback


回调函数

callback 值是用户定义的函数名称，此参数只在 output 参数设置为 JSON 时有效。

可选

无

服务示例
https://restapi.amap.com/v5/direction/driving?origin=116.434307,39.90909&destination=116.434446,39.90816&key=<用户的key>
参数

值

备注

必选

origin

116.481028,39.989643
起点经纬度，经度在前，纬度在后，经度和纬度用","分割，经纬度小数点后不得超过6位

是

destination

116.434446,39.90816
目的地，经度在前，纬度在后，经度和纬度用","分割，经纬度小数点后不得超过6位

是

destination_id

目的地 POI ID，目的地为 POI 时，建议填充此值，可提升路径规划准确性

否

运行
返回结果
名称

类型

说明

status

string

本次 API 访问状态，如果成功返回1，如果失败返回0。

info


string

访问状态值的说明，如果成功返回"ok"，失败返回错误原因，具体见 错误码说明。

infocode

string

返回状态说明,10000代表正确,详情参阅 info 状态表

count


string

路径规划方案总数

route

object

返回的规划方案列表


origin

string

起点经纬度

destination

string

终点经纬度

taxi_cost

string

预计出租车费用，单位：元

paths

object

算路方案详情



distance

string

方案距离，单位：米


restriction

string

0 代表限行已规避或未限行，即该路线没有限行路段

1 代表限行无法规避，即该线路有限行路段

steps

object

路线分段


instruction


string

行驶指示

orientation


string

进入道路方向

road_name


string

分段道路名称

step_distance


string

分段距离信息

注意以下字段如果需要返回，需要通过“show_fields”进行参数类设置。

show_fields

string

可选差异化结果返回


cost

object

设置后可返回方案所需时间及费用成本


duration

string

线路耗时，分段 step 中的耗时，单位：秒

tolls

string

此路线道路收费，单位：元，包括分段信息

toll_distance

string

收费路段里程，单位：米，包括分段信息

toll_road

string

主要收费道路

traffic_lights

string

方案中红绿灯个数，单位：个

tmcs

object

设置后可返回分段路况详情


tmc_status

string

路况信息，包括：未知、畅通、缓行、拥堵、严重拥堵

tmc_distance

string

从当前坐标点开始 step 中路况相同的距离

tmc_polyline

string

此段路况涉及的道路坐标点串，点间用","分隔


navi

object

设置后可返回详细导航动作指令


action

string

导航主要动作指令

assistant_action

string

导航辅助动作指令

cities

object

设置后可返回分段途径城市信息


adcode

string

途径区域编码

citycode

string

途径城市编码

city

string

途径城市名称

district

object

途径区县信息


name

string

途径区县名称

adcode

string

途径区县 adcode

polyline

string

设置后可返回分路段坐标点串，两点间用“;”分隔


静态地图
最后更新时间: 2024年09月25日
产品介绍
静态地图服务通过返回一张地图图片响应 HTTP 请求，使用户能够将高德地图以图片形式嵌入自己的网页中。用户可以指定请求的地图位置、图片大小、以及在地图上添加覆盖物，如标签、标注、折线、多边形。

静态地图在使用的过程中，需要遵守高德开放平台 《自定义地图服务协议》。

使用限制
 服务调用量的限制请点击 这里 查阅。  

使用说明
1
第一步
申请 【Web服务API】密钥（Key）
2
第二步
拼接 HTTP 请求 URL，第一步申请的 Key 需作为必填参数一同发送
3
第三步
接收 HTTP 请求返回的数据（JSON 或 XML 格式），解析数据
如无特殊声明，接口的输入参数和输出数据编码全部统一为 UTF-8。
成为开发者并创建 Key 
为了正常调用 Web 服务 API ，请先注册成为高德开放平台开发者，并申请 Web 服务的 key ，点击具体操作。

功能介绍

添加默认标签

添加自定义标签

添加标注

添加折线

添加多边形

调用高清图
服务示例
https://restapi.amap.com/v3/staticmap?location=116.481485,39.990464&zoom=10&size=750*300&markers=mid,,A:116.481485,39.990464&key=<用户的key>


请求参数及用法
服务地址
URL

请求方式

https://restapi.amap.com/v3/staticmap?parameters

GET

parameters 代表的参数包括必填参数和可选参数。所有参数均使用和号字符(&)进行分隔。下面的列表枚举了这些参数及其使用规则。
请求参数
参数名称

含义

规则说明

是否必填

默认值

key

用户唯一标识

用户在高德地图官网申请

必填

无

location

地图中心点

中心点坐标。

规则：经度和纬度用","分隔 经纬度小数点后不得超过6位。

部分条件必填

无

zoom

地图级别

地图缩放级别:[1,17]

必填

无

size

地图大小

图片宽度*图片高度。最大值为1024*1024

可选

400*400

scale

普通/高清

1:返回普通图；

2:调用高清图，图片高度和宽度都增加一倍，zoom 也增加一倍（当zoom 为最大值时，zoom 不再改变）。

可选

1

markers

标注

使用规则见 markers 详细说明，标注最大数10个

可选

无

labels

标签

使用规则见 labels 详细说明，标签最大数10个

可选

无

paths

折线

使用规则见 paths 详细说明，折线和多边形最大数4个

可选

无

traffic

交通路况标识

底图是否展现实时路况。 可选值： 0，不展现；1，展现。

可选

0

sig

数字签名

数字签名认证用户必填

可选

无


注：如果有标注/标签/折线等覆盖物，则中心点（location）和地图级别（zoom）可选填。当请求中无 location 值时，地图区域以包含请求中所有的标注/标签/折线的几何中心为中心点；如请求中无 zoom，地图区域以包含请求中所有的标注/标签/折线为准，系统计算出 zoom 值。

markers
格式：

markers=markersStyle1:location1;location2..|markersStyle2:location3;location4..|markersStyleN:locationN;locationM.. 
location 为经纬度信息，经纬度之间使用","分隔，不同的点使用";"分隔。 markersStyle 可以使用系统提供的样式，也可以使用自定义图片。


系统 markersStyle：size，color，label。

markersStyle（参数名称）

说明

默认值

size

可选值： small,mid,large

small

color

选值范围：[0x000000, 0xffffff]

例如：

0x000000 black,

0x008000 green,

0x800080 purple,

0xFFFF00 yellow,

0x0000FF blue,

0x808080 gray,

0xffa500 orange,

0xFF0000 red,

0xFFFFFF white

0xFC6054

label

[0-9]、[A-Z]、[单个中文字] 当 size 为 small 时，图片不展现标注名。

无


markers 示例

默认 markers：
https://restapi.amap.com/v3/staticmap?markers=mid,0xFF0000,A:116.37359,39.92437;116.47359,39.92437&key=您的key
自定义 markers 示例
提示
自定义markersStyle： -1，url，0。

-1表示为自定义图片，URL 为图片的网址。自定义图片只支持 PNG 格式。

https://restapi.amap.com/v3/staticmap?markers=-1,https://a.amap.com/jsapi_demos/static/demo-center/icons/poi-marker-default.png,0:116.37359,39.92437&key=您的key
labels
格式：

labels=labelsStyle1:location1;location2..|labelsStyle2:location3;location4..|labelsStyleN:locationN;locationM.. 
location 为经纬度信息，经纬度之间使用","分隔，不同的点使用";"分隔。


labelsStyle：label, font, bold, fontSize, fontColor, background。 各参数使用","分隔，如有默认值则可为空。

labelsStyle（参数名称）

说明

默认值

content

标签内容，字符最大数目为15

无

font

0：微软雅黑；

1：宋体；

2：Times New Roman;

3：Helvetica

0

bold

0：非粗体；

1：粗体

0

fontSize

字体大小，可选值[1,72]

10

fontColor

字体颜色，取值范围：[0x000000, 0xffffff]

0xFFFFFF

background

背景色，取值范围：[0x000000, 0xffffff]

0x5288d8


labels 示例：

https://restapi.amap.com/v3/staticmap?location=116.48482,39.94858&zoom=10&size=400*400&labels=朝阳公园,2,0,16,0xFFFFFF,0x008000:116.48482,39.94858&key=您的key
paths
格式：

paths=pathsStyle1:location1;location2..|pathsStyle2:location3;location4..|pathsStyleN:locationN;locationM.. 
location 为经纬度，经纬度之间使用","分隔，不同的点使用";"分隔。


pathsStyle：weight, color, transparency, fillcolor, fillTransparency。

pathsStyle（参数名称）

说明

默认值

weight

线条粗细。

可选值： [2,15]

5

color

折线颜色。 选值范围：[0x000000, 0xffffff]

例如：

0x000000 black,

0x008000 green,

0x800080 purple,

0xFFFF00 yellow,

0x0000FF blue,

0x808080 gray,

0xffa500 orange,

0xFF0000 red,

0xFFFFFF white

0x0000FF

transparency

透明度。

可选值[0,1]，小数后最多2位，0表示完全透明，1表示完全不透明。

1

fillcolor

多边形的填充颜色，此值不为空时折线封闭成多边形。取值规则同color

无

fillTransparency

填充面透明度。

可选值[0,1]，小数后最多2位，0表示完全透明，1表示完全不透明。

0.5


paths 示例：

https://restapi.amap.com/v3/staticmap?zoom=15&size=500*500&paths=10,0x0000ff,1,,:116.31604,39.96491;116.320816,39.966606;116.321785,39.966827;116.32361,39.966957&key=您的key