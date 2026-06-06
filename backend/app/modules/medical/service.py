import json
import logging
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core import storage
from app.modules.medical import vision
from app.modules.medical.models import MedicalReport, MedicalReportMetric

logger = logging.getLogger(__name__)

_DRAFT_TTL = timedelta(hours=1)
_DRAFTS: dict[str, dict] = {}


def _parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _new_draft_id() -> str:
    return uuid.uuid4().hex


def _cleanup_expired_drafts() -> None:
    now = datetime.now()
    expired = [k for k, v in _DRAFTS.items() if v.get("expires_at") and v["expires_at"] < now]
    for k in expired:
        _DRAFTS.pop(k, None)


def _persist_report(
    db: Session,
    *,
    uploader_id: int,
    subject_id: int | None,
    image_paths: list[str],
    report_type: str,
    report_type_label: str | None,
    report_date: date | None,
    hospital: str | None,
    metrics: list[dict],
    raw_json: str | None,
    status: str,
) -> MedicalReport:
    report = MedicalReport(
        uploader_id=uploader_id,
        subject_id=subject_id,
        report_type=report_type,
        report_type_label=report_type_label,
        report_date=report_date,
        hospital=hospital,
        image_path=image_paths[0],
        image_paths=image_paths,
        raw_json=raw_json,
        status=status,
    )
    for m in metrics:
        report.metrics.append(MedicalReportMetric(**m))

    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def create_draft_from_images(
    *,
    uploader_id: int,
    subject_id: int | None,
    files: list[tuple[bytes, str | None, str | None]],
    report_date_override: str | None = None,
    hospital_override: str | None = None,
) -> dict:
    """Save images + parse first image into an in-memory draft."""
    _cleanup_expired_drafts()

    image_paths = [
        storage.save_image(content, filename, content_type)
        for content, filename, content_type in files
    ]

    report_type = "unknown"
    report_type_label = None
    report_date = _parse_date(report_date_override)
    metrics: list[dict] = []
    raw_json = None
    status = "parsed"

    try:
        parsed, raw_text = vision.parse_report_image(files[0][0])
        report_type = parsed["report_type"]
        report_type_label = parsed["report_type_label"]
        report_date = _parse_date(report_date_override or parsed["report_date"])
        metrics = parsed["metrics"]
        raw_json = raw_text
    except Exception as e:
        logger.exception("vision parse failed for draft")
        status = "failed"
        raw_json = json.dumps({"error": str(e)}, ensure_ascii=False)

    draft_id = _new_draft_id()
    draft = {
        "draft_id": draft_id,
        "uploader_id": uploader_id,
        "subject_id": subject_id,
        "image_paths": image_paths,
        "report_type": report_type,
        "report_type_label": report_type_label,
        "report_date": report_date,
        "hospital": hospital_override,
        "metrics": metrics,
        "raw_json": raw_json,
        "status": status,
        "expires_at": datetime.now() + _DRAFT_TTL,
    }
    _DRAFTS[draft_id] = draft
    return draft


def get_draft(draft_id: str) -> dict | None:
    _cleanup_expired_drafts()
    return _DRAFTS.get(draft_id)


def commit_draft(
    db: Session,
    *,
    draft_id: str,
    report_type: str,
    report_type_label: str | None,
    report_date: date | None,
    hospital: str | None,
    metrics: list[dict],
) -> MedicalReport:
    draft = get_draft(draft_id)
    if not draft:
        raise ValueError("draft not found or expired")

    report = _persist_report(
        db,
        uploader_id=draft["uploader_id"],
        subject_id=draft["subject_id"],
        image_paths=draft["image_paths"],
        report_type=report_type or "unknown",
        report_type_label=report_type_label,
        report_date=report_date,
        hospital=hospital,
        metrics=metrics,
        raw_json=draft.get("raw_json"),
        status="parsed" if metrics else draft.get("status", "failed"),
    )

    _DRAFTS.pop(draft_id, None)
    return report


def create_report(
    db: Session,
    *,
    uploader_id: int,
    subject_id: int | None,
    image_bytes: bytes,
    filename: str | None,
    content_type: str | None,
    report_date_override: str | None = None,
    hospital_override: str | None = None,
) -> MedicalReport:
    """Backward-compatible single-step flow: upload -> parse -> persist."""
    draft = create_draft_from_images(
        uploader_id=uploader_id,
        subject_id=subject_id,
        files=[(image_bytes, filename, content_type)],
        report_date_override=report_date_override,
        hospital_override=hospital_override,
    )
    return commit_draft(
        db,
        draft_id=draft["draft_id"],
        report_type=draft["report_type"],
        report_type_label=draft["report_type_label"],
        report_date=draft["report_date"],
        hospital=draft["hospital"],
        metrics=draft["metrics"],
    )
