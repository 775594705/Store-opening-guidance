# API 契约草案

## 健康检查

```http
GET /api/health
```

## 阶段3新增：模型模拟字段

`POST /api/analysis` 响应新增 `model_insights`，用于承载可解释模型的补充说明，不影响已有 `total_score`、`level`、`dimensions` 字段。

```json
{
  "model_insights": {
    "version": "stage3_rules_v2_conservative",
    "disclaimer": "以下IRS与哈夫模型为基于公开POI数据和规则假设的模拟，不代表绝对预测结果。",
    "irs": {
      "name": "IRS零售饱和指数",
      "demand_estimate": 93.2,
      "supply_estimate": 4.8,
      "saturation_index": 0.05,
      "status": "仍有空间",
      "explanation": "用住宅、办公、学校、交通、商业和互补POI估算需求，用1000米竞品和部分商业/互补POI估算供给。"
    },
    "huff": {
      "name": "哈夫模型雏形",
      "capture_probability": 0.82,
      "target_attractiveness": 2.1,
      "competitor_attractiveness": 0.45,
      "explanation": "MVP先用客流代理、成本压力和竞品数量近似吸引力，仅用于相对比较。"
    },
    "calibration": {
      "name": "保守校准",
      "weighted_score": 72,
      "final_score": 68,
      "applied_caps": [
        {
          "max_total_score": 68,
          "reason": "500米内同品类竞品达到8家以上，短距离分流明显，总分封顶为68分。"
        }
      ],
      "data_confidence": {
        "level": "中",
        "observed_signal_count": 35,
        "has_cost_input": false,
        "explanation": "未填写租金和预算，成本项采用保守默认分。"
      },
      "explanation": "原始加权分为72分，因触发强竞争规则，最终分数调整为68分。"
    }
  }
}
```

响应：

```json
{
  "status": "ok",
  "service": "store-advisor-api"
}
```

## 创建分析

```http
POST /api/analysis
Content-Type: application/json
```

请求：

```json
{
  "city": "广州",
  "address": "天河区体育西路",
  "category": "奶茶店",
  "longitude": 113.321,
  "latitude": 23.131,
  "rent_monthly": 18000,
  "budget_monthly": 80000
}
```

响应：

```json
{
  "total_score": 72,
  "level": "谨慎推荐",
  "summary": "该位置客流潜力较好，但同品类竞争偏高。",
  "dimensions": [
    {
      "name": "客流潜力",
      "score": 78,
      "reason": "周边住宅、办公和交通设施较多。"
    }
  ],
  "next_actions": [
    "实地观察早晚高峰客流",
    "核实周边同品类竞品价格带"
  ],
  "location": {
    "formatted_address": "广东省广州市天河区体育西路",
    "longitude": 113.32157,
    "latitude": 23.13344,
    "province": "广东省",
    "city": "广州市",
    "district": "天河区",
    "adcode": "440106",
    "level": "道路"
  },
  "poi_summary": {
    "total_poi_count": 151,
    "competitor_count_500m": 4,
    "competitor_count_1000m": 4,
    "residential_poi_count": 25,
    "office_poi_count": 26,
    "transit_poi_count": 24,
    "school_poi_count": 1,
    "commercial_poi_count": 30,
    "complementary_poi_count": 27,
    "other_poi_count": 18
  },
  "poi_sample": []
}
```

## POI 预览搜索

```http
POST /api/pois/search
Content-Type: application/json
```

请求：

```json
{
  "city": "广州",
  "address": "天河区体育西路",
  "category": "奶茶店",
  "radius_meters": 1000,
  "pages": 1
}
```

响应：

```json
{
  "location": {
    "formatted_address": "广东省广州市天河区体育西路",
    "longitude": 113.32157,
    "latitude": 23.13344
  },
  "summary": {
    "total_poi_count": 151,
    "competitor_count_500m": 4,
    "residential_poi_count": 25,
    "office_poi_count": 26,
    "transit_poi_count": 24
  },
  "pois": [
    {
      "name": "示例POI",
      "category_group": "commercial",
      "distance_meters": 31
    }
  ]
}
```

实现说明：后端按餐饮、购物、生活服务、住宅、学校、交通、公司企业等类型分组请求高德周边搜索，再按 POI id 去重，避免单次综合搜索被最近的商业 POI 占满。

## 地图定位

```http
POST /api/map/geocode
Content-Type: application/json
```

请求：
```json
{
  "city": "广州",
  "address": "天河区体育西路"
}
```

响应：
```json
{
  "formatted_address": "广东省广州市天河区体育西路",
  "longitude": 113.32157,
  "latitude": 23.13344,
  "province": "广东省",
  "city": "广州市",
  "district": "天河区",
  "adcode": "440106",
  "level": "道路"
}
```

## 地点搜索

```http
POST /api/map/search
Content-Type: application/json
```

请求：
```json
{
  "city": "广州",
  "keywords": "天河区体育西路 天环广场"
}
```

响应：
```json
{
  "candidates": [
    {
      "id": "B0FFFA10A0",
      "name": "Apple 天环广场",
      "address": "天河路218号",
      "longitude": 113.325147,
      "latitude": 23.132054,
      "province": "广东省",
      "city": "广州市",
      "district": "天河区",
      "type_name": "购物服务;家电电子卖场;数码电子",
      "type_code": "060306",
      "source": "poi"
    }
  ]
}
```

实现说明：前端“搜索详细”优先使用该接口返回真实 POI 候选地点，用户选择候选后地图跳转到该 POI 坐标。若 POI 搜索无结果，后端会退回地理编码作为兜底候选。

## 静态地图代理

```http
GET /api/map/static?longitude=113.32157&latitude=23.13344&zoom=16&width=640&height=320
```

响应为 `image/png` 或高德返回的图片类型。前端只请求本地后端接口，高德 API Key 不进入浏览器代码。
