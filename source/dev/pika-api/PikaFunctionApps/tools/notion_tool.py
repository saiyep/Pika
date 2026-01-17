"""Notion tools for updating health metrics."""

import logging
import os
import asyncio
from typing import Dict, Any, Optional
from notion_client import AsyncClient
from ..core.models import HealthMetrics


async def create_or_update_health_entry(date_str: str, metrics: HealthMetrics) -> Dict[str, Any]:
    """Create or update a health metrics entry in Notion database."""
    try:
        # Get API key and database ID from environment
        api_key = os.getenv('Notion_API_Key')
        database_id = os.getenv('Health_Metrics_Notion_DB_ID')
        
        if not api_key:
            raise ValueError("Notion API key not found in environment variables")
        
        if not database_id:
            raise ValueError("Health Metrics Notion DB ID not found in environment variables")
        
        # Initialize the Notion client
        notion = AsyncClient(auth=api_key)
        
        # Check if an entry for this date already exists
        existing_pages = await _find_page_by_date(notion, database_id, date_str)
        
        if existing_pages:
            # Update the existing page
            page_id = existing_pages[0]['id']
            response = await _update_existing_page(notion, page_id, metrics, date_str)
            return {"status": "updated", "page_id": page_id, "response": response}
        else:
            # Create a new page
            response = await _create_new_page(notion, database_id, metrics, date_str)
            return {"status": "created", "response": response}
    
    except Exception as e:
        logging.error(f"Error in Notion operation: {str(e)}")
        raise e


async def _find_page_by_date(notion: AsyncClient, database_id: str, date_str: str) -> list:
    """Find pages in the database with the given date."""
    try:
        filter_criteria = {
            "property": "Date",  # Assuming the date property in Notion DB is named "Date"
            "date": {
                "equals": date_str
            }
        }
        
        response = await notion.databases.query(
            database_id=database_id,
            filter={"and": [filter_criteria]}
        )
        
        return response.get("results", [])
    except Exception as e:
        logging.error(f"Error finding page by date: {str(e)}")
        return []


async def _update_existing_page(notion: AsyncClient, page_id: str, metrics: HealthMetrics, date_str: str) -> Dict[str, Any]:
    """Update an existing Notion page with new health metrics."""
    try:
        properties = _build_properties(metrics, date_str)
        response = await notion.pages.update(page_id=page_id, properties=properties)
        return response
    except Exception as e:
        logging.error(f"Error updating existing page: {str(e)}")
        raise e


async def _create_new_page(notion: AsyncClient, database_id: str, metrics: HealthMetrics, date_str: str) -> Dict[str, Any]:
    """Create a new Notion page with health metrics."""
    try:
        properties = _build_properties(metrics, date_str)
        
        # Create the new page
        response = await notion.pages.create(
            parent={"database_id": database_id},
            properties=properties
        )
        
        return response
    except Exception as e:
        logging.error(f"Error creating new page: {str(e)}")
        raise e


def _build_properties(metrics: HealthMetrics, date_str: str) -> Dict[str, Any]:
    """Build the properties dictionary for Notion API."""
    properties = {
        "Date": {
            "date": {
                "start": date_str
            }
        },
        "Weight": {
            "number": metrics.weight
        }
    }
    
    if metrics.body_fat_percentage is not None:
        properties["Body Fat %"] = {
            "number": metrics.body_fat_percentage
        }
    
    if metrics.muscle_rate is not None:
        properties["Muscle Rate %"] = {
            "number": metrics.muscle_rate
        }
    
    if metrics.bmi is not None:
        properties["BMI"] = {
            "number": metrics.bmi
        }
    
    return properties