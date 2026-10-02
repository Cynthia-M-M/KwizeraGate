"""
KwizeraGate — JWT Issuance & Verification
Author: Cynthia Moraa · Modus Chora Studio

Issues short-lived Bearer tokens on successful /auth and validates them
on protected endpoints (/transfer).
"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "kwizeragate-insecure-default-key")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_MINUTES = 30

_bearer_scheme = HTTPBearer()


def create_access_token(data: dict) -> str:
    """
    Create a signed JWT valid for TOKEN_EXPIRE_MINUTES minutes.

    Parameters
    ----------
    data : dict
        Payload to encode. A 'sub' key is recommended (e.g. merchant api_key).
    """
    payload = data.copy()
    expire  = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)) -> dict:
    """
    FastAPI dependency — validates the Bearer JWT on incoming requests.

    Raises HTTP 401 if the token is missing, expired, or tampered.
    Returns the decoded payload dict on success.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception
