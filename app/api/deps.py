"""FastAPI dependencies: container access, authentication, RBAC."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.container import Container
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.db.models import User, UserRole
from app.db.session import get_db

_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError("Application container not initialised")
    return container


ContainerDep = Annotated[Container, Depends(get_container)]
DBDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DBDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
) -> User:
    if credentials is None:
        raise AuthenticationError("Missing bearer token")
    payload = decode_access_token(credentials.credentials)
    user = await db.get(User, payload.get("sub", ""))
    if user is None:
        raise AuthenticationError("User no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise AuthorizationError(
                f"Requires one of roles: {', '.join(r.value for r in roles)}"
            )
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
StaffUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.AGENT))]
