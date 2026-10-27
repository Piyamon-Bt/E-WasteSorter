"""Photo validation and physical (external) assessment.

Images are processed in memory only. Before any provider call they are
re-encoded as JPEG and downscaled, which also strips EXIF metadata such as GPS.
"""

import io
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

from ..config import Settings
from ..providers import mock_provider, openai_provider
from ..schemas.physical import (
    DETAIL_VIEW,
    REQUIRED_VIEWS,
    FollowUpResult,
    ImageQualityIssue,
    Observation,
    PhysicalAssessment,
)

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
TOO_DARK_MEAN = 25
TOO_BRIGHT_MEAN = 240
BLUR_EDGE_STDDEV = 6.0  # heuristic; only produces a warning

Image.MAX_IMAGE_PIXELS = 60_000_000  # refuse decompression bombs


@dataclass
class UploadedImage:
    view: str
    filename: str
    data: bytes


@dataclass
class PreparedImage:
    view: str
    data: bytes  # re-encoded JPEG


def check_image(img: UploadedImage, settings: Settings) -> tuple[PreparedImage | None, list[ImageQualityIssue]]:
    def issue(problem: str, blocking: bool = True) -> ImageQualityIssue:
        return ImageQualityIssue(view=img.view, filename=img.filename, problem=problem, blocking=blocking)

    max_bytes = int(settings.max_upload_mb * 1024 * 1024)
    if len(img.data) > max_bytes:
        return None, [issue(f"The file is larger than {settings.max_upload_mb:g} MB. Upload a smaller photo.")]
    try:
        image = Image.open(io.BytesIO(img.data))
        fmt = image.format
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return None, [issue("The file could not be read as an image. Upload a JPG, PNG or WebP photo.")]
    if fmt not in ALLOWED_FORMATS:
        return None, [issue(f"{fmt or 'This'} format is not supported. Use JPG, PNG or WebP.")]

    image = ImageOps.exif_transpose(image)
    width, height = image.size
    if min(width, height) < settings.min_image_side_px:
        return None, [
            issue(
                f"The photo is too small ({width}×{height} px). Use a photo at least "
                f"{settings.min_image_side_px} px on its shortest side so details are visible."
            )
        ]

    gray = image.convert("L")
    gray.thumbnail((512, 512))
    brightness = ImageStat.Stat(gray).mean[0]
    if brightness < TOO_DARK_MEAN:
        return None, [issue("The photo is too dark to see the device. Retake it in better light.")]
    if brightness > TOO_BRIGHT_MEAN:
        return None, [issue("The photo is overexposed or washed out. Retake it without direct glare.")]

    issues = []
    edges = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).stddev[0]
    if edges < BLUR_EDGE_STDDEV:
        issues.append(issue("The photo may be blurry. If details are hard to see, retake it.", blocking=False))

    rgb = image.convert("RGB")
    rgb.thumbnail((settings.api_image_max_side_px, settings.api_image_max_side_px))
    out = io.BytesIO()
    rgb.save(out, format="JPEG", quality=85)
    return PreparedImage(view=img.view, data=out.getvalue()), issues


def check_slots(device_type: str, images: list[UploadedImage], max_images: int) -> list[str]:
    """Returns blocking slot problems: missing required views, duplicates, unknown slots."""
    required = REQUIRED_VIEWS[device_type]
    problems = []
    if len(images) > max_images:
        problems.append(f"Too many photos: upload at most {max_images} per request.")
    views = [i.view for i in images]
    for view in views:
        if view not in required and view != DETAIL_VIEW:
            problems.append(f"Unknown photo slot “{view}”.")
    for view, label in required.items():
        count = views.count(view)
        if count == 0:
            problems.append(f"Missing required view: {label}.")
        elif count > 1:
            problems.append(f"Assign only one photo to “{label}”. Use Additional detail for extra photos.")
    return problems


def prepare_images(
    device_type: str, images: list[UploadedImage], settings: Settings
) -> tuple[list[PreparedImage], list[str], list[ImageQualityIssue]]:
    slot_problems = check_slots(device_type, images, settings.max_images_per_request)
    prepared, issues = [], []
    for img in images:
        ready, img_issues = check_image(img, settings)
        issues.extend(img_issues)
        if ready:
            prepared.append(ready)
    return prepared, slot_problems, issues


def assess_physical(
    settings: Settings, assessment_id: str, device_type: str, images: list[PreparedImage], scenario: str | None
) -> PhysicalAssessment:
    views = [i.view for i in images]
    if settings.is_mock:
        return mock_provider.assess_physical(device_type, views, mock_provider.resolve_scenario(scenario))
    provider = openai_provider.create()
    observations, unassessable, identity, summary = provider.assess_physical(
        assessment_id, device_type, [(i.view, i.data) for i in images]
    )
    return PhysicalAssessment(
        source="live",
        model=provider.model,
        device_type=device_type,
        observations=observations,
        unassessable_areas=unassessable,
        identity=identity,
        summary=summary,
    )


def follow_up(
    settings: Settings,
    assessment_id: str,
    device_type: str,
    observation: Observation,
    response: str,
    note: str,
    originals: list[PreparedImage],
    extras: list[PreparedImage],
) -> FollowUpResult:
    if settings.is_mock:
        return mock_provider.follow_up(observation, response, len(extras))
    provider = openai_provider.create()
    images = [(f"original {i.view}", i.data) for i in originals] + [
        (f"new photo {n + 1}", i.data) for n, i in enumerate(extras)
    ]
    parsed = provider.follow_up(assessment_id, device_type, observation, response, note, images)
    revised = None
    if parsed.outcome == "revised" and parsed.revised_observation is not None:
        data = parsed.revised_observation.model_dump()
        data["views"] = [v for v in data["views"] if v in observation.views] or observation.views
        revised = Observation(id=observation.id, **{k: v for k, v in data.items() if k != "id"})
    if parsed.outcome == "not_supported" and not extras:
        # Clearing an observation needs new evidence, not just a re-read of the same photos.
        parsed.outcome = "unresolved"
    return FollowUpResult(
        observation_id=observation.id,
        outcome=parsed.outcome if parsed.outcome != "revised" or revised else "unresolved",
        revised_observation=revised,
        explanation=parsed.explanation,
        extra_images=len(extras),
        source="live",
        model=provider.model,
    )

