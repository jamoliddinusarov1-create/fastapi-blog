import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session

from .. import models, schemas, oauth2
from ..database import get_db
from ..utils.email import send_post_notification, write_log
from ..cache import cache_get, cache_set, cache_delete, cache_delete_pattern
from ..middleware.rate_limit import rate_limit_middleware

router = APIRouter(prefix="/posts", tags=["Posts"])


# ─── CREATE POST (Cache tozalash bilan) ───────
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.PostResponse)
def create_post(
    post: schemas.PostCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    new_post = models.Post(owner_id=current_user.id, **post.model_dump())
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    # 1. Yangi post yaratilganda ro'yxat keshini tozalash
    background_tasks.add_task(cache_delete_pattern, "posts:all:*")

    # 2. Fonda post bildirishi yuborish
    background_tasks.add_task(
        send_post_notification,
        author_email=current_user.email,
        title=new_post.title
    )
    # 3. Fonda log yozish
    background_tasks.add_task(
        write_log,
        action="post_created",
        user_id=current_user.id,
        details=f"title={new_post.title}"
    )

    return new_post


# ─── READ ALL POSTS (Cache va Rate limit) ─────
@router.get("/", response_model=List[schemas.PostResponse])
async def get_all_posts(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = ""
):
    # Postlar ro'yxatiga yumshoq cheklov: 100 ta so'rov/daqiqa
    await rate_limit_middleware(request, calls=100, period=60)

    # Cache kaliti (parametrlar bilan)
    cache_key = f"posts:all:limit={limit}:skip={skip}:search={search}"

    # 1. Keshdan tekshirish (Cache Hit)
    cached = cache_get(cache_key)
    if cached:
        return cached

    # 2. Keshda yo'q (Cache Miss) -> DB dan olish
    posts = db.query(models.Post).filter(
        models.Post.title.contains(search)
    ).limit(limit).offset(skip).all()

    # Pydantic serializer orqali dict ga aylantirish
    posts_data = [
        json.loads(schemas.PostResponse.model_validate(p).model_dump_json())
        for p in posts
    ]

    # 3. Keshga saqlash (5 daqiqa)
    cache_set(cache_key, posts_data, ttl=300)
    return posts


# ─── MY POSTS ─────────────────────────────────
@router.get("/my", response_model=List[schemas.PostResponse])
def get_my_posts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    posts = db.query(models.Post).filter(models.Post.owner_id == current_user.id).all()
    return posts


# ─── READ ONE POST (Cache bilan) ──────────────
@router.get("/{post_id}", response_model=schemas.PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    cache_key = f"posts:{post_id}"

    # 1. Keshdan tekshirish
    cached = cache_get(cache_key)
    if cached:
        return cached

    # 2. DB dan qidirish
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={post_id} bo'lgan post topilmadi"
        )

    # 3. Keshga saqlash (10 daqiqa)
    post_data = json.loads(schemas.PostResponse.model_validate(post).model_dump_json())
    cache_set(cache_key, post_data, ttl=600)

    return post


# ─── UPDATE POST (Cache tozalash bilan) ───────
@router.put("/{post_id}", response_model=schemas.PostResponse)
def update_post(
    post_id: int,
    updated_post: schemas.PostUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    post_query = db.query(models.Post).filter(models.Post.id == post_id)
    post = post_query.first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={post_id} bo'lgan post topilmadi"
        )
    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz bu postni tahrirlay olmaysiz"
        )

    post_query.update(updated_post.model_dump(), synchronize_session=False)
    db.commit()

    # Keshni tozalash (fonda)
    background_tasks.add_task(cache_delete, f"posts:{post_id}")
    background_tasks.add_task(cache_delete_pattern, "posts:all:*")

    return post_query.first()


# ─── DELETE POST (Cache tozalash bilan) ───────
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    post_query = db.query(models.Post).filter(models.Post.id == post_id)
    post = post_query.first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={post_id} bo'lgan post topilmadi"
        )
    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz bu postni o'chira olmaysiz"
        )

    post_query.delete(synchronize_session=False)
    db.commit()

    # Keshni tozalash (fonda)
    background_tasks.add_task(cache_delete, f"posts:{post_id}")
    background_tasks.add_task(cache_delete_pattern, "posts:all:*")

    return None