"""Notion API操作工具"""
import asyncio
import logging
from datetime import date
from typing import Optional
from notion_client import AsyncClient
from ..core.config import get_required_config
from ..core.models import HealthMetrics
from ..core.exceptions import NotionError


async def create_or_update_health_entry(target_date: date, metrics: HealthMetrics) -> dict:
    """在Notion数据库中创建或更新健康条目"""
    try:
        config = get_required_config()
        api_key = config['notion_api_key']
        database_id = config['databases']['health_metrics']
        
        notion = AsyncClient(auth=api_key)
        
        # 格式化日期为Notion接受的格式
        formatted_date = target_date.isoformat()
        
        # 查询是否已存在当天的记录
        query_result = await notion.databases.query(
            database_id=database_id,
            filter={
                "property": "Date",  # 假设数据库中有一个名为"Date"的属性
                "date": {
                    "equals": formatted_date
                }
            }
        )
        
        properties = {
            "Date": {
                "date": {"start": formatted_date}
            },
            "Weight (jin)": {
                "number": metrics.weight
            }
        }
        
        # 添加可选字段
        if metrics.body_fat_percentage is not None:
            properties["Body Fat %"] = {"number": metrics.body_fat_percentage}
        
        if metrics.muscle_rate is not None:
            properties["Muscle Rate %"] = {"number": metrics.muscle_rate}
        
        if metrics.bmi is not None:
            properties["BMI"] = {"number": metrics.bmi}
        
        if query_result.get("results"):
            # 更新现有页面
            page_id = query_result["results"][0]["id"]
            response = await notion.pages.update(
                page_id=page_id,
                properties=properties
            )
            logging.info(f"更新健康数据页面: {page_id}")
        else:
            # 创建新页面
            response = await notion.pages.create(
                parent={"database_id": database_id},
                properties=properties
            )
            logging.info(f"创建健康数据页面: {response.get('id')}")
        
        return response
    
    except Exception as e:
        logging.error(f"Notion操作失败: {str(e)}")
        raise NotionError(f"Notion操作失败: {str(e)}")