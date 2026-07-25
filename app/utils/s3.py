import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
import uuid
import os

def get_s3_client():
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY or not settings.AWS_S3_BUCKET_NAME:
        return None
        
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

from app.services.s3_utils import s3_service

async def upload_file_to_s3(file_obj, filename: str, content_type: str) -> str:
    """Uploads a file to AWS S3 and returns the public URL."""
    if s3_service.s3_client:
        if hasattr(file_obj, "read"):
            file_bytes = file_obj.read()
        else:
            file_bytes = file_obj
        return await s3_service.upload_bytes(file_bytes, filename=filename, content_type=content_type, folder="uploads")
    else:
        raise ValueError("AWS S3 is not configured.")

