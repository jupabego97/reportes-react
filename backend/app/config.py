"""
Configuración de la aplicación usando pydantic-settings.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación."""
    
    database_url: str
    app_name: str = "Ventas Dashboard API"
    debug: bool = False
    
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

