from typing import Any, Optional

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    city: str = Field(..., examples=["广州"])
    address: Optional[str] = Field(default=None, examples=["天河区体育西路"])
    category: str = Field(..., examples=["奶茶店"])
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    radius_meters: int = Field(default=1000, ge=100, le=50000)
    rent_monthly: Optional[float] = None
    budget_monthly: Optional[float] = None

    # MVP 阶段允许前端或调试工具直接传入统计值；接入高德后由后端自动计算。
    competitor_count_500m: int = 0
    competitor_count_1000m: int = 0
    residential_poi_count: int = 0
    office_poi_count: int = 0
    school_poi_count: int = 0
    transit_poi_count: int = 0
    commercial_poi_count: int = 0
    complementary_poi_count: int = 0


class DimensionScore(BaseModel):
    name: str
    score: int
    reason: str


class LocationResolved(BaseModel):
    formatted_address: str
    longitude: float
    latitude: float
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    adcode: Optional[str] = None
    level: Optional[str] = None


class PoiPreview(BaseModel):
    id: str
    name: str
    type_name: str
    type_code: str
    address: str
    category_group: str
    distance_meters: Optional[int] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None


class PoiSearchRequest(BaseModel):
    city: str = Field(..., examples=["广州"])
    category: str = Field(..., examples=["奶茶店"])
    address: Optional[str] = Field(default=None, examples=["天河区体育西路"])
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    radius_meters: int = Field(default=1000, ge=100, le=50000)
    pages: int = Field(default=2, ge=1, le=10)


class PoiSearchResponse(BaseModel):
    location: Optional[LocationResolved] = None
    summary: dict[str, int]
    pois: list[PoiPreview]


class AnalysisResponse(BaseModel):
    total_score: int
    level: str
    summary: str
    dimensions: list[DimensionScore]
    next_actions: list[str]
    location: Optional[LocationResolved] = None
    poi_summary: Optional[dict[str, int]] = None
    poi_sample: list[PoiPreview] = []
    model_insights: dict[str, Any] = Field(default_factory=dict)
