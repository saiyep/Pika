"""Data models for Pika life automation service."""

from typing import Optional
from pydantic import BaseModel


class PikaRequest(BaseModel):
    """Request model for Pika service."""
    mode: str  # 'structured' or 'natural'
    task_type: Optional[str] = None
    query: Optional[str] = None
    parameters: dict = {}


class HealthMetrics(BaseModel):
    """Health metrics data model."""
    weight: float
    body_fat_percentage: Optional[float] = None
    muscle_rate: Optional[float] = None
    bmi: Optional[float] = None
    unit: str = "jin"  # 默认单位为斤


class ProcessResult(BaseModel):
    """Result model for processing tasks."""
    success: bool
    message: str
    data: Optional[dict] = None