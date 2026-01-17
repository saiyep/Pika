"""Configuration management for Pika life automation service."""

import os


def get_config():
    """Load and return configuration from environment variables."""
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