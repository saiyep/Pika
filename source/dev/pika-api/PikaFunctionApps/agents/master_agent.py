"""Master agent for Pika life automation service."""

import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from ..core.models import PikaRequest
from ..tools.storage_tool import build_blob_path
from ..tools.notion_tool import create_or_update_health_entry
from ..tools.vision_tool import extract_health_metrics
from ..core.exceptions import InvalidTaskTypeException
import base64


class MasterAgent(BaseAgent):
    """Master agent that routes requests to specialized agents."""
    
    def __init__(self):
        super().__init__("MasterAgent")
        self.agents = {
            'health_metrics': self._route_to_health_metrics
        }
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request and route to appropriate agent."""
        try:
            request = PikaRequest(**request_data)
            
            if request.mode == 'structured':
                if request.task_type not in self.agents:
                    raise InvalidTaskTypeException(f"Invalid task type: {request.task_type}")
                
                # Route to the appropriate agent
                result = await self.agents[request.task_type](request.parameters)
                return {"success": True, "data": result, "message": f"{request.task_type} processed successfully"}
            
            elif request.mode == 'natural':
                # For now, handle as health metrics by default
                # In a full implementation, we'd parse the natural language query
                params = request.parameters
                params['query'] = request.query
                result = await self.agents['health_metrics'](params)
                return {"success": True, "data": result, "message": "Natural language request processed successfully"}
            
            else:
                return {"success": False, "message": f"Invalid mode: {request.mode}"}
        
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _route_to_health_metrics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Route to health metrics agent."""
        from .health_metrics_agent import HealthMetricsAgent
        agent = HealthMetricsAgent()
        return await agent.execute(params)