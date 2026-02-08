"""
Rutas de autenticación.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.auth.security import verify_password, create_access_token, blacklist_token
from app.auth.dependencies import get_user, get_current_active_user, oauth2_scheme
from app.auth.models import Token, User, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _authenticate_user(username: str, password: str) -> dict:
    """Lógica común de autenticación. Retorna user_data o lanza HTTPException."""
    user_data = get_user(username)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user_data.get("disabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario deshabilitado"
        )
    
    return user_data


def _create_token_response(user_data: dict) -> Token:
    """Crea la respuesta de token a partir de user_data."""
    access_token = create_access_token(
        data={"sub": user_data["username"], "role": user_data["role"].value}
    )
    
    user = User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data.get("email"),
        full_name=user_data.get("full_name"),
        role=user_data["role"],
        disabled=user_data.get("disabled", False)
    )
    
    return Token(access_token=access_token, user=user)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint de login con OAuth2."""
    user_data = _authenticate_user(form_data.username, form_data.password)
    return _create_token_response(user_data)


@router.post("/login/json", response_model=Token)
async def login_json(credentials: LoginRequest):
    """Endpoint de login con JSON body."""
    user_data = _authenticate_user(credentials.username, credentials.password)
    return _create_token_response(user_data)


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Obtiene el usuario actual."""
    return current_user


@router.post("/logout")
async def logout(token: Optional[str] = Depends(oauth2_scheme)):
    """Logout - invalida el token actual."""
    if token:
        blacklist_token(token)
    return {"message": "Sesión cerrada correctamente"}


