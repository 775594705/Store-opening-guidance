from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.schemas.analysis import LocationResolved
from app.services.amap import AmapApiError, AmapClient

router = APIRouter(tags=["maps"])


class MapGeocodeRequest(BaseModel):
    city: str = Field(..., min_length=1, examples=["广州"])
    address: str = Field(..., min_length=1, examples=["天河区体育西路"])


class MapSearchRequest(BaseModel):
    city: str = Field(..., min_length=1, examples=["广州"])
    keywords: str = Field(..., min_length=1, examples=["天河区天环广场"])


class MapSearchCandidate(BaseModel):
    id: str
    name: str
    address: str
    longitude: float
    latitude: float
    province: str | None = None
    city: str | None = None
    district: str | None = None
    type_name: str | None = None
    type_code: str | None = None
    source: str = "poi"


class MapSearchResponse(BaseModel):
    candidates: list[MapSearchCandidate]


@router.post("/map/geocode", response_model=LocationResolved)
def geocode_location(payload: MapGeocodeRequest) -> LocationResolved:
    settings = get_settings()
    try:
        with AmapClient(settings.amap_api_key) as client:
            result = client.geocode(city=payload.city.strip(), address=payload.address.strip())
    except AmapApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LocationResolved(**asdict(result))


@router.post("/map/search", response_model=MapSearchResponse)
def search_locations(payload: MapSearchRequest) -> MapSearchResponse:
    settings = get_settings()
    city = payload.city.strip()
    keywords = payload.keywords.strip()
    try:
        with AmapClient(settings.amap_api_key) as client:
            results = client.search_text(city=city, keywords=keywords)
            candidates = [
                MapSearchCandidate(**asdict(result), source="poi")
                for result in results
            ]
            if not candidates:
                geocoded = client.geocode(city=city, address=keywords)
                candidates = [
                    MapSearchCandidate(
                        id="",
                        name=geocoded.formatted_address,
                        address=geocoded.formatted_address,
                        longitude=geocoded.longitude,
                        latitude=geocoded.latitude,
                        province=geocoded.province,
                        city=geocoded.city,
                        district=geocoded.district,
                        type_name=geocoded.level,
                        type_code=None,
                        source="geocode",
                    )
                ]
    except AmapApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MapSearchResponse(candidates=candidates)


@router.get("/map/static")
def get_static_map(
    longitude: float = Query(..., ge=-180, le=180),
    latitude: float = Query(..., ge=-90, le=90),
    zoom: int = Query(16, ge=3, le=19),
    width: int = Query(640, ge=64, le=1024),
    height: int = Query(320, ge=64, le=1024),
) -> Response:
    settings = get_settings()
    try:
        with AmapClient(settings.amap_api_key) as client:
            image_bytes, media_type = client.static_map(
                longitude=longitude,
                latitude=latitude,
                zoom=zoom,
                width=width,
                height=height,
            )
    except AmapApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(
        content=image_bytes,
        media_type=media_type,
        headers={"Cache-Control": "no-store"},
    )
