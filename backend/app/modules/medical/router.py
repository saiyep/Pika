import os

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core import storage
from app.core.db import get_db
from app.core.deps import get_current_membership, get_current_user
from app.core.exceptions import NotFoundError, PikaException, VisionParseError
from app.core.user import service as user_service
from app.core.user.models import FamilyMembership
from app.core.schemas_base import ApiResponse
from app.core.user.models import User
from app.modules.medical import service
from app.modules.medical.models import MedicalReport, MedicalReportMetric
from app.modules.medical.schemas import (
    CatalogItem,
    CatalogOut,
    DraftCommitIn,
    DraftMetric,
    DraftOut,
    MedicalAclGrantIn,
    MedicalAclGrantOut,
    MedicalAclListOut,
    MetricOut,
    ReportDetailOut,
    ReportListItem,
    ReportListOut,
    ReportOut,
    ReportUpdateIn,
    TrendOut,
    TrendPoint,
)

router = APIRouter(prefix="/api/medical", tags=["medical"])


def _detail_out(db: Session, report: MedicalReport) -> ReportDetailOut:
    out = ReportOut.model_validate(report)
    if report.subject_id is not None:
        subj = db.get(User, report.subject_id)
        out.subject_nickname = subj.nickname if subj else None
    return ReportDetailOut(
        report=out,
        metrics=[MetricOut.model_validate(m) for m in report.metrics],
    )


def _ensure_subject_in_family(db: Session, actor: User, subject_id: int | None) -> None:
    if subject_id is None:
        return
    subject = db.get(User, subject_id)
    if not subject:
        raise NotFoundError("subject not found")
    if not user_service.in_same_family(db, actor_user_id=actor.id, target_user_id=subject_id):
        raise PikaException("subject out of family", code=403)


def _report_owner_user_id(report: MedicalReport) -> int:
    return report.subject_id or report.uploader_id


def _require_action_on_owner(db: Session, actor: User, owner_user_id: int, action: str) -> None:
    if not service.has_acl_action(
        db,
        actor_user_id=actor.id,
        owner_user_id=owner_user_id,
        action=action,
    ):
        raise PikaException("permission denied", code=403)


def _require_report_access(db: Session, actor: User, report: MedicalReport) -> None:
    _require_action_on_owner(db, actor, _report_owner_user_id(report), "view_report")


def _require_report_editable(db: Session, actor: User, report: MedicalReport) -> None:
    _require_action_on_owner(db, actor, _report_owner_user_id(report), "edit_report")


def _require_report_deletable(db: Session, actor: User, report: MedicalReport) -> None:
    _require_action_on_owner(db, actor, _report_owner_user_id(report), "delete_report")


def _family_user_ids(db: Session, membership: FamilyMembership) -> list[int]:
    return [
        uid
        for (uid,) in db.query(FamilyMembership.user_id)
        .filter(
            FamilyMembership.family_id == membership.family_id,
            FamilyMembership.is_active.is_(True),
        )
        .all()
    ]


def _owner_acl_out(db: Session, membership: FamilyMembership, owner_user_id: int) -> MedicalAclListOut:
    grants = {
        g.grantee_user_id: (g.actions_json or sorted(service.MEDICAL_ACTIONS))
        for g in service.list_acl_grants(db, owner_user_id=owner_user_id)
    }
    family_user_ids = _family_user_ids(db, membership)
    return MedicalAclListOut(
        owner_user_id=owner_user_id,
        grants=[
            MedicalAclGrantOut(
                owner_user_id=owner_user_id,
                grantee_user_id=uid,
                actions=grants.get(uid, sorted(service.MEDICAL_ACTIONS)),
            )
            for uid in family_user_ids
            if uid != owner_user_id
        ],
    )


