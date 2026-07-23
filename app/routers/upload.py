from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.utils.s3 import upload_file_to_s3
from app.routers.auth import get_current_user

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Uploads a file to AWS S3 and returns the public URL."""
    try:
        url = await upload_file_to_s3(file.file, file.filename, file.content_type)
        return {"url": url}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload file")
