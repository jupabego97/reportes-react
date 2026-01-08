"""
Rutas de autenticación.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.security import verify_password, create_access_token
from app.auth.dependencies import get_user, get_current_active_user
from app.auth.models import Token, User, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint de login con OAuth2."""
    user_data = get_user(form_data.username)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user_data["hashed_password"]):
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


@router.post("/login/json", response_model=Token)
async def login_json(credentials: LoginRequest):
    """Endpoint de login con JSON body."""
    user_data = get_user(credentials.username)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    
    if not verify_password(credentials.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    
    if user_data.get("disabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario deshabilitado"
        )
    
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


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Obtiene el usuario actual."""
    return current_user


@router.post("/logout")
async def logout():
    """Logout (el cliente debe eliminar el token)."""
    return {"message": "Sesión cerrada correctamente"}

