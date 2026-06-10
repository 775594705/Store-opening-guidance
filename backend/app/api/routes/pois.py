from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.schemas.analysis import PoiPreview, PoiSearchRequest, PoiSearchResponse
from app.services.amap import AmapApiError
from app.services.poi_analysis import collect_pois_for_analysis

router = APIRouter(tags=["pois"])


@router.post("/pois/search", response_model=PoiSearchResponse)
def search_pois(payload: PoiSearchRequest) -> PoiSearchResponse:
    settings = get_settings()
    try:
        result = collect_pois_for_analysis(
            settings=settings,
            city=payload.city,
            category=payload.category,
            address=payload.address,
            longitude=payload.longitude,
            latitude=payload.latitude,
            radius_meters=payload.radius_meters,
            pages=payload.pages,
        )
    except (AmapApiError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    public = result.to_public_dict()
    return PoiSearchResponse(
        location=public["location"],
        summary=public["summary"],
        pois=[PoiPreview(**item) for item in public["pois"]],
    )
