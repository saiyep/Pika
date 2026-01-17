"""Azure Storage操作工具"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from azure.storage.blob import BlobServiceClient
from ..core.config import get_required_config
from ..core.exceptions import StorageError


async def download_blob_with_key(storage_key: str, container: str, blob_path: str) -> bytes:
    """使用存储密钥下载Blob"""
    try:
        config = get_required_config()
        account_name = config['storage']['account_name']
        
        connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={storage_key};EndpointSuffix=core.windows.net"
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        blob_client = blob_service_client.get_blob_client(container=container, blob=blob_path)
        download_stream = blob_client.download_blob()
        
        return download_stream.readall()
    except Exception as e:
        logging.error(f"下载Blob失败: {str(e)}")
        raise StorageError(f"下载Blob失败: {str(e)}")


async def move_to_processed(original_path: str, storage_key: str) -> str:
    """将文件移动到processed目录"""
    try:
        config = get_required_config()
        account_name = config['storage']['account_name']
        # 假设容器名为"data"
        container = "data"
        
        connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={storage_key};EndpointSuffix=core.windows.net"
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # 构建目标路径
        path_parts = original_path.split('/')
        task_type = path_parts[0]  # health, running, swimming等
        original_filename = path_parts[-1]
        
        # 获取当前年月
        now = datetime.now()
        year = str(now.year)
        month = f"{now.month:02d}"
        
        # 新路径
        new_path = f"{task_type}/processed/{year}/{month}/{original_filename}"
        
        # 复制到新位置
        source_blob = f"https://{account_name}.blob.core.windows.net/{container}/{original_path}"
        dest_blob_client = blob_service_client.get_blob_client(container=container, blob=new_path)
        dest_blob_client.start_copy_from_url(source_blob)
        
        # 删除原文件
        source_blob_client = blob_service_client.get_blob_client(container=container, blob=original_path)
        source_blob_client.delete_blob()
        
        logging.info(f"文件已移动: {original_path} -> {new_path}")
        return new_path
    except Exception as e:
        logging.error(f"移动文件失败: {str(e)}")
        raise StorageError(f"移动文件失败: {str(e)}")


def build_blob_path(task_type: str, date: datetime, filename: str) -> str:
    """构建存储路径"""
    year = date.strftime('%Y')
    month = date.strftime('%m')
    return f"{task_type}/{year}/{month}/{filename}"