import unittest

from app.services.amap import AmapClient, classify_poi, summarize_pois


class FakeResponse:
    def __init__(self, payload=None, *, content=b"", headers=None, text=""):
        self.payload = payload
        self.content = content
        self.headers = headers or {}
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        if self.payload is None:
            raise ValueError("No JSON payload")
        return self.payload


class FakeHttpClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []

    def get(self, url, params):
        self.requests.append((url, params))
        payload = self.payloads.pop(0)
        if isinstance(payload, FakeResponse):
            return payload
        return FakeResponse(payload)


class AmapClientTests(unittest.TestCase):
    def test_geocode_parses_location(self):
        client = AmapClient(
            "test-key",
            http_client=FakeHttpClient(
                [
                    {
                        "status": "1",
                        "geocodes": [
                            {
                                "formatted_address": "广东省广州市天河区体育西路",
                                "location": "113.321000,23.131000",
                                "province": "广东省",
                                "city": "广州市",
                                "district": "天河区",
                                "adcode": "440106",
                                "level": "道路",
                            }
                        ],
                    }
                ]
            ),
        )

        result = client.geocode(city="广州", address="天河区体育西路")

        self.assertEqual(result.longitude, 113.321)
        self.assertEqual(result.latitude, 23.131)
        self.assertEqual(result.district, "天河区")

    def test_search_around_parses_and_classifies_pois(self):
        client = AmapClient(
            "test-key",
            http_client=FakeHttpClient(
                [
                    {
                        "status": "1",
                        "pois": [
                            {
                                "id": "poi-1",
                                "name": "喜茶",
                                "type": "餐饮服务;冷饮店;冷饮店",
                                "typecode": "050700",
                                "address": "测试地址1",
                                "distance": "120",
                                "location": "113.320000,23.130000",
                            },
                            {
                                "id": "poi-2",
                                "name": "某某花园",
                                "type": "商务住宅;住宅区;住宅小区",
                                "typecode": "120300",
                                "address": "测试地址2",
                                "distance": "420",
                                "location": "113.322000,23.132000",
                            },
                        ],
                    },
                    {"status": "1", "pois": []},
                ]
            ),
        )

        pois = client.search_around(
            longitude=113.321,
            latitude=23.131,
            radius_meters=1000,
            category="奶茶店",
            pages=2,
        )
        summary = summarize_pois(pois)

        self.assertEqual(len(pois), 2)
        self.assertEqual(pois[0].category_group, "competitor")
        self.assertEqual(summary["competitor_count_500m"], 1)
        self.assertEqual(summary["residential_poi_count"], 1)

    def test_static_map_returns_image_bytes(self):
        http_client = FakeHttpClient(
            [
                FakeResponse(
                    content=b"fake-png",
                    headers={"content-type": "image/png"},
                )
            ]
        )
        client = AmapClient("test-key", http_client=http_client)

        image_bytes, media_type = client.static_map(
            longitude=113.321,
            latitude=23.131,
            zoom=16,
            width=640,
            height=320,
        )

        self.assertEqual(image_bytes, b"fake-png")
        self.assertEqual(media_type, "image/png")
        _, params = http_client.requests[0]
        self.assertEqual(params["location"], "113.321000,23.131000")
        self.assertEqual(params["size"], "640*320")
        self.assertEqual(params["markers"], "mid,,A:113.321000,23.131000")

    def test_search_text_parses_poi_candidates(self):
        http_client = FakeHttpClient(
            [
                {
                    "status": "1",
                    "pois": [
                        {
                            "id": "B001",
                            "name": "天环广场",
                            "type": "购物服务;商场;购物中心",
                            "typecode": "060101",
                            "address": "天河路218号",
                            "location": "113.324000,23.132000",
                            "pname": "广东省",
                            "cityname": "广州市",
                            "adname": "天河区",
                        }
                    ],
                }
            ]
        )
        client = AmapClient("test-key", http_client=http_client)

        results = client.search_text(city="广州", keywords="天河区天环广场")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "天环广场")
        self.assertEqual(results[0].longitude, 113.324)
        self.assertEqual(results[0].latitude, 23.132)
        _, params = http_client.requests[0]
        self.assertEqual(params["city"], "广州")
        self.assertEqual(params["citylimit"], "true")
        self.assertEqual(params["keywords"], "天河区天环广场")

    def test_classify_poi_detects_common_groups(self):
        self.assertEqual(classify_poi("咖啡店", "瑞幸咖啡", "餐饮服务", "050000"), "competitor")
        self.assertEqual(classify_poi("奶茶店", "地铁体育西路站", "交通设施服务", "150500"), "transit")
        self.assertEqual(classify_poi("美甲店", "甲天下美甲", "生活服务", "070000"), "competitor")


if __name__ == "__main__":
    unittest.main()
