from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

# --- USER SCHEMAS ---
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- CATEGORY SCHEMAS ---
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- POST SCHEMAS ---
class PostBase(BaseModel):
    title: str
    body: str
    published: bool = True
    rating: Optional[int] = None
    category_id: Optional[int] = None

class PostCreate(PostBase):
    pass

class PostUpdate(PostBase):
    pass

class OwnerInfo(BaseModel):
    id: int
    username: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)

class PostResponse(PostBase):
    id: int
    created_at: datetime
    owner_id: int
    owner: Optional[OwnerInfo] = None
    category: Optional[CategoryResponse] = None
    model_config = ConfigDict(from_attributes=True)

# --- TOKEN SCHEMAS ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[str] = None

# --- MESSAGE SCHEMAS ---
class MessageResponse(BaseModel):
    id: int
    room: str
    username: str
    content: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)