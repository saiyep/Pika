import os

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import storage
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.core.models_base import User
from app.core.schemas_base import ApiResponse
from app.modules.medical import service
from app.modules.medical.models import MedicalReport, MedicalReportMetric
from app.modules.medical.schemas import (
    CatalogItem,
    CatalogOut,
    MetricOut,
    ReportDetailOut,
    ReportListItem,
    ReportListOut,
    ReportOut,
    TrendOut,
    TrendPoint,
)

router = APIRouter(prefix="/api/medical", tags=["medical"])


@router.post("/reports", response_model=ApiResponse[ReportDetailOut])
async def upload_report(
    file: UploadFile = File(...),
    report_date: str | None = Form(default=None),
    subject_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    report = service.create_report(
        db,
        uploader_id=user.id,
        subject_id=subject_id,
        image_bytes=content,
        filename=file.filename,
        content_type=file.content_type,
        report_date_override=report_date,
    )
    return ApiResponse.ok(
        ReportDetailOut(
            report=ReportOut.model_validate(report),
            metrics=[MetricOut.model_validate(m) for m in report.metrics],
        )
    )


@router.get("/reports", response_model=ApiResponse[ReportListOut])
def list_reports(
    subject_id: int | None = Query(default=None),
    report_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(MedicalReport)
    if subject_id is not None:
        q = q.filter(MedicalReport.subject_id == subject_id)
    if report_type:
        q = q.filter(MedicalReport.report_type == report_type)

    total = q.count()
    rows = (
        q.order_by(MedicalReport.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    nickname_by_id = {u.id: u.nickname for u in db.query(User).all()}
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
                uploader_nickname=nickname_by_id.get(r.uploader_id),
                abnormal_count=abnormal,
                status=r.status,
                created_at=r.created_at,
            )
        )
    return ApiResponse.ok(ReportListOut(total=total, items=items))


@router.get("/reports/{report_id}", response_model=ApiResponse[ReportDetailOut])
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = db.get(MedicalReport, report_id)
    if not report:
        raise NotFoundError("report not found")
    return ApiResponse.ok(
        ReportDetailOut(
            report=ReportOut.model_validate(report),
            metrics=[MetricOut.model_validate(m) for m in report.metrics],
        )
    )


@router.get("/reports/{report_id}/image")
def get_report_image(report_id: int, db: Session = Depends(get_db)):
    report = db.get(MedicalReport, report_id)
    if not report:
        raise NotFoundError("report not found")
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
):
    q = (
        db.query(MedicalReportMetric, MedicalReport)
        .join(MedicalReport, MedicalReportMetric.report_id == MedicalReport.id)
    )
    if item_code:
        q = q.filter(MedicalReportMetric.item_code == item_code)
    elif item_name:
        q = q.filter(MedicalReportMetric.item_name == item_name)
    if subject_id is not None:
        q = q.filter(MedicalReport.subject_id == subject_id)

    rows = q.order_by(MedicalReport.report_date.asc()).all()

    points = [
        TrendPoint(
            report_date=rep.report_date,
            value_num=metric.value_num,
            abnormal_flag=metric.abnormal_flag,
            report_id=rep.id,
        )
        for metric, rep in rows
    ]
    first = rows[0][0] if rows else None
    return ApiResponse.ok(
        TrendOut(
            item_code=item_code or (first.item_code if first else None),
            item_name=item_name or (first.item_name if first else ""),
            unit=first.unit if first else None,
            ref_low=first.ref_low if first else None,
            ref_high=first.ref_high if first else None,
            points=points,
        )
    )


@router.get("/metrics/catalog", response_model=ApiResponse[CatalogOut])
def metric_catalog(
    subject_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = (
        db.query(
            MedicalReportMetric.item_code,
            MedicalReportMetric.item_name,
            func.count(MedicalReportMetric.id),
        )
        .join(MedicalReport, MedicalReportMetric.report_id == MedicalReport.id)
    )
    if subject_id is not None:
        q = q.filter(MedicalReport.subject_id == subject_id)
    q = q.group_by(MedicalReportMetric.item_code, MedicalReportMetric.item_name)

    items = [
        CatalogItem(item_code=code, item_name=name, count=count)
        for code, name, count in q.all()
    ]
    return ApiResponse.ok(CatalogOut(items=items))
