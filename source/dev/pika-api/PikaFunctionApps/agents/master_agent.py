"""MasterAgent智能调度器"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic_ai import Agent, RunContext
from ..core.models import PikaRequest, TaskContext, HealthMetrics
from ..tools.storage_tool import build_blob_path
from ..tools.vision_tool import extract_health_metrics
from ..tools.notion_tool import create_or_update_health_entry
from ..utils.date_utils import parse_date_string
from ..core.exceptions import ValidationError, ProcessingError
from .base_agent import BaseAgent


class MasterAgent(BaseAgent):
    """MasterAgent - 智能调度器"""
    
    def __init__(self):
        system_prompt = """
        你是一个智能调度器，负责解析用户的自然语言请求并将其路由到适当的处理模块。
        你的任务包括：
        1. 识别任务类型（目前主要是health_metrics）
        2. 从自然语言中提取关键参数（日期、存储路径等）
        3. 将请求路由到相应的专业Agent进行处理
        4. 整合结果并返回给用户
        """
        super().__init__(system_prompt, "MasterAgent")
        
        # 初始化专业agent
        self.health_agent = HealthMetricsAgent()
    
    async def process_request(self, request: PikaRequest) -> Dict[str, Any]:
        """处理请求入口"""
        try:
            self.logger.info(f"收到请求，模式: {request.mode}, 类型: {request.task_type}")
            
            if request.mode == "structured":
                return await self._handle_structured_request(request)
            elif request.mode == "natural":
                return await self._handle_natural_language_request(request)
            else:
                raise ValidationError(f"不支持的请求模式: {request.mode}")
                
        except Exception as e:
            self.logger.error(f"处理请求时发生错误: {str(e)}")
            return {
                "success": False,
                "message": "请求处理失败",
                "error": str(e)
            }
    
    async def _handle_structured_request(self, request: PikaRequest) -> Dict[str, Any]:
        """处理结构化请求"""
        if not request.task_type:
            raise ValidationError("结构化请求必须指定task_type")
        
        if request.task_type == "health_metrics":
            return await self._route_to_health_metrics(request.parameters)
        else:
            raise ValidationError(f"未知的任务类型: {request.task_type}")
    
    async def _handle_natural_language_request(self, request: PikaRequest) -> Dict[str, Any]:
        """处理自然语言请求"""
        if not request.query:
            raise ValidationError("自然语言请求必须包含query字段")
        
        # 解析自然语言请求
        parsed_result = await self._parse_natural_language_request(request.query)
        
        # 根据解析结果路由
        if parsed_result.get("task_type") == "health_metrics":
            return await self._route_to_health_metrics(parsed_result.get("parameters", {}))
        else:
            raise ValidationError(f"无法处理的任务类型: {parsed_result.get('task_type')}")
    
    async def _parse_natural_language_request(self, query: str) -> Dict[str, Any]:
        """解析自然语言请求"""
        # 这里简化处理，实际应用中可能需要更复杂的NLP处理
        self.logger.info(f"解析自然语言请求: {query}")
        
        # 示例解析逻辑 - 实际实现可能需要更复杂的解析
        if "健康" in query or "体重" in query or "体脂" in query:
            return {
                "task_type": "health_metrics",
                "parameters": {
                    # 这里可以尝试从query中提取更多参数
                }
            }
        
        # 默认返回健康指标类型
        return {
            "task_type": "health_metrics",
            "parameters": {}
        }
    
    async def _route_to_health_metrics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """路由到健康数据Agent"""
        self.logger.info("路由到健康数据处理Agent")
        return await self.health_agent.process(params)


class HealthMetricsAgent(BaseAgent):
    """健康数据专业Agent"""
    
    def __init__(self):
        system_prompt = """
        你是一个专业的健康数据分析器，专门处理健康指标数据。
        你需要：
        1. 从图像中提取体重（斤）、体脂率、肌肉率、BMI等健康指标
        2. 将数据更新到Notion数据库中
        3. 返回处理结果
        """
        super().__init__(system_prompt, "HealthMetricsAgent")
    
    async def process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理健康指标数据"""
        try:
            required_params = ['storage_key', 'blob_path']
            for param in required_params:
                if param not in params:
                    raise ValidationError(f"缺少必需参数: {param}")
            
            # 提取参数
            storage_key = params['storage_key']
            blob_path = params['blob_path']
            date_str = params.get('date', datetime.now().strftime('%Y-%m-%d'))
            
            # 解析日期
            date_obj = parse_date_string(date_str)
            
            # 从存储中下载图片并提取健康指标
            self.logger.info(f"正在处理健康数据，路径: {blob_path}")
            health_metrics = await extract_health_metrics(storage_key, blob_path)
            
            # 更新到Notion数据库
            notion_result = await create_or_update_health_entry(date_obj, health_metrics)
            
            # 移动文件到processed目录
            processed_path = await self._move_to_processed(blob_path, storage_key)
            
            return {
                "success": True,
                "message": "健康数据处理成功",
                "data": {
                    "original_path": blob_path,
                    "processed_path": processed_path,
                    "metrics": health_metrics.dict(),
                    "notion_result": notion_result
                }
            }
            
        except Exception as e:
            self.logger.error(f"处理健康数据时发生错误: {str(e)}")
            raise ProcessingError(f"健康数据处理失败: {str(e)}")
    
    async def _move_to_processed(self, original_path: str, storage_key: str) -> str:
        """移动文件到processed目录"""
        from ..tools.storage_tool import move_to_processed
        return await move_to_processed(original_path, storage_key)