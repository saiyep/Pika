from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    openid: str
    nickname: str | None = None
    role: str | None = None


class LoginIn(BaseModel):
    code: str
    nickname: str | None = None


class LoginOut(BaseModel):
    token: str
    user: UserOut


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
    report_type: str
    report_type_label: str | None = None
    report_date: date | None = None
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
