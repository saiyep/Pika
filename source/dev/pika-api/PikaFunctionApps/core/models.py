"""数据模型定义"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date


class PikaRequest(BaseModel):
    """Pika服务请求模型"""
    mode: str = Field(..., description="请求模式: structured | natural")
    task_type: Optional[str] = Field(None, description="任务类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    query: Optional[str] = Field(None, description="自然语言查询")


class PikaResponse(BaseModel):
    """Pika服务响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthMetrics(BaseModel):
    """健康指标数据模型"""
    weight: float = Field(..., description="体重")
    weight_unit: str = Field("jin", description="单位（直接从图片读取，通常为斤）")
    body_fat_percentage: Optional[float] = Field(None, description="体脂率")
    muscle_rate: Optional[float] = Field(None, description="肌肉率")
    bmi: Optional[float] = Field(None, description="BMI")


class TaskContext(BaseModel):
    """任务上下文模型"""
    date: date
    storage_key: str
    blob_path: str
    extra_params: Optional[Dict[str, Any]] = Field(default_factory=dict)