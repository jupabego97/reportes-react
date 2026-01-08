"""
Modelos de autenticación.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserRole(str, Enum):
    """Roles de usuario."""
    ADMIN = "admin"
    VENDEDOR = "vendedor"
    VIEWER = "viewer"


class User(BaseModel):
    """Modelo de usuario."""
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRole = UserRole.VIEWER
    disabled: bool = False


class UserInDB(User):
    """Usuario con hash de contraseña."""
    hashed_password: str


class TokenData(BaseModel):
    """Datos del token JWT."""
    username: Optional[str] = None
    role: Optional[UserRole] = None


class Token(BaseModel):
    """Respuesta de token."""
    access_token: str
    token_type: str = "bearer"
    user: User


class LoginRequest(BaseModel):
    """Request de login."""
    username: str
    password: str

