"""OpenRouter视觉模型工具"""
import asyncio
import base64
import logging
from typing import Optional
from openai import AsyncOpenAI
from ..core.config import get_required_config
from ..core.models import HealthMetrics
from ..core.exceptions import VisionError
from .storage_tool import download_blob_with_key


async def extract_health_metrics(storage_key: str, blob_path: str) -> HealthMetrics:
    """从图像中提取健康指标"""
    try:
        # 下载图像
        image_bytes = await download_blob_with_key(storage_key, "data", blob_path)
        
        # 将图像转换为base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # 获取API配置
        config = get_required_config()
        api_key = config['openrouter_key']
        
        # 使用OpenRouter API
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        
        # 调用视觉模型
        response = await client.chat.completions.create(
            model="qwen-2.5-vl",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请从这张健康监测截图中提取以下信息：体重、体脂率(%)、肌肉率(%)、BMI。以JSON格式返回，例如：{'weight': 70.5, 'body_fat_percentage': 15.2, 'muscle_rate': 45.3, 'bmi': 22.4}"
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # 解析返回结果
        result_text = response.choices[0].message.content
        import json
        data = json.loads(result_text)
        
        # 创建健康指标对象
        weight = data.get('weight', 0)
        # 将公斤转换为市斤
        converted_weight = weight * 2 if weight else None
        
        health_metrics = HealthMetrics(
            weight=weight,
            body_fat_percentage=data.get('body_fat_percentage'),
            muscle_rate=data.get('muscle_rate'),
            bmi=data.get('bmi'),
            weight_unit='kg',
            converted_weight=converted_weight
        )
        
        logging.info(f"成功提取健康指标: {health_metrics}")
        return health_metrics
        
    except Exception as e:
        logging.error(f"提取健康指标失败: {str(e)}")
        raise VisionError(f"提取健康指标失败: {str(e)}")