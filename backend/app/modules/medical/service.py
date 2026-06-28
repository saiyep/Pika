import hashlib
import json
import logging
import os
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core import storage
from app.core.exceptions import DuplicateReportError
from app.core.user import service as user_service
from app.modules.medical import vision
from app.modules.medical.models import (
    MedicalAclGrant,
    MedicalMetricAlias,
    MedicalMetricDictionary,
    MedicalReport,
    MedicalReportCategory,
    MedicalReportMetric,
    MedicalReportMetricMap,
    MedicalUserFocusMetric,
)

logger = logging.getLogger(__name__)

MEDICAL_ACTIONS = {
    "view_report",
    "upload_for_owner",
    "edit_report",
    "delete_report",
}

MEDICAL_CATEGORY_DEFAULTS = [
    ("blood_routine", "血常规", 10),
    ("urine_routine", "尿常规", 20),
    ("liver_kidney", "肝肾功能", 30),
    ("tumor_marker", "肿瘤标志物", 40),
    ("thyroid", "甲状腺功能", 50),
]
MEDICAL_CATEGORY_KEYS = {key for key, _, _ in MEDICAL_CATEGORY_DEFAULTS}

_KEYWORD_CATEGORY_RULES = [
    ("blood_routine", ["白细胞", "红细胞", "血小板", "血红蛋白", "中性粒", "淋巴"]),
    ("urine_routine", ["尿", "尿蛋白", "尿糖", "尿酮体", "尿白细胞"]),
    ("liver_kidney", ["谷丙", "谷草", "肌酐", "尿素", "总蛋白", "白蛋白", "胆红素"]),
    ("tumor_marker", ["肿瘤", "癌胚", "甲胎", "ca125", "ca199", "psa"]),
    ("thyroid", ["甲状", "t3", "t4", "tsh", "ft3", "ft4"]),
]

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

    owner_user_id = subject_id or uploader_id
    categories = list_user_categories(db, user_id=owner_user_id)
    candidates = [c.display_name for c in categories if c.enabled]

    try:
        parsed, raw_text = vision.parse_report_image(files[0][0], category_candidates=candidates)
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
    subject_id: int | None = None,
) -> MedicalReport | None:
    report = db.get(MedicalReport, report_id)
    if not report:
        return None

    report.report_type = report_type or "unknown"
    report.report_type_label = report_type_label
    report.report_date = report_date
    report.hospital = hospital
    if subject_id is not None:
        report.subject_id = subject_id
    report.metrics.clear()
    for i, m in enumerate(metrics):
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


def _normalized_actions(actions: list[str]) -> list[str]:
    uniq = sorted(set(a for a in actions if a in MEDICAL_ACTIONS))
    return uniq


def set_acl_grant(
    db: Session,
    *,
    owner_user_id: int,
    grantee_user_id: int,
    actions: list[str],
) -> MedicalAclGrant:
    clean = _normalized_actions(actions)
    grant = (
        db.query(MedicalAclGrant)
        .filter(
            MedicalAclGrant.owner_user_id == owner_user_id,
            MedicalAclGrant.grantee_user_id == grantee_user_id,
        )
        .first()
    )
    if clean:
        if grant is None:
            grant = MedicalAclGrant(
                owner_user_id=owner_user_id,
                grantee_user_id=grantee_user_id,
                actions_json=clean,
            )
            db.add(grant)
        else:
            grant.actions_json = clean
        db.commit()
        db.refresh(grant)
        return grant

    if grant is not None:
        db.delete(grant)
        db.commit()

    return MedicalAclGrant(
        owner_user_id=owner_user_id,
        grantee_user_id=grantee_user_id,
        actions_json=sorted(MEDICAL_ACTIONS),
    )


def list_acl_grants(db: Session, *, owner_user_id: int) -> list[MedicalAclGrant]:
    return (
        db.query(MedicalAclGrant)
        .filter(MedicalAclGrant.owner_user_id == owner_user_id)
        .order_by(MedicalAclGrant.grantee_user_id.asc())
        .all()
    )


def has_acl_action(
    db: Session,
    *,
    actor_user_id: int,
    owner_user_id: int,
    action: str,
) -> bool:
    if actor_user_id == owner_user_id:
        return True
    if action not in MEDICAL_ACTIONS:
        return False
    if not user_service.in_same_family(db, actor_user_id=actor_user_id, target_user_id=owner_user_id):
        return False

    grant = (
        db.query(MedicalAclGrant)
        .filter(
            MedicalAclGrant.owner_user_id == owner_user_id,
            MedicalAclGrant.grantee_user_id == actor_user_id,
        )
        .first()
    )
    if not grant:
        return True
    actions = grant.actions_json or []
    if not actions:
        return True
    return action in actions


