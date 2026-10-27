from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import ValidationError

from ..config import get_settings
from ..providers.errors import ProviderError
from ..schemas.common import DeviceType
from ..schemas.functional import EvaluateRequest, FunctionalEvaluation, FunctionalPlan, PlanRequest
from ..schemas.physical import FollowUpResult, Observation, PhysicalAssessment, UserResponse
from ..services import functional_checks, image_assessment
from ..services.image_assessment import UploadedImage

router = APIRouter(prefix="/api", tags=["assessment"])


async def _read(files: list[UploadFile], views: list[str]) -> list[UploadedImage]:
    if len(files) != len(views):
        raise HTTPException(422, {"message": "Each photo must be assigned to exactly one view slot."})
    images = []
    try:
        for f, view in zip(files, views):
            images.append(UploadedImage(view=view, filename=f.filename or "photo", data=await f.read()))
    finally:
        for f in files:
            await f.close()  # releases any temporary spool file
    return images


def _provider_http_error(exc: ProviderError, step: str) -> HTTPException:
    status = {"not_configured": 503, "budget_limit": 429, "quota": 429, "timeout": 504}.get(exc.code, 502)
    return HTTPException(status, {"message": exc.message, "issue": exc.to_issue(step).model_dump()})


@router.post("/assessments/physical", response_model=PhysicalAssessment)
async def physical_assessment(
    device_type: DeviceType = Form(...),
    views: list[str] = Form(...),
    files: list[UploadFile] = File(...),
    x_assessment_id: str = Header(..., min_length=8, max_length=64),
    x_mock_scenario: str | None = Header(None),
):
    settings = get_settings()
    images = await _read(files, views)
    prepared, slot_problems, issues = image_assessment.prepare_images(device_type, images, settings)
    blocking = [i for i in issues if i.blocking]
    if slot_problems or blocking:
        raise HTTPException(
            422,
            {
                "message": "Some photos need attention before the analysis can start.",
                "slot_problems": slot_problems,
                "image_issues": [i.model_dump() for i in issues],
            },
        )
    try:
        return image_assessment.assess_physical(settings, x_assessment_id, device_type, prepared, x_mock_scenario)
    except ProviderError as exc:
        raise _provider_http_error(exc, "physical_assessment") from exc


@router.post("/assessments/follow-up", response_model=FollowUpResult)
async def follow_up(
    device_type: DeviceType = Form(...),
    observation: str = Form(..., description="The observation being reviewed, as JSON"),
    response: UserResponse = Form(...),
    note: str = Form(""),
    views: list[str] = Form([]),
    files: list[UploadFile] = File([]),
    x_assessment_id: str = Header(..., min_length=8, max_length=64),
):
    settings = get_settings()
    try:
        obs = Observation.model_validate_json(observation)
    except ValidationError as exc:
        raise HTTPException(422, {"message": "Invalid observation."}) from exc
    images = await _read(files, views)
    originals, extras, problems = [], [], []
    for img in images:
        ready, img_issues = image_assessment.check_image(img, settings)
        problems.extend(i for i in img_issues if i.blocking)
        if ready:
            (extras if img.view == "followup" else originals).append(ready)
    if problems:
        raise HTTPException(
            422,
            {"message": "Some photos could not be used.", "image_issues": [p.model_dump() for p in problems]},
        )
    try:
        return image_assessment.follow_up(
            settings, x_assessment_id, device_type, obs, response, note, originals, extras
        )
    except ProviderError as exc:
        raise _provider_http_error(exc, "follow_up") from exc


@router.post("/checks/plan", response_model=FunctionalPlan)
def check_plan(req: PlanRequest):
    return functional_checks.build_plan(req.device_type, req.observations, req.reviews)


@router.post("/checks/evaluate", response_model=FunctionalEvaluation)
def check_evaluate(req: EvaluateRequest):
    return functional_checks.evaluate(req.device_type, req.observations, req.reviews, req.responses)
