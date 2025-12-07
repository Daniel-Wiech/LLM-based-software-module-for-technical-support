from fastapi import Depends, HTTPException, Header
from modules.db import get_user_by_login, get_refresh_token, get_user_by_id, revoke_refresh_token, add_refresh_token, get_active_refresh_token_by_user
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
import os


SECRET_KEY = os.getenv("JWT_SECRET")
REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 1
REFRESH_TOKEN_EXPIRE_DAYS = 7

def decode_token(authorization: str = Header(...)):

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

def require_role(allowedroles: list):
    def role_checker(payload: dict = Depends(decode_token)):
        userroles = payload.get("roles", [])
        if not any(role in allowedroles for role in userroles):
            raise HTTPException(status_code=403, detail="Access denied")
        return payload

    return role_checker

def login_user(login: str, password: str):
    user = get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid login or password")

    if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid login or password")

    payload = {
        "sub": user["login"],
        "user_id": user["id"],
        "roles": [user["role"]],
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    refreshtoken = get_or_create_refresh_token(user["id"])

    return {
        "access_token": token,
        "refresh_token": refreshtoken,
        "token_type": "bearer",
        "user_id": user["id"],
        "role": user["role"]
    }

def new_refresh_token(userid: int):

    exp = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "user_id": userid,
        "exp": exp
    }

    refreshtoken = jwt.encode(payload, REFRESH_SECRET, algorithm=ALGORITHM)
    add_refresh_token(userid, refreshtoken, exp)

    return refreshtoken

def new_access_token(refreshtoken: str):

    tokenobj = get_refresh_token(refreshtoken)

    if not tokenobj:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if tokenobj["revoked"]:
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    if tokenobj["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = get_user_by_id(tokenobj["user_id"])

    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    payload = {
        "sub": user["login"],
        "user_id": user["id"],
        "roles": [user["role"]],
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }

    newaccesstoken = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    rowaffected = revoke_refresh_token(refreshtoken)

    if rowaffected != 1:
        raise HTTPException(status_code=500, detail="Internal server error")

    newrefreshtoken = new_refresh_token(user["id"])

    return {
        "access_token": newaccesstoken,
        "refresh_token": newrefreshtoken,
        "token_type": "bearer",
        "user_id": user["id"],
        "role": user["role"]
    }

def get_or_create_refresh_token(userid: int):
    tokenobj = get_active_refresh_token_by_user(userid)
    if tokenobj:
        return tokenobj["token"]
    else:
        return new_refresh_token(userid)
