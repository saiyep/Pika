import json
import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core import storage
from app.modules.medical import vision
from app.modules.medical.models import MedicalReport, MedicalReportMetric

logger = logging.getLogger(__name__)


def _parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def create_report(
    db: Session,
    *,
    uploader_id: int,
    subject_id: int | None,
    image_bytes: bytes,
    filename: str | None,
    content_type: str | None,
    report_date_override: str | None = None,
) -> MedicalReport:
    """Store the raw image, parse it, and persist. Never lose the image."""
    image_path = storage.save_image(image_bytes, filename, content_type)

    report = MedicalReport(
        uploader_id=uploader_id,
        subject_id=subject_id,
        image_path=image_path,
        status="parsing",
    )

    try:
        parsed, raw_text = vision.parse_report_image(image_bytes)
        report.report_type = parsed["report_type"]
        report.report_type_label = parsed["report_type_label"]
        report.report_date = _parse_date(report_date_override or parsed["report_date"])
        report.raw_json = raw_text
        report.status = "parsed"
        for m in parsed["metrics"]:
            report.metrics.append(MedicalReportMetric(**m))
    except Exception as e:  # vision/parse failure: keep image, mark failed
        logger.exception("vision parse failed for report")
        report.status = "failed"
        report.report_date = _parse_date(report_date_override)
        report.raw_json = json.dumps({"error": str(e)}, ensure_ascii=False)

    db.add(report)
    db.commit()
    db.refresh(report)
    return report
