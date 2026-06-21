from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    item_name: str
    item_code: str | None = None
    value_text: str | None = None
    value_num: float | None = None
    unit: str | None = None
    ref_range: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    abnormal_flag: str | None = None
    seq: int = 0


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uploader_id: int
    subject_id: int | None = None
    subject_nickname: str | None = None
    report_type: str
    report_type_label: str | None = None
    report_date: date | None = None
    hospital: str | None = None
    status: str
    created_at: datetime


class ReportDetailOut(BaseModel):
    report: ReportOut
    metrics: list[MetricOut]


class ReportListItem(BaseModel):
    id: int
    report_type: str
    report_type_label: str | None = None
    report_date: date | None = None
    hospital: str | None = None
    subject_id: int | None = None
    subject_nickname: str | None = None
    uploader_nickname: str | None = None
    abnormal_count: int = 0
    status: str
    created_at: datetime


class ReportListOut(BaseModel):
    total: int
    items: list[ReportListItem]


class TrendPoint(BaseModel):
    report_date: date | None = None
    value_num: float | None = None
    abnormal_flag: str | None = None
    report_id: int
    hospital: str | None = None


class TrendOut(BaseModel):
    item_code: str | None = None
    item_name: str
    unit: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    points: list[TrendPoint]


class CatalogItem(BaseModel):
    item_code: str | None = None
    item_name: str
    count: int


class CatalogOut(BaseModel):
    items: list[CatalogItem]


class DraftMetric(BaseModel):
    item_name: str
    item_code: str | None = None
    value_text: str | None = None
    value_num: float | None = None
    unit: str | None = None
    ref_range: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    abnormal_flag: str | None = None
    seq: int = 0


class DraftOut(BaseModel):
    draft_id: str
    is_lab_report: bool = True
    report_type: str
    report_type_label: str | None = None
    report_date: date | None = None
    hospital: str | None = None
    metrics: list[DraftMetric]


class DraftCommitIn(BaseModel):
    report_type: str = "unknown"
    report_type_label: str | None = None
    report_date: date | None = None
    hospital: str | None = None
    metrics: list[DraftMetric]


class ReportUpdateIn(BaseModel):
    report_type: str = "unknown"
    report_type_label: str | None = None
    report_date: date | None = None
    hospital: str | None = None
    subject_id: int | None = None
    metrics: list[DraftMetric]


class MedicalAclGrantIn(BaseModel):
    grantee_user_id: int
    actions: list[str]


class MedicalAclGrantOut(BaseModel):
    owner_user_id: int
    grantee_user_id: int
    actions: list[str]


class MedicalAclListOut(BaseModel):
    owner_user_id: int
    grants: list[MedicalAclGrantOut]
