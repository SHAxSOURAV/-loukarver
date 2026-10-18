import boto3
import mimetypes
import uuid
import os
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings

from botocore.config import Config

class S3Service:
    def __init__(self):
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.region = settings.AWS_REGION or "eu-north-1"

        if settings.AWS_ACCESS_KEY_ID and settings.AWS_S3_BUCKET_NAME:
            s3_config = Config(
                region_name=self.region,
                signature_version='s3v4',
                s3={'addressing_style': 'virtual'}
            )
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                endpoint_url=f"https://s3.{self.region}.amazonaws.com",
                config=s3_config
            )
        else:
            self.s3_client = None

    def _upload_sync(self, file_obj, filename, content_type):
        self.s3_client.upload_fileobj(
            file_obj,
            self.bucket_name,
            filename,
            ExtraArgs={"ContentType": content_type}
        )
        url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{filename}"
        return url

    def _save_local_bytes(self, file_bytes: bytes, filename: str, folder: str = "") -> str:
        target_dir = os.path.join("uploads", folder) if folder else "uploads"
        os.makedirs(target_dir, exist_ok=True)
        unique_filename = f"{uuid.uuid4().hex}_{filename}" if filename else f"{uuid.uuid4().hex}.bin"
        filepath = os.path.join(target_dir, unique_filename)
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        # Normalize slashes for URL
        rel_path = filepath.replace("\\", "/")
        return f"/{rel_path}"

    async def upload_file(self, file: UploadFile, folder: str = "") -> str:
        """
        Uploads a FastAPI UploadFile to AWS S3 asynchronously and returns the public URL.
        Falls back to local disk storage if AWS S3 is not configured.
        """
        file_bytes = await file.read()
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        s3_key = f"{folder}/{unique_filename}" if folder else unique_filename
        content_type = file.content_type or (mimetypes.guess_type(file.filename)[0] if file.filename else None) or "application/octet-stream"

        if self.s3_client:
            try:
                import io
                url = await run_in_threadpool(self._upload_sync, io.BytesIO(file_bytes), s3_key, content_type)
                return url
            except Exception as e:
                print(f"[S3Service Warning] S3 Upload failed, using local storage fallback: {e}")

        # Fallback to local storage
        return await run_in_threadpool(self._save_local_bytes, file_bytes, unique_filename, folder)

    async def upload_bytes(self, file_bytes: bytes, filename: str, content_type: str, folder: str = "") -> str:
        """
        Uploads raw bytes to AWS S3 asynchronously and returns the public URL.
        Falls back to local disk storage if AWS S3 is not configured.
        """
        import io
        file_ext = os.path.splitext(filename)[1] if filename else ""
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        s3_key = f"{folder}/{unique_filename}" if folder else unique_filename

        if self.s3_client:
            try:
                url = await run_in_threadpool(self._upload_sync, io.BytesIO(file_bytes), s3_key, content_type)
                return url
            except Exception as e:
                print(f"[S3Service Warning] S3 upload_bytes failed, using local storage fallback: {e}")

        # Fallback to local storage
        return await run_in_threadpool(self._save_local_bytes, file_bytes, filename or unique_filename, folder)

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

    def generate_presigned_view_url(self, file_url_or_key: str, expires_in: int = 7200) -> str:
        """
        Generates a secure temporary pre-signed URL for direct streaming/downloading from AWS S3.
        Safe for private buckets and native mobile video players.
        """
        if not self.s3_client or not file_url_or_key:
            return file_url_or_key
            
        try:
            if ".amazonaws.com/" in file_url_or_key:
                key = file_url_or_key.split(".amazonaws.com/")[1]
            elif file_url_or_key.startswith("http"):
                return file_url_or_key
            else:
                key = file_url_or_key.lstrip("/")

            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
        except Exception as e:
            print(f"[S3Service Warning] Presigned URL generation failed: {e}")
            return file_url_or_key

s3_service = S3Service()

