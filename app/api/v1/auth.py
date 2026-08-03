"""Authentication and user management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import AdminUser, CurrentUser, DBDep
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RoleUpdateRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DBDep) -> User:
    existing = (
        await db.execute(select(User).where(User.email == data.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("A user with this email already exists")
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: DBDep) -> TokenResponse:
    user = (
        await db.execute(select(User).where(User.email == data.email))
    ).scalar_one_or_none()
    if user is None or not verify_password(data.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")
    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(_: AdminUser, db: DBDep) -> list[User]:
    return list((await db.execute(select(User))).scalars().all())


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_role(
    user_id: str, data: RoleUpdateRequest, _: AdminUser, db: DBDep
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    user.role = data.role
    await db.commit()
    await db.refresh(user)
    return user
