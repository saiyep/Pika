"""Vision tools for extracting health metrics from images."""
import logging
import os
import re
import asyncio
from openai import AsyncOpenAI
from ..core.models import HealthMetrics


async def extract_health_metrics(image_base64: str) -> HealthMetrics:
    """Extract health metrics from an image using OpenRouter's vision model."""
    try:
        # Get API key from environment
        api_key = os.getenv('OpenRouter_API_Key')
        if not api_key:
            raise ValueError("OpenRouter API key not found in environment variables")
        
        # Initialize the OpenAI client with OpenRouter
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        
        # Prepare the prompt for extracting health metrics
        prompt = """
        Analyze this health tracking screenshot and extract the following metrics:
        - Weight (in 斤 - jin)
        - Body fat percentage (if available)
        - Muscle rate (if available)
        - BMI (if available)
        
        Notes:
        - Weight values in this app are displayed in 斤 (jin), so extract the numerical value as-is without conversion
        - If some metrics are not available, return null for those fields
        - Return only the numerical values without units
        - Pay attention to the exact numbers shown in the image
        """
        
        # Call the vision model
        response = await client.chat.completions.create(
            model="qwen/qwen-2.5-vl-7b-instruct:free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.1
        )
        
        # Extract the response content
        content = response.choices[0].message.content
        
        # Parse the extracted metrics
        # Look for weight in 斤 (should be present according to our memory)
        weight_match = re.search(r'weight\D*([0-9.]+)', content.lower())
        weight = float(weight_match.group(1)) if weight_match else 0.0
        
        # Look for body fat percentage
        body_fat_match = re.search(r'fat\D*([0-9.]+)%', content.lower())
        body_fat_percentage = float(body_fat_match.group(1)) if body_fat_match else None
        
        # Look for muscle rate
        muscle_rate_match = re.search(r'muscle\D*([0-9.]+)%', content.lower())
        muscle_rate = float(muscle_rate_match.group(1)) if muscle_rate_match else None
        
        # Look for BMI
        bmi_match = re.search(r'bmi\D*([0-9.]+)', content.lower())
        bmi = float(bmi_match.group(1)) if bmi_match else None
        
        # Create and return the HealthMetrics object
        return HealthMetrics(
            weight=weight,
            body_fat_percentage=body_fat_percentage,
            muscle_rate=muscle_rate,
            bmi=bmi,
            unit="jin"
        )
    
    except Exception as e:
        logging.error(f"Error extracting health metrics: {str(e)}")
        raise e