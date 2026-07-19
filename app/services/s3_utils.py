import boto3
import mimetypes
import uuid
import os
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings

class S3Service:
    def __init__(self):
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_S3_BUCKET_NAME:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        else:
            self.s3_client = None
            
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.region = settings.AWS_REGION

    def _upload_sync(self, file_obj, filename, content_type):
        self.s3_client.upload_fileobj(
            file_obj,
            self.bucket_name,
            filename,
            ExtraArgs={"ContentType": content_type}
        )
        url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{filename}"
        return url

    async def upload_file(self, file: UploadFile, folder: str = "") -> str:
        """
        Uploads a FastAPI UploadFile to AWS S3 asynchronously and returns the public URL.
        """
        if not self.s3_client:
            raise Exception("AWS S3 is not configured in .env.")
            
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        s3_key = f"{folder}/{unique_filename}" if folder else unique_filename
        
        content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        
        url = await run_in_threadpool(self._upload_sync, file.file, s3_key, content_type)
        return url

    async def upload_bytes(self, file_bytes: bytes, filename: str, content_type: str, folder: str = "") -> str:
        """
        Uploads raw bytes to AWS S3 asynchronously and returns the public URL.
        """
        import io
        if not self.s3_client:
            raise Exception("AWS S3 is not configured in .env.")
            
        file_ext = os.path.splitext(filename)[1] if filename else ""
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        s3_key = f"{folder}/{unique_filename}" if folder else unique_filename
        
        url = await run_in_threadpool(self._upload_sync, io.BytesIO(file_bytes), s3_key, content_type)
        return url

    def _delete_sync(self, key: str):
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)

    async def delete_file(self, file_url: str):
        """
        Deletes a file from AWS S3 asynchronously.
        """
        if not self.s3_client or "amazonaws.com" not in file_url:
            return
            
        try:
            key = file_url.split(".amazonaws.com/")[1]
            await run_in_threadpool(self._delete_sync, key)
        except Exception:
            pass

s3_service = S3Service()
