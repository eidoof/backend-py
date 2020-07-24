import bcrypt
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header
from passlib.context import CryptContext
from starlette.exceptions import HTTPException
from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_401_UNAUTHORIZED,
)
from itsdangerous import (
    URLSafeTimedSerializer,
    JSONWebSignatureSerializer,
    BadHeader,
    SignatureExpired,
)

from app.database import AsyncIOMotorClient, db_get
from app.config import (
    AUTHORIZATION_TOKEN_PREFIX,
    AUTHORIZATION_REFRESH_TOKEN_PREFIX,
    JWT_SECRET,
    JWT_EXPIRY_SECONDS,
    JWT_REFRESH_EXPIRY_SECONDS,
    VERIFICATION_TOKEN_SECRET,
    VERIFICATION_TOKEN_EXPIRY_SECONDS,
)
from app.models import User, TokenClaims


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
jwt_serializer = JSONWebSignatureSerializer(JWT_SECRET)
verification_token_serializer = URLSafeTimedSerializer(VERIFICATION_TOKEN_SECRET)


def get_salt():
    return bcrypt.gensalt().decode()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _header_get_authorization_tokens(authorization: str = Header(...)) -> (str, str):
    # Parse the Authorization header which should contain two tokens with
    # the Token and RefreshToken prefixes
    tokens = dict(token.split(" ") for token in authorization.split(";"))
    if (
        AUTHORIZATION_TOKEN_PREFIX in tokens
        and AUTHORIZATION_REFRESH_TOKEN_PREFIX in tokens
    ):
        return (
            tokens[AUTHORIZATION_TOKEN_PREFIX],
            tokens[AUTHORIZATION_REFRESH_TOKEN_PREFIX],
        )

    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header"
    )


def load_token(
    token: str, is_jwt=False, is_refresh=False
) -> (dict, datetime, datetime):
    payload: dict
    now = datetime.now(timezone.utc)
    expiry: datetime
    if is_jwt:
        payload, headers = jwt_serializer.loads(token, return_header=True)

        # Check that the token isn't expired
        if not "exp" in headers:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Authorization token is invalid",
            )
        expiry = datetime.strptime(headers["exp"], "%Y-%m-%d %H:%M:%S.%f%z")
    else:
        try:
            payload, timestamp = verification_token_serializer.loads(
                token, max_age=VERIFICATION_TOKEN_EXPIRY_SECONDS, return_timestamp=True
            )
        except SignatureExpired:
            expiry = timestamp + timedelta(seconds=VERIFICATION_TOKEN_EXPIRY_SECONDS)
            pass

    if now >= expiry:
        return payload, expiry, now

    return payload, None, None


def try_authorize(
    tokens: (str, str) = Depends(_header_get_authorization_tokens)
) -> (User, bool):
    token, refresh_token = tokens
    # Attempt to decode the token and verify the claims
    try:
        claims, expiry, _ = load_token(token, is_jwt=True)
        user = User(**claims, token=token, refresh_token=refresh_token)
        if expiry:
            return user, False
        return user, True

    except BadHeader:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
        )


def get_token(claims: dict, is_refresh=False) -> str:
    ttl = (
        lambda: timedelta(seconds=JWT_REFRESH_EXPIRY_SECONDS)
        if is_refresh
        else timedelta(seconds=JWT_EXPIRY_SECONDS)
    )
    return jwt_serializer.dumps(
        claims, header_fields={"exp": str(datetime.now(timezone.utc) + ttl())},
    )


def verify_verification_token(token: str):
    payload: dict
    payload, expiry, now = load_token(token)
    if expiry:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Could not verify, token expired on: {expiry}, current time is: {now}",
        )

    return payload


def get_verification_token(user_id: int):
    return verification_token_serializer.dumps(str(user_id))
