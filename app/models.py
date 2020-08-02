from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, BaseConfig, Field, EmailStr


class DateTimeModelMixin(BaseModel):
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc), alias="updatedAt"
    )


class DBModelMixin(DateTimeModelMixin):
    _id: Optional[int] = None


class RWModel(BaseModel):
    class Config(BaseConfig):
        json_encoders = {
            datetime: lambda dt: dt.replace(tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        }


class UserBase(RWModel):
    email: EmailStr
    username: str


class UserInDB(DBModelMixin, UserBase):
    salt: str = ""
    hashed_password: str = ""
    refresh_token: str = ""
    is_verified: bool = False


class User(UserBase):
    token: str
    refresh_token: str


class UserInLogin(RWModel):
    email: EmailStr
    password: str


class UserInRegister(UserInLogin):
    username: str


class UserInUpdate(RWModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None


TokenClaims = UserBase
