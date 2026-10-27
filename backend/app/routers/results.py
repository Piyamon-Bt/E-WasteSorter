from fastapi import APIRouter, Header
from fastapi.responses import PlainTextResponse

from ..config import get_settings
from ..schemas.market import PriceRequest, PriceResearch, ServicesRequest, ServicesResult
from ..schemas.recommendation import AssessmentSnapshot, RecommendationResult, ReportRequest
from ..services import local_services, price_research, recommendations, report_export

router = APIRouter(prefix="/api", tags=["results"])


@router.post("/market/prices", response_model=PriceResearch)
def prices(
    req: PriceRequest,
    x_assessment_id: str = Header(..., min_length=8, max_length=64),
    x_mock_scenario: str | None = Header(None),
):
    return price_research.research(get_settings(), x_assessment_id, req, x_mock_scenario)


@router.post("/services/nearby", response_model=ServicesResult)
def nearby(
    req: ServicesRequest,
    x_assessment_id: str = Header(..., min_length=8, max_length=64),
    x_mock_scenario: str | None = Header(None),
):
    return local_services.find(get_settings(), x_assessment_id, req, x_mock_scenario)


@router.post("/recommendations", response_model=RecommendationResult)
def recommend(snapshot: AssessmentSnapshot):
    return recommendations.recommend(snapshot)


@router.post("/report", response_class=PlainTextResponse)
def report(req: ReportRequest):
    text = report_export.build_report(req.snapshot, req.recommendation)
    return PlainTextResponse(
        text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ewaste-assessment-report.md"'},
    )
