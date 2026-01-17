"""Azure Storage tools for Pika life automation service."""

import logging
from typing import Optional
from azure.storage.blob import BlobServiceClient, BlobProperties
from ..utils.path_utils import build_blob_path, get_processed_path


async def download_blob_with_key(storage_key: str, container: str, blob_path: str) -> bytes:
    """Download a blob from Azure Storage using the provided storage key."""
    try:
        # Get the account name to construct the URL properly
        from ..core.config import get_config
        config = get_config()
        account_name = config['storage']['account_name']
        
        # Create a BlobServiceClient using the storage key
        account_url = f"https://{account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=storage_key
        )
        
        # Get a blob client
        blob_client = blob_service_client.get_blob_client(
            container=container, blob=blob_path
        )
        
        # Download the blob content
        download_stream = blob_client.download_blob()
        return download_stream.readall()
    
    except Exception as e:
        logging.error(f"Failed to download blob {blob_path}: {str(e)}")
        raise e


async def move_to_processed(original_path: str, storage_key: str, container: str = "filesystem") -> bool:
    """Move a blob to the processed folder."""
    try:
        # Get the account name to construct the URL properly
        from ..core.config import get_config
        config = get_config()
        account_name = config['storage']['account_name']
        
        # Create a BlobServiceClient using the storage key
        account_url = f"https://{account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=storage_key
        )
        
        # Get the original blob client
        original_blob_client = blob_service_client.get_blob_client(
            container=container, blob=original_path
        )
        
        # Verify that the original blob exists
        props = await original_blob_client.get_blob_properties()
        
        # Determine the new path in the processed folder
        path_parts = original_path.split('/')
        task_type = path_parts[0]  # health, running, swimming, etc.
        new_path = get_processed_path(original_path, task_type)
        
        # Get a client for the destination blob
        dest_blob_client = blob_service_client.get_blob_client(
            container=container, blob=new_path
        )
        
        # Start copying the blob to the new location
        copy_operation = dest_blob_client.start_copy_from_url(original_blob_client.url)
        
        # Wait for the copy operation to complete
        # In a real implementation, we might want to handle this asynchronously
        import time
        while dest_blob_client.get_blob_properties().copy.status == 'pending':
            time.sleep(1)
        
        # Check if the copy was successful
        if dest_blob_client.get_blob_properties().copy.status == 'success':
            # Delete the original blob after copying
            original_blob_client.delete_blob()
            return True
        else:
            logging.error(f"Failed to copy blob from {original_path} to {new_path}, copy status: {dest_blob_client.get_blob_properties().copy.status}")
            return False
            
    except Exception as e:
        logging.error(f"Failed to move blob {original_path} to processed folder: {str(e)}")
        return False