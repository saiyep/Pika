"""Agent基类定义"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic_ai import Agent


class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, system_prompt: str, agent_name: str):
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.agent = Agent(
            "openai",  # 实际上可能是不同的后端，这里使用通用接口
            system_prompt=system_prompt
        )
        self.logger = logging.getLogger(f"Pika.{agent_name}")
    
    @abstractmethod
    async def process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求的抽象方法"""
        pass