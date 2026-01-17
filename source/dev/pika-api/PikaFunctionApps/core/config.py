"""配置管理"""
import os
from typing import Dict, Any


def get_config() -> Dict[str, Any]:
    """获取配置"""
    return {
        'function_key': os.getenv('AzureWebJobsStorage'),  # Functions运行时使用的存储账户
        'pika_api_key': os.getenv('Pika_API_Key'),         # 业务逻辑API密钥
        'notion_api_key': os.getenv('Notion_API_Key'),
        'openrouter_key': os.getenv('OpenRouter_API_Key'),
        'databases': {
            'health_metrics': os.getenv('Health_Metrics_Notion_DB_ID'),
            'running_log': os.getenv('Running_Log_Notion_DB_ID')
        },
        'storage': {
            'account_name': os.getenv('Azure_Storage_Account_Name'),
            'account_key': os.getenv('Azure_Storage_Account_Key_default')
        }
    }


def get_required_config() -> Dict[str, Any]:
    """获取必需的配置项，如果缺失则抛出异常"""
    config = get_config()
    
    required_keys = [
        'pika_api_key',
        'notion_api_key', 
        'openrouter_key',
        'databases',
        'storage'
    ]
    
    for key in required_keys:
        if not config.get(key):
            raise ValueError(f"缺少必需的配置项: {key}")
    
    if not config['databases']['health_metrics']:
        raise ValueError("缺少必需的配置项: Health_Metrics_Notion_DB_ID")
    
    if not config['storage']['account_name'] or not config['storage']['account_key']:
        raise ValueError("缺少必需的存储配置项: Azure_Storage_Account_Name 或 Azure_Storage_Account_Key_default")
    
    return config