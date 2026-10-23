from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..utils.hashing import verify_password
from ..oauth2 import create_access_token
from ..middleware.rate_limit import rate_limit_middleware

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=schemas.Token)
async def login(
    request: Request,
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Login ga qattiq cheklash: 5 ta urinish/daqiqa
    await rate_limit_middleware(request, calls=5, period=60)

    user = db.query(models.User).filter(models.User.email == user_credentials.username).first()

    if not user or not verify_password(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Noto'g'ri email yoki parol"
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Hisobingiz faol emas")

    access_token = create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}