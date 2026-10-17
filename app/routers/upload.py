import os
import uuid
import aiofiles
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session

from .. import models, oauth2, schemas
from ..database import get_db

router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Ruxsat etilgan fayl turlari va hajmlari (Uy vazifasi 3 bo'yicha kengaytirilgan)
ALLOWED_TYPES = {
    # Rasmlar
    "image/jpeg", "image/png", "image/gif", "image/webp",
    # Hujjatlar
    "application/pdf",
    # Videolar
    "video/mp4", "video/quicktime", "video/webm"
}

ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp"
}

MAX_SIZES = {
    "image": 5 * 1024 * 1024,        # 5 MB
    "application": 20 * 1024 * 1024,  # 20 MB
    "video": 100 * 1024 * 1024       # 100 MB
}


def _get_max_size_for_content_type(content_type: str) -> int:
    main_type = content_type.split("/")[0]
    return MAX_SIZES.get(main_type, 5 * 1024 * 1024)


async def _save_file(file: UploadFile, allowed_types: Optional[set] = None) -> dict:
    types_to_check = allowed_types or ALLOWED_TYPES

    if file.content_type not in types_to_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fayl formati noto'g'ri. Ruxsat etilganlar: {', '.join(sorted(types_to_check))}"
        )

    contents = await file.read()
    max_size = _get_max_size_for_content_type(file.content_type)
    if len(contents) > max_size:
        max_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fayl hajmi {max_mb} MB dan oshmasligi kerak"
        )

    # Noyob fayl nomi yaratish
    orig_name = file.filename or "file.bin"
    extension = orig_name.split(".")[-1].lower() if "." in orig_name else "bin"
    filename = f"{uuid.uuid4().hex}.{extension}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(contents)

    return {
        "filename": filename,
        "url": f"/uploads/{filename}",
        "size": len(contents),
        "content_type": file.content_type
    }


# ─── RASM YUKLASH ─────────────────────────────
@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    result = await _save_file(file, allowed_types=ALLOWED_IMAGE_TYPES)
    result["uploaded_by"] = current_user.username
    return result


# ─── UNIVERSAL FAYL YUKLASH (Rasm, PDF, Video) ─
@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    result = await _save_file(file, allowed_types=ALLOWED_TYPES)
    result["uploaded_by"] = current_user.username
    return result


# ─── KO'P FAYL YUKLASH (Max 5 ta) ─────────────
@router.post("/images")
async def upload_multiple(
    files: List[UploadFile] = File(...),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bir vaqtda maksimal 5 ta fayl yuklash mumkin"
        )

    results = []
    for file in files:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            continue

        result = await _save_file(file, allowed_types=ALLOWED_IMAGE_TYPES)
        results.append(result)

    return {"uploaded": results, "count": len(results)}


# ─── AVATAR YUKLASH (Amaliy mashq 3) ──────────
@router.post("/avatar", response_model=schemas.UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    result = await _save_file(file, allowed_types=ALLOWED_IMAGE_TYPES)

    # Eski avatar mavjud bo'lsa uni o'chirish
    if current_user.avatar_url:
        old_filename = os.path.basename(current_user.avatar_url)
        old_filepath = os.path.join(UPLOAD_DIR, old_filename)
        if os.path.exists(old_filepath):
            try:
                os.remove(old_filepath)
            except OSError:
                pass

    current_user.avatar_url = result["url"]
    db.commit()
    db.refresh(current_user)
    return current_user