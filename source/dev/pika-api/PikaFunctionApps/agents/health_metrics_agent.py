"""Health metrics agent for Pika life automation service."""

import logging
import base64
from typing import Dict, Any
from .base_agent import BaseAgent
from ..tools.storage_tool import download_blob_with_key
from ..tools.vision_tool import extract_health_metrics
from ..tools.notion_tool import create_or_update_health_entry
from ..core.models import HealthMetrics
from ..core.exceptions import StorageAuthenticationException, VisionProcessingException, NotionUpdateException


class HealthMetricsAgent(BaseAgent):
    """Specialized agent for processing health metrics from images."""
    
    def __init__(self):
        super().__init__("HealthMetricsAgent")
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute health metrics processing."""
        try:
            # Extract parameters
            storage_key = params.get('storage_key')
            blob_path = params.get('blob_path')
            date_str = params.get('date')
            
            if not storage_key:
                raise StorageAuthenticationException("Storage key is required")
            
            if not blob_path:
                raise ValueError("Blob path is required")
            
            if not date_str:
                raise ValueError("Date is required")
            
            # Download image from Azure Blob Storage
            self.logger.info(f"Downloading image from {blob_path}")
            image_bytes = await download_blob_with_key(storage_key, "data", blob_path)
            
            # Encode image to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Extract health metrics using vision tool
            self.logger.info("Extracting health metrics from image")
            metrics = await extract_health_metrics(image_base64)
            
            # Update Notion database
            self.logger.info("Updating Notion database")
            notion_result = await create_or_update_health_entry(date_str, metrics)
            
            # TODO: Move the processed file to processed folder
            # await move_to_processed(blob_path, storage_key)
            
            return {
                "original_image_path": blob_path,
                "date": date_str,
                "metrics": metrics.dict(),
                "notion_update_result": notion_result
            }
        
        except Exception as e:
            self.logger.error(f"Error in HealthMetricsAgent: {str(e)}")
            raise e