@router.get("/permissions", response_model=ApiResponse[MedicalAclListOut])
def get_my_acl(
    owner_user_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    _ = membership
    owner_id = owner_user_id or user.id
    _ensure_subject_in_family(db, user, owner_id)
    if owner_id != user.id:
        _require_action_on_owner(db, user, owner_id, "view_report")
    return ApiResponse.ok(_owner_acl_out(db, membership, owner_id))


@router.put("/permissions", response_model=ApiResponse[MedicalAclListOut])
def set_my_acl(
    body: MedicalAclGrantIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    _ = membership
    if body.grantee_user_id == user.id:
        raise PikaException("cannot set acl for self", code=400)
    _ensure_subject_in_family(db, user, body.grantee_user_id)

    service.set_acl_grant(
        db,
        owner_user_id=user.id,
        grantee_user_id=body.grantee_user_id,
        actions=body.actions,
    )
    return ApiResponse.ok(_owner_acl_out(db, membership, user.id))


@router.post("/reports", response_model=ApiResponse[ReportDetailOut])
async def upload_report(
    file: UploadFile = File(...),
    report_date: str | None = Form(default=None),
    subject_id: int | None = Form(default=None),
    hospital: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    _ = membership
    _ensure_subject_in_family(db, user, subject_id)
    owner_user_id = subject_id or user.id
    _require_action_on_owner(db, user, owner_user_id, "upload_for_owner")
    content = await file.read()
    report = service.create_report(
        db,
        uploader_id=user.id,
        subject_id=subject_id,
        image_bytes=content,
        filename=file.filename,
        content_type=file.content_type,
        report_date_override=report_date,
        hospital_override=hospital,
    )
    return ApiResponse.ok(_detail_out(db, report))


@router.post("/report-drafts", response_model=ApiResponse[DraftOut])
async def create_report_draft(
    files: list[UploadFile] = File(...),
    report_date: str | None = Form(default=None),
    subject_id: int | None = Form(default=None),
    hospital: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    _ = membership
    _ensure_subject_in_family(db, user, subject_id)
    owner_user_id = subject_id or user.id
    _require_action_on_owner(db, user, owner_user_id, "upload_for_owner")
    payload = []
    for f in files:
        payload.append((await f.read(), f.filename, f.content_type))

    draft = service.create_draft_from_images(
        db,
        uploader_id=user.id,
        subject_id=subject_id,
        files=payload,
        report_date_override=report_date,
        hospital_override=hospital,
    )
    return ApiResponse.ok(
        DraftOut(
            draft_id=draft["draft_id"],
            is_lab_report=draft["is_lab_report"],
            report_type=draft["report_type"],
            report_type_label=draft["report_type_label"],
            report_date=draft["report_date"],
            hospital=draft["hospital"],
            metrics=[DraftMetric(**m) for m in draft["metrics"]],
        )
    )


@router.post("/report-drafts/{draft_id}/commit", response_model=ApiResponse[ReportDetailOut])
def commit_report_draft(
    draft_id: str,
    body: DraftCommitIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    _ = membership
    try:
        report = service.commit_draft(
            db,
            draft_id=draft_id,
            report_type=body.report_type,
            report_type_label=body.report_type_label,
            report_date=body.report_date,
            hospital=body.hospital,
            metrics=[m.model_dump() for m in body.metrics],
        )
    except ValueError as e:
        raise NotFoundError(str(e))

    _require_report_access(db, user, report)
    return ApiResponse.ok(_detail_out(db, report))


@router.get("/reports", response_model=ApiResponse[ReportListOut])
def list_reports(
    subject_id: int | None = Query(default=None),
    report_type: str | None = Query(default=None),
    hospital: list[str] | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    family_user_ids = _family_user_ids(db, membership)
    visible_owner_ids = [
        uid for uid in family_user_ids
        if service.has_acl_action(db, actor_user_id=user.id, owner_user_id=uid, action="view_report")
    ]
    if not visible_owner_ids:
        return ApiResponse.ok(ReportListOut(total=0, items=[]))

    q = db.query(MedicalReport).filter(
        or_(
            MedicalReport.subject_id.in_(visible_owner_ids),
            and_(MedicalReport.subject_id.is_(None), MedicalReport.uploader_id.in_(visible_owner_ids)),
        )
    )
    if subject_id is not None:
        _ensure_subject_in_family(db, user, subject_id)
        _require_action_on_owner(db, user, subject_id, "view_report")
        q = q.filter(MedicalReport.subject_id == subject_id)
    if report_type:
        q = q.filter(MedicalReport.report_type == report_type)
    if hospital:
        hospital_values = [h for h in hospital if h]
        if hospital_values:
            q = q.filter(MedicalReport.hospital.in_(hospital_values))
    if date_from:
        q = q.filter(MedicalReport.report_date >= date_from)
    if date_to:
        q = q.filter(MedicalReport.report_date <= date_to)

    total = q.count()
    rows = (
        q.order_by(
            MedicalReport.report_date.is_(None),  # nulls last
            MedicalReport.report_date.desc(),
            MedicalReport.created_at.desc(),
        )
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    nickname_by_id = {
        u.id: u.nickname
        for u in db.query(User).filter(User.id.in_(family_user_ids)).all()
    }
    items = []
    for r in rows:
        abnormal = sum(
            1 for m in r.metrics if m.abnormal_flag in ("high", "low")
        )
        items.append(
            ReportListItem(
                id=r.id,
                report_type=r.report_type,
                report_type_label=r.report_type_label,
                report_date=r.report_date,
                hospital=r.hospital,
                subject_id=r.subject_id,
                subject_nickname=nickname_by_id.get(r.subject_id),
                uploader_nickname=nickname_by_id.get(r.uploader_id),
                abnormal_count=abnormal,
                status=r.status,
                created_at=r.created_at,
            )
        )
    return ApiResponse.ok(ReportListOut(total=total, items=items))


@router.get("/hospitals", response_model=ApiResponse[list[str]])
def list_hospitals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    family_user_ids = _family_user_ids(db, membership)
    visible_owner_ids = [
        uid for uid in family_user_ids
        if service.has_acl_action(db, actor_user_id=user.id, owner_user_id=uid, action="view_report")
    ]
    if not visible_owner_ids:
        return ApiResponse.ok([])

    rows = (
        db.query(MedicalReport.hospital)
        .filter(
            or_(
                MedicalReport.subject_id.in_(visible_owner_ids),
                and_(MedicalReport.subject_id.is_(None), MedicalReport.uploader_id.in_(visible_owner_ids)),
            ),
            MedicalReport.hospital.isnot(None),
        )
        .distinct()
        .all()
    )
    return ApiResponse.ok(sorted(r[0] for r in rows if r[0]))


@router.get("/reports/{report_id}", response_model=ApiResponse[ReportDetailOut])
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    _ = membership
    report = db.get(MedicalReport, report_id)
    if not report:
        raise NotFoundError("report not found")
    _require_report_access(db, user, report)
    return ApiResponse.ok(_detail_out(db, report))


@router.put("/reports/{report_id}", response_model=ApiResponse[ReportDetailOut])
def update_report(
    report_id: int,
    body: ReportUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    _ = membership
    report = db.get(MedicalReport, report_id)
    if report is None:
        raise NotFoundError("report not found")
    _require_report_editable(db, user, report)
    _ensure_subject_in_family(db, user, body.subject_id)
    if body.subject_id is not None:
        _require_action_on_owner(db, user, body.subject_id, "edit_report")

    updated = service.update_report(
        db,
        report_id=report_id,
        report_type=body.report_type,
        report_type_label=body.report_type_label,
        report_date=body.report_date,
        hospital=body.hospital,
        subject_id=body.subject_id,
        metrics=[m.model_dump() for m in body.metrics],
    )
    if updated is None:
        raise NotFoundError("report not found")
    return ApiResponse.ok(_detail_out(db, updated))


@router.delete("/reports/{report_id}", response_model=ApiResponse[None])
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    _ = membership
    report = db.get(MedicalReport, report_id)
    if not report:
        raise NotFoundError("report not found")
    _require_report_deletable(db, user, report)

    ok = service.delete_report(db, report_id=report_id)
    if not ok:
        raise NotFoundError("report not found")
    return ApiResponse.ok(None)


@router.post("/reports/{report_id}/reparse", response_model=ApiResponse[ReportDetailOut])
def reparse_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    _ = membership
    existing = db.get(MedicalReport, report_id)
    if not existing:
        raise NotFoundError("report not found")
    _require_report_editable(db, user, existing)

    try:
        report = service.reparse_report(db, report_id=report_id)
    except Exception:
        raise VisionParseError("重新解析失败，请稍后再试")
    if report is None:
        raise NotFoundError("report not found")
    return ApiResponse.ok(_detail_out(db, report))


@router.get("/reports/{report_id}/image")
def get_report_image(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    _ = membership
    report = db.get(MedicalReport, report_id)
    if not report:
        raise NotFoundError("report not found")
    _require_report_access(db, user, report)
    path = storage.abs_path(report.image_path)
    if not os.path.exists(path):
        raise NotFoundError("image file missing")
    return FileResponse(path)


@router.get("/metrics/trend", response_model=ApiResponse[TrendOut])
def metric_trend(
    item_code: str | None = Query(default=None),
    item_name: str | None = Query(default=None),
    subject_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    family_user_ids = _family_user_ids(db, membership)
    visible_owner_ids = [
        uid for uid in family_user_ids
        if service.has_acl_action(db, actor_user_id=user.id, owner_user_id=uid, action="view_report")
    ]
    if not visible_owner_ids:
        return ApiResponse.ok(
            TrendOut(
                item_code=item_code,
                item_name=item_name or "",
                unit=None,
                ref_low=None,
                ref_high=None,
                has_mixed_reference=False,
                points=[],
            )
        )

    q = (
        db.query(MedicalReportMetric, MedicalReport)
        .join(MedicalReport, MedicalReportMetric.report_id == MedicalReport.id)
        .filter(
            or_(
                MedicalReport.subject_id.in_(visible_owner_ids),
                and_(MedicalReport.subject_id.is_(None), MedicalReport.uploader_id.in_(visible_owner_ids)),
            )
        )
    )
    if item_code:
        q = q.filter(MedicalReportMetric.item_code == item_code)
    elif item_name:
        q = q.filter(MedicalReportMetric.item_name == item_name)
    if subject_id is not None:
        _ensure_subject_in_family(db, user, subject_id)
        _require_action_on_owner(db, user, subject_id, "view_report")
        q = q.filter(MedicalReport.subject_id == subject_id)

    rows = q.order_by(
        MedicalReport.report_date.is_(None),
        MedicalReport.report_date.asc(),
        MedicalReport.created_at.asc(),
        MedicalReport.id.asc(),
        MedicalReportMetric.seq.asc(),
    ).all()

    reference_keys = {
        (metric.ref_low, metric.ref_high, metric.ref_range)
        for metric, _ in rows
    }
    has_mixed_reference = len(reference_keys) > 1

    points = [
        TrendPoint(
            report_date=rep.report_date,
            value_text=metric.value_text,
            value_num=metric.value_num,
            unit=metric.unit,
            ref_range=metric.ref_range,
            ref_low=metric.ref_low,
            ref_high=metric.ref_high,
            abnormal_flag=metric.abnormal_flag,
            report_id=rep.id,
            hospital=rep.hospital,
        )
        for metric, rep in rows
    ]
    first = rows[0][0] if rows else None
    latest = rows[-1][0] if rows else None
    return ApiResponse.ok(
        TrendOut(
            item_code=item_code or (first.item_code if first else None),
            item_name=item_name or (first.item_name if first else ""),
            unit=latest.unit if latest else (first.unit if first else None),
            ref_low=latest.ref_low if latest else None,
            ref_high=latest.ref_high if latest else None,
            has_mixed_reference=has_mixed_reference,
            points=points,
        )
    )


@router.get("/metrics/catalog", response_model=ApiResponse[CatalogOut])
def metric_catalog(
    subject_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    membership: FamilyMembership = Depends(get_current_membership),
):
    family_user_ids = _family_user_ids(db, membership)
    visible_owner_ids = [
        uid for uid in family_user_ids
        if service.has_acl_action(db, actor_user_id=user.id, owner_user_id=uid, action="view_report")
    ]
    if not visible_owner_ids:
        return ApiResponse.ok(CatalogOut(items=[]))

    q = (
        db.query(
            MedicalReportMetric.item_code,
            MedicalReportMetric.item_name,
            func.count(MedicalReportMetric.id),
        )
        .join(MedicalReport, MedicalReportMetric.report_id == MedicalReport.id)
        .filter(
            or_(
                MedicalReport.subject_id.in_(visible_owner_ids),
                and_(MedicalReport.subject_id.is_(None), MedicalReport.uploader_id.in_(visible_owner_ids)),
            )
        )
    )
    if subject_id is not None:
        _ensure_subject_in_family(db, user, subject_id)
        _require_action_on_owner(db, user, subject_id, "view_report")
        q = q.filter(MedicalReport.subject_id == subject_id)
    q = q.group_by(MedicalReportMetric.item_code, MedicalReportMetric.item_name)

    items = [
        CatalogItem(item_code=code, item_name=name, count=count)
        for code, name, count in q.all()
    ]
    return ApiResponse.ok(CatalogOut(items=items))