def ensure_user_categories(db: Session, *, user_id: int) -> None:
    exists = (
        db.query(MedicalReportCategory.id)
        .filter(MedicalReportCategory.user_id == user_id, MedicalReportCategory.enabled.is_(True))
        .first()
    )
    if exists:
        return

    for key, display_name, sort_order in MEDICAL_CATEGORY_DEFAULTS:
        db.add(
            MedicalReportCategory(
                user_id=user_id,
                category_key=key,
                display_name=display_name,
                enabled=True,
                sort_order=sort_order,
            )
        )
    db.commit()


def list_user_categories(db: Session, *, user_id: int) -> list[MedicalReportCategory]:
    ensure_user_categories(db, user_id=user_id)
    return (
        db.query(MedicalReportCategory)
        .filter(MedicalReportCategory.user_id == user_id, MedicalReportCategory.enabled.is_(True))
        .order_by(MedicalReportCategory.id.asc())
        .all()
    )


def get_user_category_by_id(
    db: Session,
    *,
    user_id: int,
    category_id: int,
) -> MedicalReportCategory | None:
    return (
        db.query(MedicalReportCategory)
        .filter(
            MedicalReportCategory.id == category_id,
            MedicalReportCategory.user_id == user_id,
            MedicalReportCategory.enabled.is_(True),
        )
        .first()
    )


