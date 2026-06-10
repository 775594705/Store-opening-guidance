from __future__ import annotations

from dataclasses import asdict, dataclass
from time import sleep

from app.core.config import Settings
from app.services.amap import AmapClient, GeocodingResult, PoiItem, summarize_pois
from app.services.scoring import LocationSignals


ANALYSIS_TYPE_GROUPS = (
    "050000",
    "060000",
    "070000",
    "120000",
    "141000",
    "150000",
    "170000",
)


@dataclass(frozen=True)
class PoiCollectionResult:
    location: GeocodingResult | None
    pois: list[PoiItem]
    summary: dict[str, int]

    def to_public_dict(self, *, sample_size: int = 20) -> dict:
        return {
            "location": asdict(self.location) if self.location else None,
            "summary": self.summary,
            "pois": [asdict(poi) for poi in self.pois[:sample_size]],
        }


def collect_pois_for_analysis(
    *,
    settings: Settings,
    city: str,
    category: str,
    address: str | None = None,
    longitude: float | None = None,
    latitude: float | None = None,
    radius_meters: int | None = None,
    pages: int = 2,
) -> PoiCollectionResult:
    radius = radius_meters or settings.default_search_radius_meters
    location: GeocodingResult | None = None

    with AmapClient(settings.amap_api_key) as client:
        if longitude is None or latitude is None:
            if not address:
                raise ValueError("address or longitude/latitude is required")
            location = client.geocode(city=city, address=address)
            longitude = location.longitude
            latitude = location.latitude
        else:
            location = GeocodingResult(
                formatted_address=address or "地图选点",
                longitude=longitude,
                latitude=latitude,
                city=city,
                level="地图选点",
            )

        pois = _search_by_type_groups(
            client=client,
            longitude=longitude,
            latitude=latitude,
            radius_meters=radius,
            category=category,
            city=city,
            pages=pages,
        )
    return PoiCollectionResult(location=location, pois=pois, summary=summarize_pois(pois))


def signals_from_poi_summary(
    *,
    category: str,
    summary: dict[str, int],
    rent_monthly: float | None,
    budget_monthly: float | None,
) -> LocationSignals:
    return LocationSignals(
        category=category,
        competitor_count_500m=summary.get("competitor_count_500m", 0),
        competitor_count_1000m=summary.get("competitor_count_1000m", 0),
        residential_poi_count=summary.get("residential_poi_count", 0),
        office_poi_count=summary.get("office_poi_count", 0),
        school_poi_count=summary.get("school_poi_count", 0),
        transit_poi_count=summary.get("transit_poi_count", 0),
        commercial_poi_count=summary.get("commercial_poi_count", 0),
        complementary_poi_count=summary.get("complementary_poi_count", 0),
        rent_monthly=rent_monthly,
        budget_monthly=budget_monthly,
    )


def _search_by_type_groups(
    *,
    client: AmapClient,
    longitude: float,
    latitude: float,
    radius_meters: int,
    category: str,
    city: str,
    pages: int,
) -> list[PoiItem]:
    pois_by_key: dict[str, PoiItem] = {}
    for type_group in ANALYSIS_TYPE_GROUPS:
        sleep(0.25)
        for poi in client.search_around(
            longitude=longitude,
            latitude=latitude,
            radius_meters=radius_meters,
            category=category,
            city=city,
            types=type_group,
            pages=pages,
        ):
            key = poi.id or f"{poi.name}|{poi.longitude}|{poi.latitude}"
            pois_by_key[key] = poi
    return sorted(
        pois_by_key.values(),
        key=lambda poi: poi.distance_meters if poi.distance_meters is not None else 999999,
    )
