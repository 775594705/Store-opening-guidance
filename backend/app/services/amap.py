from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Optional

import httpx


GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
PLACE_AROUND_URL = "https://restapi.amap.com/v3/place/around"
PLACE_TEXT_URL = "https://restapi.amap.com/v3/place/text"
STATIC_MAP_URL = "https://restapi.amap.com/v3/staticmap"


class AmapApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeocodingResult:
    formatted_address: str
    longitude: float
    latitude: float
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    adcode: Optional[str] = None
    level: Optional[str] = None


@dataclass(frozen=True)
class PoiItem:
    id: str
    name: str
    type_name: str
    type_code: str
    address: str
    category_group: str
    distance_meters: Optional[int] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None


@dataclass(frozen=True)
class PlaceSearchResult:
    id: str
    name: str
    address: str
    longitude: float
    latitude: float
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    type_name: Optional[str] = None
    type_code: Optional[str] = None


class AmapClient:
    def __init__(self, api_key: str, http_client: Optional[httpx.Client] = None) -> None:
        if not api_key:
            raise AmapApiError("AMAP_API_KEY is not configured")
        self.api_key = api_key
        self._client = http_client or httpx.Client(timeout=10.0)
        self._owns_client = http_client is None

    def __enter__(self) -> "AmapClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def geocode(self, city: str, address: str) -> GeocodingResult:
        data = self._get(
            GEOCODE_URL,
            {
                "key": self.api_key,
                "address": address,
                "city": city,
                "output": "JSON",
            },
        )
        geocodes = data.get("geocodes") or []
        if not geocodes:
            raise AmapApiError(f"No geocoding result for address: {address}")

        item = geocodes[0]
        longitude, latitude = _parse_location(item.get("location", ""))
        return GeocodingResult(
            formatted_address=item.get("formatted_address") or address,
            longitude=longitude,
            latitude=latitude,
            province=_empty_to_none(item.get("province")),
            city=_empty_to_none(item.get("city")),
            district=_empty_to_none(item.get("district")),
            adcode=_empty_to_none(item.get("adcode")),
            level=_empty_to_none(item.get("level")),
        )

    def search_around(
        self,
        longitude: float,
        latitude: float,
        radius_meters: int,
        *,
        category: str,
        city: Optional[str] = None,
        keywords: Optional[str] = None,
        types: Optional[str] = None,
        pages: int = 2,
        offset: int = 25,
    ) -> list[PoiItem]:
        items: list[PoiItem] = []
        safe_pages = max(1, min(pages, 10))
        safe_offset = max(1, min(offset, 25))
        safe_radius = max(1, min(radius_meters, 50000))

        for page in range(1, safe_pages + 1):
            params = {
                "key": self.api_key,
                "location": f"{longitude:.6f},{latitude:.6f}",
                "radius": str(safe_radius),
                "page": str(page),
                "offset": str(safe_offset),
                "extensions": "base",
                "sortrule": "distance",
                "output": "JSON",
            }
            if city:
                params["city"] = city
            if keywords:
                params["keywords"] = keywords
            if types:
                params["types"] = types

            data = self._get(PLACE_AROUND_URL, params)
            pois = data.get("pois") or []
            if not pois:
                break
            items.extend(_parse_poi(raw, category) for raw in pois)

        return items

    def search_text(
        self,
        *,
        city: str,
        keywords: str,
        limit: int = 8,
    ) -> list[PlaceSearchResult]:
        safe_limit = max(1, min(limit, 20))
        data = self._get(
            PLACE_TEXT_URL,
            {
                "key": self.api_key,
                "keywords": keywords,
                "city": city,
                "citylimit": "true",
                "offset": str(safe_limit),
                "page": "1",
                "extensions": "base",
                "output": "JSON",
            },
        )
        pois = data.get("pois") or []
        results: list[PlaceSearchResult] = []
        for raw in pois:
            longitude, latitude = _parse_location(raw.get("location", ""), allow_empty=True)
            if longitude is None or latitude is None:
                continue
            results.append(
                PlaceSearchResult(
                    id=raw.get("id") or "",
                    name=raw.get("name") or keywords,
                    address=_normalize_address(raw.get("address")),
                    longitude=longitude,
                    latitude=latitude,
                    province=_empty_to_none(raw.get("pname")),
                    city=_empty_to_none(raw.get("cityname")),
                    district=_empty_to_none(raw.get("adname")),
                    type_name=_empty_to_none(raw.get("type")),
                    type_code=_empty_to_none(raw.get("typecode")),
                )
            )
        return results

    def static_map(
        self,
        longitude: float,
        latitude: float,
        *,
        zoom: int = 16,
        width: int = 640,
        height: int = 320,
    ) -> tuple[bytes, str]:
        response = self._client.get(
            STATIC_MAP_URL,
            params={
                "key": self.api_key,
                "location": f"{longitude:.6f},{latitude:.6f}",
                "zoom": str(zoom),
                "size": f"{width}*{height}",
                "markers": f"mid,,A:{longitude:.6f},{latitude:.6f}",
            },
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if content_type.startswith("image/"):
            media_type = content_type.split(";", 1)[0]
            return response.content, media_type

        try:
            data = response.json()
            info = data.get("info") or "Unknown Amap static map error"
            info_code = data.get("infocode") or "unknown"
            raise AmapApiError(f"{info} ({info_code})")
        except ValueError as exc:
            message = (response.text or "Amap static map request failed").strip()
            raise AmapApiError(message[:200]) from exc

    def _get(self, url: str, params: dict[str, str]) -> dict:
        for attempt in range(3):
            response = self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "1":
                return data

            info = data.get("info") or "Unknown Amap API error"
            info_code = data.get("infocode") or "unknown"
            if info_code == "10021" and attempt < 2:
                sleep(0.8 * (attempt + 1))
                continue
            raise AmapApiError(f"{info} ({info_code})")

        raise AmapApiError("Amap request failed after retries")


def summarize_pois(pois: list[PoiItem]) -> dict[str, int]:
    summary = {
        "total_poi_count": len(pois),
        "competitor_count_500m": 0,
        "competitor_count_1000m": 0,
        "residential_poi_count": 0,
        "office_poi_count": 0,
        "transit_poi_count": 0,
        "school_poi_count": 0,
        "commercial_poi_count": 0,
        "complementary_poi_count": 0,
        "other_poi_count": 0,
    }
    for poi in pois:
        group_key = f"{poi.category_group}_poi_count"
        if group_key in summary:
            summary[group_key] += 1
        else:
            summary["other_poi_count"] += 1

        if poi.category_group == "competitor":
            distance = poi.distance_meters
            if distance is not None and distance <= 500:
                summary["competitor_count_500m"] += 1
            if distance is not None and distance <= 1000:
                summary["competitor_count_1000m"] += 1
    return summary


def classify_poi(category: str, name: str, type_name: str, type_code: str) -> str:
    text = f"{category} {name} {type_name} {type_code}".lower()
    if _is_competitor(category, name, type_name):
        return "competitor"
    if any(word in text for word in ["住宅", "小区", "公寓", "宿舍"]) or type_code.startswith("120"):
        return "residential"
    if any(word in text for word in ["写字楼", "产业园", "公司", "企业", "办公"]) or type_code.startswith("170"):
        return "office"
    if any(word in text for word in ["地铁", "公交", "停车", "火车", "机场"]) or type_code.startswith("150"):
        return "transit"
    if any(word in text for word in ["学校", "大学", "学院", "幼儿园"]) or type_code.startswith("141"):
        return "school"
    if any(word in text for word in ["商场", "购物", "商业", "步行街"]) or type_code.startswith("060"):
        return "commercial"
    if type_code.startswith(("050", "070", "080")):
        return "complementary"
    return "other"


def _parse_poi(raw: dict, category: str) -> PoiItem:
    longitude, latitude = _parse_location(raw.get("location", ""), allow_empty=True)
    type_name = raw.get("type") or ""
    type_code = raw.get("typecode") or ""
    name = raw.get("name") or ""
    distance = _parse_int(raw.get("distance"))
    return PoiItem(
        id=raw.get("id") or "",
        name=name,
        type_name=type_name,
        type_code=type_code,
        address=_normalize_address(raw.get("address")),
        category_group=classify_poi(category, name, type_name, type_code),
        distance_meters=distance,
        longitude=longitude,
        latitude=latitude,
    )


def _is_competitor(category: str, name: str, type_name: str) -> bool:
    haystack = f"{name} {type_name}".lower()
    keywords_by_category = {
        "奶茶": ["奶茶", "茶饮", "饮品", "甜品", "喜茶", "奈雪", "霸王茶姬", "蜜雪", "茶百道", "古茗", "沪上阿姨", "书亦"],
        "咖啡": ["咖啡", "星巴克", "瑞幸", "manner", "costa", "seesaw"],
        "美甲": ["美甲", "美睫", "美业"],
        "火锅": ["火锅", "串串", "麻辣烫"],
        "小吃": ["小吃", "炸鸡", "烧烤", "卤味", "快餐"],
    }
    matched_keywords = []
    for key, keywords in keywords_by_category.items():
        if key in category:
            matched_keywords.extend(keywords)
    if not matched_keywords:
        matched_keywords.append(category)
    return any(keyword.lower() in haystack for keyword in matched_keywords)


def _parse_location(value: str, *, allow_empty: bool = False) -> tuple[Optional[float], Optional[float]]:
    if not value:
        if allow_empty:
            return None, None
        raise AmapApiError("Amap response is missing location")
    parts = value.split(",")
    if len(parts) != 2:
        raise AmapApiError(f"Invalid Amap location value: {value}")
    return float(parts[0]), float(parts[1])


def _parse_int(value) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _empty_to_none(value) -> Optional[str]:
    if value in (None, "", []):
        return None
    return str(value)


def _normalize_address(value) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    if value is None:
        return ""
    return str(value)
