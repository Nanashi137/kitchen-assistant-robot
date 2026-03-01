from api.schemas import (LoginRequest, SignUpRequest, TokenResponse,
                         UserResponse)
from fastapi import APIRouter, HTTPException, status
from utils.auth import create_access_token, hash_password, verify_password
from utils.db import create_user, get_user_by_username

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup(body: SignUpRequest):
    """Register a new user. Returns JWT."""
    existing = get_user_by_username(body.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    user_id = create_user(
        username=body.username,
        password_hash=hash_password(body.password),
        email=body.email,
    )
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed (e.g. username/email conflict)",
        )
    token = create_access_token(subject=user_id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """Authenticate and return JWT."""
    user = get_user_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(subject=user["id"])
    return TokenResponse(access_token=token)
