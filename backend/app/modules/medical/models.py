from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
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
