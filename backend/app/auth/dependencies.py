"""
Dependencies de autenticación para FastAPI.
"""
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.auth.security import decode_token
from app.auth.models import User, UserRole, TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Base de datos simulada de usuarios (en producción usar DB real)
USERS_DB = {
    "admin": {
        "id": 1,
        "username": "admin",
        "email": "admin@ventas.com",
        "full_name": "Administrador",
        "role": UserRole.ADMIN,
        "disabled": False,
        "hashed_password": "$2b$12$V5cxPzMxzoqGI6VC9AY9TuUJ6PmoWs5utSZMcPohsqO46AsXOaIjC"  # password: admin123
    },
    "vendedor": {
        "id": 2,
        "username": "vendedor",
        "email": "vendedor@ventas.com",
        "full_name": "Vendedor Demo",
        "role": UserRole.VENDEDOR,
        "disabled": False,
        "hashed_password": "$2b$12$V5cxPzMxzoqGI6VC9AY9TuUJ6PmoWs5utSZMcPohsqO46AsXOaIjC"  # password: admin123
    },
    "viewer": {
        "id": 3,
        "username": "viewer",
        "email": "viewer@ventas.com",
        "full_name": "Usuario Vista",
        "role": UserRole.VIEWER,
        "disabled": False,
        "hashed_password": "$2b$12$V5cxPzMxzoqGI6VC9AY9TuUJ6PmoWs5utSZMcPohsqO46AsXOaIjC"  # password: admin123
    }
}


def get_user(username: str) -> Optional[dict]:
    """Obtiene un usuario de la base de datos."""
    return USERS_DB.get(username)


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    """Obtiene el usuario actual del token JWT."""
    if not token:
        return None
    
    payload = decode_token(token)
    if not payload:
        return None
    
    username: str = payload.get("sub")
    if not username:
        return None
    
    user_data = get_user(username)
    if not user_data:
        return None
    
    if user_data.get("disabled"):
        return None
    
    return User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data.get("email"),
        full_name=user_data.get("full_name"),
        role=user_data.get("role", UserRole.VIEWER),
        disabled=user_data.get("disabled", False)
    )


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Requiere un usuario autenticado y activo."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def require_role(allowed_roles: List[UserRole]):
    """Factory para crear dependency que requiere roles específicos."""
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{current_user.role}' no tiene permiso para esta acción"
            )
        return current_user
    return role_checker

