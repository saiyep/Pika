import hashlib
import json
import logging
import os
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core import storage
from app.core.exceptions import DuplicateReportError
from app.modules.medical import vision
from app.modules.medical.models import MedicalReport, MedicalReportMetric, UserFavoriteService

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


def _content_hash(files: list[tuple[bytes, str | None, str | None]]) -> str:
    """Order-independent hash of a report's images: sha256 of each image's
    sha256, sorted then joined. Same images -> same hash regardless of order."""
    per_image = sorted(hashlib.sha256(content).hexdigest() for content, _, _ in files)
    return hashlib.sha256("".join(per_image).encode()).hexdigest()


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
    content_hash: str | None = None,
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
        content_hash=content_hash,
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
    db: Session,
    *,
    uploader_id: int,
    subject_id: int | None,
    files: list[tuple[bytes, str | None, str | None]],
    report_date_override: str | None = None,
    hospital_override: str | None = None,
) -> dict:
    """Save images + parse first image into an in-memory draft.

    Rejects duplicates (same image set already committed) before saving or
    parsing, to save disk and Azure tokens.
    """
    _cleanup_expired_drafts()

    content_hash = _content_hash(files)
    if db.query(MedicalReport.id).filter_by(content_hash=content_hash).first():
        raise DuplicateReportError("该检查单已存在，请勿重复上传")

    image_paths = [
        storage.save_image(content, filename, content_type)
        for content, filename, content_type in files
    ]

    report_type = "unknown"
    report_type_label = None
    report_date = _parse_date(report_date_override)
    hospital = hospital_override
    is_lab_report = True
    metrics: list[dict] = []
    raw_json = None
    status = "parsed"

    try:
        parsed, raw_text = vision.parse_report_image(files[0][0])
        is_lab_report = parsed["is_lab_report"]
        report_type = parsed["report_type"]
        report_type_label = parsed["report_type_label"]
        report_date = _parse_date(report_date_override or parsed["report_date"])
        hospital = hospital_override or parsed["hospital"]
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
        "content_hash": content_hash,
        "is_lab_report": is_lab_report,
        "report_type": report_type,
        "report_type_label": report_type_label,
        "report_date": report_date,
        "hospital": hospital,
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
        content_hash=draft.get("content_hash"),
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
        db,
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


def delete_report(db: Session, *, report_id: int) -> bool:
    """Delete a report, its metrics (cascade), and its image files.

    Returns False if the report does not exist.
    """
    report = db.get(MedicalReport, report_id)
    if not report:
        return False

    paths = report.image_paths or ([report.image_path] if report.image_path else [])
    for rel in paths:
        abs_p = storage.abs_path(rel)
        if os.path.exists(abs_p):
            os.remove(abs_p)

    db.delete(report)
    db.commit()
    return True


def reparse_report(db: Session, *, report_id: int) -> MedicalReport | None:
    """Re-run vision on a stored report's first image and refresh its
    metrics/type/date/status. Returns None if the report does not exist.
    Used to recover from transient parse failures without re-uploading.
    """
    report = db.get(MedicalReport, report_id)
    if not report:
        return None

    abs_p = storage.abs_path(report.image_path)
    with open(abs_p, "rb") as f:
        image_bytes = f.read()

    parsed, raw_text = vision.parse_report_image(image_bytes)

    report.metrics.clear()
    for m in parsed["metrics"]:
        report.metrics.append(MedicalReportMetric(**m))
    report.report_type = parsed["report_type"] or "unknown"
    report.report_type_label = parsed["report_type_label"]
    parsed_date = _parse_date(parsed["report_date"])
    if parsed_date:
        report.report_date = parsed_date
    report.raw_json = raw_text
    report.status = "parsed" if parsed["metrics"] else "failed"

    db.commit()
    db.refresh(report)
    return report


def update_report(
    db: Session,
    *,
    report_id: int,
    report_type: str,
    report_type_label: str | None,
    report_date: date | None,
    hospital: str | None,
    metrics: list[dict],
) -> MedicalReport | None:
    """Edit a stored report's header fields and metrics (user correction).
    Image and content_hash are untouched. Returns None if not found.
    """
    report = db.get(MedicalReport, report_id)
    if not report:
        return None

    report.report_type = report_type or "unknown"
    report.report_type_label = report_type_label
    report.report_date = report_date
    report.hospital = hospital
    report.metrics.clear()
    for i, m in enumerate(metrics):
        # Re-derive value_num/ref_low/ref_high/abnormal_flag from the edited
        # text so the trend chart stays consistent after manual correction.
        norm = vision._normalize_metric(
            {
                "item_name": m.get("item_name"),
                "item_code": m.get("item_code"),
                "value": m.get("value_text"),
                "unit": m.get("unit"),
                "ref_range": m.get("ref_range"),
                "abnormal_flag": m.get("abnormal_flag"),
            },
            i,
        )
        if norm:
            report.metrics.append(MedicalReportMetric(**norm))
    report.status = "parsed" if report.metrics else report.status

    db.commit()
    db.refresh(report)
    return report


def list_favorites(db: Session, *, user_id: int) -> list[str]:
    rows = db.query(UserFavoriteService.service_key).filter_by(user_id=user_id).all()
    return [r[0] for r in rows]


def add_favorite(db: Session, *, user_id: int, service_key: str) -> None:
    exists = (
        db.query(UserFavoriteService.id)
        .filter_by(user_id=user_id, service_key=service_key)
        .first()
    )
    if exists:
        return
    db.add(UserFavoriteService(user_id=user_id, service_key=service_key))
    db.commit()


def remove_favorite(db: Session, *, user_id: int, service_key: str) -> None:
    db.query(UserFavoriteService).filter_by(
        user_id=user_id, service_key=service_key
    ).delete()
    db.commit()
