"""
Configuración de la base de datos con SQLAlchemy async.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


def get_engine():
    """Crea el engine de forma lazy."""
    settings = get_settings()
    return create_async_engine(
        settings.async_database_url,
        echo=settings.debug,
        pool_pre_ping=False,  # No verificar conexión al inicio
        pool_size=5,
        max_overflow=10,
        connect_args={
            "server_settings": {"application_name": "ventas-dashboard"}
        }
    )


# Engine y session factory (lazy)
_engine = None
_async_session = None


def get_session_factory():
    """Obtiene el session factory, creándolo si no existe."""
    global _engine, _async_session
    if _engine is None:
        _engine = get_engine()
        _async_session = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session


class Base(DeclarativeBase):
    """Base para modelos ORM."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para obtener sesión de base de datos."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

