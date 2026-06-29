from datetime import date, datetime

from sqlalchemy import Boolean, JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    report_type: Mapped[str] = mapped_column(String, default="unknown", index=True)
    report_type_label: Mapped[str | None] = mapped_column(String, nullable=True)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    hospital: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    image_path: Mapped[str] = mapped_column(String, nullable=False)
    image_paths: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, default="parsed")  # uploaded/parsing/parsed/failed
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    metrics: Mapped[list["MedicalReportMetric"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="MedicalReportMetric.seq"
    )


class MedicalReportMetric(Base):
    __tablename__ = "medical_report_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("medical_reports.id", ondelete="CASCADE"), index=True
    )
    item_name: Mapped[str] = mapped_column(String, nullable=False)
    item_code: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    value_text: Mapped[str | None] = mapped_column(String, nullable=True)
    value_num: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    ref_range: Mapped[str | None] = mapped_column(String, nullable=True)
    ref_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ref_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    abnormal_flag: Mapped[str | None] = mapped_column(String, nullable=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)

    report: Mapped["MedicalReport"] = relationship(back_populates="metrics")


class MedicalAclGrant(Base):
    __tablename__ = "medical_acl_grants"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "grantee_user_id", name="uq_medical_acl_owner_grantee"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    grantee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    actions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MedicalReportCategory(Base):
    __tablename__ = "medical_report_categories"
    __table_args__ = (
        UniqueConstraint("user_id", "category_key", name="uq_medical_category_user_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("family_groups.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category_key: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MedicalMetricDictionary(Base):
    __tablename__ = "medical_metric_dictionary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_key: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    canonical_name: Mapped[str] = mapped_column(String, nullable=False)
    canonical_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    category_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MedicalMetricAlias(Base):
    __tablename__ = "medical_metric_aliases"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "dictionary_id",
            "alias_name",
            "alias_unit",
            "hospital_hint",
            name="uq_medical_metric_alias_owner_compound",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    dictionary_id: Mapped[int] = mapped_column(ForeignKey("medical_metric_dictionary.id", ondelete="CASCADE"), index=True)
    alias_name: Mapped[str] = mapped_column(String, nullable=False)
    alias_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    hospital_hint: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    report_type_hint: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MedicalReportMetricMap(Base):
    __tablename__ = "medical_report_metric_maps"
    __table_args__ = (
        UniqueConstraint("report_metric_id", name="uq_medical_report_metric_map_metric"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_metric_id: Mapped[int] = mapped_column(ForeignKey("medical_report_metrics.id", ondelete="CASCADE"), index=True)
    dictionary_id: Mapped[int | None] = mapped_column(ForeignKey("medical_metric_dictionary.id", ondelete="SET NULL"), nullable=True, index=True)
    alias_id: Mapped[int | None] = mapped_column(ForeignKey("medical_metric_aliases.id", ondelete="SET NULL"), nullable=True, index=True)
    match_status: Mapped[str] = mapped_column(String, nullable=False, server_default="unmapped")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    mapped_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MedicalUserFocusMetric(Base):
    __tablename__ = "medical_user_focus_metrics"
    __table_args__ = (
        UniqueConstraint("user_id", "dictionary_id", name="uq_medical_user_focus_metric"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    dictionary_id: Mapped[int] = mapped_column(ForeignKey("medical_metric_dictionary.id", ondelete="CASCADE"), index=True)
    category_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
