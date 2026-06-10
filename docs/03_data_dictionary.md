# 数据字典

## 位置分析输入

| 字段 | 类型 | 来源 | 说明 |
|---|---|---|---|
| city | string | 用户输入 | 城市 |
| address | string | 用户输入 | 候选地址 |
| longitude | number | 地图 API | 经度 |
| latitude | number | 地图 API | 纬度 |
| category | string | 用户输入 | 开店品类 |
| rent_monthly | number | 用户输入 | 月租金 |
| budget_monthly | number | 用户输入 | 可支配月预算 |

## POI 分类

| 分类 | 说明 | 示例 |
|---|---|---|
| competitor | 同品类竞品 | 奶茶店、咖啡店、美甲店 |
| residential | 居住区 | 小区、公寓 |
| office | 办公与产业 | 写字楼、产业园 |
| school | 学校 | 大学、中学、小学 |
| transit | 交通设施 | 地铁站、公交站、停车场 |
| commercial | 商业设施 | 商场、步行街、综合体 |
| complement | 互补业态 | 餐饮、影院、健身等 |

