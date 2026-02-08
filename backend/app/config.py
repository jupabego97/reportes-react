"""
Configuración de la aplicación usando pydantic-settings.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación."""
    
    database_url: str
    app_name: str = "Ventas Dashboard API"
    debug: bool = False
    
    # JWT / Auth
    secret_key: str = "cambiar-en-produccion-generar-con-openssl-rand-hex-32"
    access_token_expire_minutes: int = 1440  # 24 horas
    
    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convierte la cadena de orígenes CORS en una lista."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    # Convertir URL de PostgreSQL a asyncpg si es necesario
    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not url.startswith("postgresql+asyncpg://"):
            url = f"postgresql+asyncpg://{url.split('://', 1)[-1]}"
        return url
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignorar variables de entorno extra


@lru_cache
def get_settings() -> Settings:
    """Obtiene la configuración cacheada."""
    return Settings()

