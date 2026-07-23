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

async def upload_file_to_s3(file_obj, filename: str, content_type: str) -> str:
    """Uploads a file to AWS S3 and returns the public URL."""
    s3_client = get_s3_client()
    if not s3_client:
        # Fallback to local upload if S3 not configured
        local_path = f"uploads/{uuid.uuid4().hex}_{filename}"
        os.makedirs("uploads", exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(file_obj.read())
        # Not a complete URL, but works for fallback testing
        return f"/{local_path}"
        
    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    
    try:
        s3_client.upload_fileobj(
            file_obj,
            settings.AWS_S3_BUCKET_NAME,
            unique_filename,
            ExtraArgs={'ContentType': content_type}
        )
        
        # Build URL
        s3_url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{unique_filename}"
        return s3_url
    except ClientError as e:
        print(f"S3 Upload Error: {e}")
        raise ValueError("Failed to upload file to S3")
