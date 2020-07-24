from typing import Optional
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, APIRouter, Body
from starlette.responses import RedirectResponse
from starlette.exceptions import HTTPException
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
)
from bson.objectid import ObjectId
from pydantic import EmailStr

from app.database import db_get, AsyncIOMotorClient
import app.models as models
from app.auth import (
    get_token,
    try_authorize,
    load_token,
    hash_password,
    verify_password,
    get_salt,
    get_verification_token,
    verify_verification_token,
)
from app.config import DATABASE_NAME
from app.email import send_verification_email

router = APIRouter()


async def get_user(db: AsyncIOMotorClient, query: dict) -> models.UserInDB:
    result = await db[DATABASE_NAME]["users"].find_one(query)
    if result:
        return models.UserInDB(**result)


async def check_username_email_is_free(
    db: AsyncIOMotorClient,
    username: Optional[str] = None,
    email: Optional[EmailStr] = None,
):
    # TODO I'm 90% this could be refactored with the `with` operator
    if username:
        user = await get_user(db, {"username": username})
        if user and user.is_verified:
            raise HTTPException(
                HTTP_422_UNPROCESSABLE_ENTITY, detail="Username is already taken"
            )
    if email:
        user = await get_user(db, {"email": email})
        if user and user.is_verified:
            raise HTTPException(
                HTTP_422_UNPROCESSABLE_ENTITY,
                detail="User with this email already exists",
            )


async def refresh(db: AsyncIOMotorClient, user: models.User) -> models.User:
    # TODO Should we also try and find the user by username
    db_user = await get_user(db, {"email": user.email})
    if not db_user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="User does not exist"
        )

    # Check that the refresh token matches with what is on the database
    if not db_user.refresh_token == user.refresh_token:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Authorization token is invalid"
        )

    # Check that the refresh token is not expired
    _, expiry, now = load_token(user.refresh_token, is_jwt=True, is_refresh=True)
    if expiry:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Could not authenticate, refresh token expired on: {expiry}, current time is: {now}",
        )

    # Generate a new token and return it
    token = get_token({"email": db_user.email, "username": db_user.username})
    return models.User(**db_user.dict(), token=token)


# Attempts to authenticate using the short-lived token, otherwise if the refresh
# token is still valid then a new token can be issued
async def authorize(result=Depends(try_authorize), db=Depends(db_get)) -> models.User:
    user, authorized = result
    # If not authorized, Attempt to refresh the token
    if not authorized:
        await refresh(db, user)
    return user


@router.get("/")
async def main():
    return RedirectResponse(url="/docs")


@router.post(
    "/register",
    response_model=models.User,
    tags=["authentication"],
    status_code=HTTP_201_CREATED,
)
async def register(
    # Create the UserInCreate Model from the body
    user: models.UserInCreate = Body(...),
    db: AsyncIOMotorClient = Depends(db_get),
):
    # Check that the username and email is not taken by an existing user
    await check_username_email_is_free(db, user.username, user.email)

    async with await db.start_session() as session:
        async with session.start_transaction():
            # Construct a UserInDB Model from the given UserInCreate Model
            db_user = models.UserInDB(**user.dict())
            db_user.salt = get_salt()
            # Set the user's password
            db_user.hashed_password = hash_password(db_user.salt + user.password)

            # Insert the new user into the database
            result = await db[DATABASE_NAME].users.insert_one(db_user.dict())

            if not result.acknowledged:
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user",
                )

            # TODO Send out a verification email
            send_verification_email(user.username, user.email, result.inserted_id)


@router.get("/verify/{token}", tags=["authentication"], status_code=HTTP_200_OK)
async def verify(token: str, db: AsyncIOMotorClient = Depends(db_get)):
    user_id = ObjectId(verify_verification_token(token))
    db_user = await get_user(db, {"_id": user_id})
    db_user.is_verified = True
    db_user.updated_at = datetime.now(tz=timezone.utc)

    result = await db[DATABASE_NAME].users.update_one(
        {"_id": user_id}, {"$set": db_user.dict()}
    )
    if not result.acknowledged:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update database",
        )

    # Remove duplicate users with the same email or username
    result = await db[DATABASE_NAME].users.delete_many(
        {
            "is_verified": False,
            "$or": [{"email": db_user.email}, {"username": db_user.username}],
        }
    )


@router.post(
    "/login",
    response_model=models.User,
    tags=["authorization"],
    status_code=HTTP_200_OK,
)
async def login(
    login: models.UserInLogin = Body(...), db: AsyncIOMotorClient = Depends(db_get)
):
    db_user = await get_user(db, {"email": login.email})
    if not db_user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="User with email does not exist"
        )
    print(login.password)
    print(db_user.hashed_password)
    if not verify_password(db_user.salt + login.password, db_user.hashed_password):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )

    token = get_token({"email": db_user.email, "username": db_user.username})
    db_user.refresh_token = get_token({"email": db_user.email}, is_refresh=True)

    # Put the refresh token into the database
    result = await db[DATABASE_NAME].users.update_one(
        {"email": db_user.email}, {"$set": db_user.dict()}
    )
    if not result.acknowledged:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update database",
        )

    return models.User(**db_user.dict(), token=token)


@router.get(
    "/user", response_model=models.User, tags=["users"],
)
async def get_current_user(user=Depends(authorize)):
    return user
