"""安全验证工具"""
import os
import logging
from typing import Optional
from ..core.exceptions import AuthenticationError


def validate_function_key(provided_key: Optional[str]) -> bool:
    """
    验证函数密钥
    注意：在Azure Functions中，authLevel为function时，Azure会自动验证密钥
    此函数主要用于额外的安全验证
    """
    if not provided_key:
        raise AuthenticationError("缺少函数密钥")
    
    # 在实际环境中，我们通常不需要手动验证密钥，因为Azure会自动处理
    # 这里主要是为了演示目的
    expected_key = os.getenv('Pika_API_Key')
    
    if not expected_key:
        logging.warning("未配置Pika_API_Key环境变量")
        return True  # 如果没有配置，则跳过验证
    
    if provided_key != expected_key:
        raise AuthenticationError("函数密钥无效")
    
    return True


def validate_storage_key(storage_key: str) -> bool:
    """验证存储密钥"""
    if not storage_key or len(storage_key) < 10:
        raise AuthenticationError("存储密钥无效")
    
    return True