def create_user_category(db: Session, *, user_id: int, display_name: str) -> MedicalReportCategory:
    clean_name = (display_name or "").strip()
    if not clean_name:
        raise ValueError("display_name required")

    category = MedicalReportCategory(
        user_id=user_id,
        category_key=f"custom_{uuid.uuid4().hex[:8]}",
        display_name=clean_name,
        enabled=True,
        sort_order=0,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def rename_user_category(db: Session, *, user_id: int, category_id: int, display_name: str) -> MedicalReportCategory:
    category = (
        db.query(MedicalReportCategory)
        .filter(
            MedicalReportCategory.id == category_id,
            MedicalReportCategory.user_id == user_id,
            MedicalReportCategory.enabled.is_(True),
        )
        .first()
    )
    if category is None:
        raise ValueError("category not found")

    clean_name = (display_name or "").strip()
    if not clean_name:
        raise ValueError("display_name required")

    category.display_name = clean_name
    db.commit()
    db.refresh(category)
    return category


def disable_user_category(db: Session, *, user_id: int, category_id: int) -> bool:
    category = (
        db.query(MedicalReportCategory)
        .filter(
            MedicalReportCategory.id == category_id,
            MedicalReportCategory.user_id == user_id,
            MedicalReportCategory.enabled.is_(True),
        )
        .first()
    )
    if category is None:
        return False
    category.enabled = False
    db.commit()
    return True

def create_user_focus_metric(
    db: Session,
    *,
    user_id: int,
    dictionary_id: int,
    category_id: int,
) -> MedicalUserFocusMetric:
    dictionary = db.get(MedicalMetricDictionary, dictionary_id)
    if dictionary is None:
        raise ValueError("dictionary not found")

    category = get_user_category_by_id(db, user_id=user_id, category_id=category_id)
    if category is None:
        raise ValueError("category not found")

    row = (
        db.query(MedicalUserFocusMetric)
        .filter(
            MedicalUserFocusMetric.user_id == user_id,
            MedicalUserFocusMetric.dictionary_id == dictionary_id,
        )
        .first()
    )
    if row is not None:
        raise ValueError("focus metric already exists")

    row = MedicalUserFocusMetric(
        user_id=user_id,
        dictionary_id=dictionary_id,
        category_key=category.category_key,
        enabled=True,
        sort_order=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_user_focus_metric_category(
    db: Session,
    *,
    user_id: int,
    focus_id: int,
    category_id: int,
) -> MedicalUserFocusMetric:
    category = get_user_category_by_id(db, user_id=user_id, category_id=category_id)
    if category is None:
        raise ValueError("category not found")

    row = (
        db.query(MedicalUserFocusMetric)
        .filter(
            MedicalUserFocusMetric.id == focus_id,
            MedicalUserFocusMetric.user_id == user_id,
        )
        .first()
    )
    if row is None:
        raise ValueError("focus metric not found")

    row.category_key = category.category_key
    db.commit()
    db.refresh(row)
    return row


def list_user_focus_metrics(db: Session, *, user_id: int) -> list[MedicalUserFocusMetric]:
    return (
        db.query(MedicalUserFocusMetric)
        .filter(MedicalUserFocusMetric.user_id == user_id)
        .order_by(MedicalUserFocusMetric.sort_order.asc(), MedicalUserFocusMetric.id.asc())
        .all()
    )


def delete_user_focus_metric(db: Session, *, user_id: int, focus_id: int) -> bool:
    row = (
        db.query(MedicalUserFocusMetric)
        .filter(
            MedicalUserFocusMetric.id == focus_id,
            MedicalUserFocusMetric.user_id == user_id,
        )
        .first()
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def list_user_focus_metric_details(db: Session, *, user_id: int) -> list[tuple[MedicalUserFocusMetric, MedicalMetricDictionary]]:
    return (
        db.query(MedicalUserFocusMetric, MedicalMetricDictionary)
        .join(MedicalMetricDictionary, MedicalMetricDictionary.id == MedicalUserFocusMetric.dictionary_id)
        .filter(MedicalUserFocusMetric.user_id == user_id)
        .order_by(MedicalUserFocusMetric.sort_order.asc(), MedicalUserFocusMetric.id.asc())
        .all()
    )


def _guess_category(item_name: str) -> str:
    name = (item_name or "").strip().lower()
    for category_key, keywords in _KEYWORD_CATEGORY_RULES:
        for kw in keywords:
            if kw in name:
                return category_key
    return "blood_routine"


def bootstrap_metric_dictionary(db: Session, *, owner_user_id: int) -> dict:
    rows = (
        db.query(
            MedicalReportMetric.item_name,
            MedicalReportMetric.item_code,
            MedicalReportMetric.unit,
            MedicalReport.hospital,
        )
        .join(MedicalReport, MedicalReport.id == MedicalReportMetric.report_id)
        .filter(
            or_(
                MedicalReport.subject_id == owner_user_id,
                and_(MedicalReport.subject_id.is_(None), MedicalReport.uploader_id == owner_user_id),
            )
        )
        .all()
    )

    created_dictionary = 0
    created_alias = 0

    for item_name, item_code, unit, hospital in rows:
        clean_name = (item_name or "").strip()
        if not clean_name:
            continue
        canonical_key = ((item_code or "").strip() or clean_name).lower()
        category_key = _guess_category(clean_name)

        dic = (
            db.query(MedicalMetricDictionary)
            .filter(MedicalMetricDictionary.canonical_key == canonical_key)
            .first()
        )
        if dic is None:
            dic = MedicalMetricDictionary(
                canonical_key=canonical_key,
                canonical_name=clean_name,
                canonical_unit=(unit or None),
                category_key=category_key,
                enabled=True,
            )
            db.add(dic)
            db.flush()
            created_dictionary += 1

        alias = (
            db.query(MedicalMetricAlias)
            .filter(
                MedicalMetricAlias.owner_user_id == owner_user_id,
                MedicalMetricAlias.dictionary_id == dic.id,
                MedicalMetricAlias.alias_name == clean_name,
                MedicalMetricAlias.alias_unit == (unit or None),
                MedicalMetricAlias.hospital_hint == (hospital or None),
            )
            .first()
        )
        if alias is None:
            db.add(
                MedicalMetricAlias(
                    owner_user_id=owner_user_id,
                    dictionary_id=dic.id,
                    alias_name=clean_name,
                    alias_unit=(unit or None),
                    hospital_hint=(hospital or None),
                    report_type_hint=None,
                    priority=100 if hospital else 10,
                )
            )
            created_alias += 1

    db.commit()
    return {
        "dictionary_created": created_dictionary,
        "alias_created": created_alias,
    }


def list_metric_alias_details(
    db: Session,
    *,
    owner_user_id: int,
    hospital_hint: str | None = None,
    category_key: str | None = None,
    dictionary_id: int | None = None,
) -> list[tuple[MedicalMetricAlias, MedicalMetricDictionary]]:
    q = (
        db.query(MedicalMetricAlias, MedicalMetricDictionary)
        .join(MedicalMetricDictionary, MedicalMetricDictionary.id == MedicalMetricAlias.dictionary_id)
        .filter(MedicalMetricAlias.owner_user_id == owner_user_id)
    )
    if hospital_hint is not None:
        q = q.filter(MedicalMetricAlias.hospital_hint == hospital_hint)
    if category_key:
        q = q.filter(MedicalMetricDictionary.category_key == category_key)
    if dictionary_id is not None:
        q = q.filter(MedicalMetricAlias.dictionary_id == dictionary_id)

    return q.order_by(MedicalMetricAlias.priority.desc(), MedicalMetricAlias.id.asc()).all()


def create_metric_alias(
    db: Session,
    *,
    owner_user_id: int,
    dictionary_id: int,
    alias_name: str,
    alias_unit: str | None = None,
    hospital_hint: str | None = None,
    priority: int = 10,
) -> MedicalMetricAlias:
    dic = db.get(MedicalMetricDictionary, dictionary_id)
    if dic is None:
        raise ValueError("dictionary not found")

    clean_name = (alias_name or "").strip()
    if not clean_name:
        raise ValueError("alias_name required")

    row = (
        db.query(MedicalMetricAlias)
        .filter(
            MedicalMetricAlias.owner_user_id == owner_user_id,
            MedicalMetricAlias.dictionary_id == dictionary_id,
            MedicalMetricAlias.alias_name == clean_name,
            MedicalMetricAlias.alias_unit == ((alias_unit or "").strip() or None),
            MedicalMetricAlias.hospital_hint == ((hospital_hint or "").strip() or None),
        )
        .first()
    )
    if row is not None:
        raise ValueError("alias already exists")

    row = MedicalMetricAlias(
        owner_user_id=owner_user_id,
        dictionary_id=dictionary_id,
        alias_name=clean_name,
        alias_unit=((alias_unit or "").strip() or None),
        hospital_hint=((hospital_hint or "").strip() or None),
        report_type_hint=None,
        priority=priority,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_metric_alias(
    db: Session,
    *,
    owner_user_id: int,
    alias_id: int,
    alias_name: str | None = None,
    alias_unit: str | None = None,
    hospital_hint: str | None = None,
    priority: int | None = None,
) -> MedicalMetricAlias:
    row = (
        db.query(MedicalMetricAlias)
        .filter(
            MedicalMetricAlias.id == alias_id,
            MedicalMetricAlias.owner_user_id == owner_user_id,
        )
        .first()
    )
    if row is None:
        raise ValueError("alias not found")

    if alias_name is not None:
        clean_name = alias_name.strip()
        if not clean_name:
            raise ValueError("alias_name required")
        row.alias_name = clean_name
    if alias_unit is not None:
        row.alias_unit = (alias_unit or "").strip() or None
    if hospital_hint is not None:
        row.hospital_hint = (hospital_hint or "").strip() or None
    if priority is not None:
        row.priority = priority

    db.commit()
    db.refresh(row)
    return row


def delete_metric_alias(db: Session, *, owner_user_id: int, alias_id: int) -> bool:
    row = (
        db.query(MedicalMetricAlias)
        .filter(
            MedicalMetricAlias.id == alias_id,
            MedicalMetricAlias.owner_user_id == owner_user_id,
        )
        .first()
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def rebuild_metric_mappings(db: Session, *, owner_user_id: int) -> dict:
    aliases = db.query(MedicalMetricAlias).filter(MedicalMetricAlias.owner_user_id == owner_user_id).all()
    alias_by_name: dict[str, list[MedicalMetricAlias]] = {}
    for alias in aliases:
        alias_by_name.setdefault(alias.alias_name.strip().lower(), []).append(alias)

    rows = (
        db.query(MedicalReportMetric, MedicalReport)
        .join(MedicalReport, MedicalReport.id == MedicalReportMetric.report_id)
        .filter(
            or_(
                MedicalReport.subject_id == owner_user_id,
                and_(MedicalReport.subject_id.is_(None), MedicalReport.uploader_id == owner_user_id),
            )
        )
        .all()
    )

    mapped = 0
    unmapped = 0

    for metric, report in rows:
        key = (metric.item_name or "").strip().lower()
        candidates = alias_by_name.get(key, [])
        best: MedicalMetricAlias | None = None
        best_score = -1
        for candidate in candidates:
            score = candidate.priority or 0
            if candidate.alias_unit and metric.unit and candidate.alias_unit == metric.unit:
                score += 10
            if candidate.hospital_hint and report.hospital and candidate.hospital_hint == report.hospital:
                score += 20
            if score > best_score:
                best = candidate
                best_score = score

        mapping = (
            db.query(MedicalReportMetricMap)
            .filter(MedicalReportMetricMap.report_metric_id == metric.id)
            .first()
        )
        if mapping is None:
            mapping = MedicalReportMetricMap(report_metric_id=metric.id)
            db.add(mapping)

        if best is None:
            mapping.dictionary_id = None
            mapping.alias_id = None
            mapping.match_status = "unmapped"
            mapping.confidence = None
            unmapped += 1
        else:
            mapping.dictionary_id = best.dictionary_id
            mapping.alias_id = best.id
            mapping.match_status = "auto"
            mapping.confidence = 1.0
            mapped += 1

    db.commit()
    return {
        "mapped": mapped,
        "unmapped": unmapped,
    }