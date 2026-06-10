from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, DimensionScore
from app.schemas.analysis import PoiPreview
from app.services.amap import AmapApiError
from app.services.llm_report import build_rule_based_summary
from app.services.poi_analysis import collect_pois_for_analysis, signals_from_poi_summary
from app.services.scoring import LocationSignals, score_location

router = APIRouter(tags=["analysis"])


@router.post("/analysis", response_model=AnalysisResponse)
def create_analysis(payload: AnalysisRequest) -> AnalysisResponse:
    poi_public = {"location": None, "summary": None, "pois": []}
    if _has_manual_signals(payload):
        signals = _manual_signals(payload)
    else:
        settings = get_settings()
        try:
            poi_result = collect_pois_for_analysis(
                settings=settings,
                city=payload.city,
                category=payload.category,
                address=payload.address,
                longitude=payload.longitude,
                latitude=payload.latitude,
                radius_meters=payload.radius_meters,
                pages=2,
            )
        except (AmapApiError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        poi_public = poi_result.to_public_dict(sample_size=200)
        signals = signals_from_poi_summary(
            category=payload.category,
            summary=poi_result.summary,
            rent_monthly=payload.rent_monthly,
            budget_monthly=payload.budget_monthly,
        )

    result = score_location(signals)
    summary = build_rule_based_summary(payload.category, result)
    return AnalysisResponse(
        total_score=result["total_score"],
        level=result["level"],
        summary=summary,
        dimensions=[DimensionScore(**item) for item in result["dimensions"]],
        next_actions=result["next_actions"],
        location=poi_public["location"],
        poi_summary=poi_public["summary"],
        poi_sample=[PoiPreview(**item) for item in poi_public["pois"]],
        model_insights=result["model_insights"],
    )


def _has_manual_signals(payload: AnalysisRequest) -> bool:
    return any(
        [
            payload.competitor_count_500m,
            payload.competitor_count_1000m,
            payload.residential_poi_count,
            payload.office_poi_count,
            payload.school_poi_count,
            payload.transit_poi_count,
            payload.commercial_poi_count,
            payload.complementary_poi_count,
        ]
    )


def _manual_signals(payload: AnalysisRequest) -> LocationSignals:
    return LocationSignals(
        category=payload.category,
        competitor_count_500m=payload.competitor_count_500m,
        competitor_count_1000m=payload.competitor_count_1000m,
        residential_poi_count=payload.residential_poi_count,
        office_poi_count=payload.office_poi_count,
        school_poi_count=payload.school_poi_count,
        transit_poi_count=payload.transit_poi_count,
        commercial_poi_count=payload.commercial_poi_count,
        complementary_poi_count=payload.complementary_poi_count,
        rent_monthly=payload.rent_monthly,
        budget_monthly=payload.budget_monthly,
    )
