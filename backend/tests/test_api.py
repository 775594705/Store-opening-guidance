import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.amap import GeocodingResult, PlaceSearchResult


class FakeAmapClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def geocode(self, city, address):
        return GeocodingResult(
            formatted_address=f"{city}{address}",
            longitude=113.321,
            latitude=23.131,
            province="Guangdong",
            city=city,
            district="Tianhe",
            adcode="440106",
            level="road",
        )

    def search_text(self, *, city, keywords, limit=8):
        return [
            PlaceSearchResult(
                id="poi-1",
                name="IFC Mall",
                address="Century Avenue",
                longitude=121.507,
                latitude=31.234,
                province="Shanghai",
                city=city,
                district="Pudong",
                type_name="shopping",
                type_code="060101",
            )
        ]

    def static_map(self, longitude, latitude, *, zoom=16, width=640, height=320):
        return b"fake-map-image", "image/png"


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_analysis_supports_manual_poi_signals(self):
        response = self.client.post(
            "/api/analysis",
            json={
                "city": "广州",
                "address": "天河区体育西路",
                "category": "奶茶店",
                "competitor_count_500m": 3,
                "competitor_count_1000m": 8,
                "residential_poi_count": 12,
                "office_poi_count": 10,
                "transit_poi_count": 4,
                "complementary_poi_count": 8,
                "rent_monthly": 18000,
                "budget_monthly": 80000,
            },
        )

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["level"], "谨慎推荐")
        self.assertEqual(data["total_score"], 60)
        self.assertEqual(data["poi_sample"], [])
        self.assertIn("irs", data["model_insights"])
        self.assertIn("huff", data["model_insights"])
        self.assertIn("calibration", data["model_insights"])

    @patch("app.api.routes.maps.AmapClient", FakeAmapClient)
    def test_map_geocode(self):
        response = self.client.post(
            "/api/map/geocode",
            json={"city": "Guangzhou", "address": "Tiyu West Road"},
        )

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["longitude"], 113.321)
        self.assertEqual(data["latitude"], 23.131)
        self.assertEqual(data["district"], "Tianhe")

    @patch("app.api.routes.maps.AmapClient", FakeAmapClient)
    def test_static_map(self):
        response = self.client.get(
            "/api/map/static",
            params={"longitude": 113.321, "latitude": 23.131},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(response.content, b"fake-map-image")

    @patch("app.api.routes.maps.AmapClient", FakeAmapClient)
    def test_map_search_returns_candidates(self):
        response = self.client.post(
            "/api/map/search",
            json={"city": "Shanghai", "keywords": "IFC Mall"},
        )

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["candidates"][0]["name"], "IFC Mall")
        self.assertEqual(data["candidates"][0]["longitude"], 121.507)
        self.assertEqual(data["candidates"][0]["source"], "poi")


if __name__ == "__main__":
    unittest.main()
