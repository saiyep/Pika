"""健康数据专业Agent - 已合并到master_agent中，此文件保留用于未来扩展"""
from typing import Dict, Any
from .base_agent import BaseAgent


class HealthMetricsAgentTemplate(BaseAgent):
    """健康数据专业Agent模板 - 保留供参考"""
    
    def __init__(self):
        system_prompt = """
        你是一个专业的健康数据分析器，专门处理健康指标数据。
        你需要：
        1. 从图像中提取体重、体脂率、肌肉率、BMI等健康指标
        2. 将体重从公斤(kg)转换为市斤
        3. 将数据更新到Notion数据库中
        4. 返回处理结果
        """
        super().__init__(system_prompt, "HealthMetricsAgent")
    
    async def process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理健康指标数据"""
        # 此功能已在master_agent.py中实现
        # 保留此文件用于未来可能的模块分离
        pass