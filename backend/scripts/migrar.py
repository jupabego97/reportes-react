"""
Ejecuta las migraciones de Alembic de forma segura en el arranque del deploy.

Caso especial: la base de datos de produccion ya tiene la tabla `users`
(creada antes de adoptar Alembic) pero nunca corrio `alembic upgrade`,
asi que no existe `alembic_version`. Si corremos `upgrade head` a ciegas,
la migracion 001 falla con "table users already exists".

Estrategia:
1. Si no existe `alembic_version` pero si existe `users` -> stamp 001
   (marcar la 001 como aplicada sin ejecutarla).
2. Correr `alembic upgrade head` (aplica 002, 003 y las que vengan).

Uso (desde el directorio backend/):
    python -m scripts.migrar
"""
from __future__ import annotations

import asyncio
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings


async def _estado_bd() -> tuple[bool, bool]:
    """Devuelve (existe alembic_version, existe users)."""
    engine = create_async_engine(get_settings().async_database_url)
    try:
        async with engine.connect() as conn:
            tiene_version = await conn.scalar(text("SELECT to_regclass('alembic_version')"))
            tiene_users = await conn.scalar(text("SELECT to_regclass('users')"))
        return tiene_version is not None, tiene_users is not None
    finally:
        await engine.dispose()


def main() -> None:
    tiene_version, tiene_users = asyncio.run(_estado_bd())
    cfg = Config("alembic.ini")

    if not tiene_version and tiene_users:
        print("BD legada detectada (users existe, alembic_version no): stamp 001")
        command.stamp(cfg, "001")

    print("Ejecutando alembic upgrade head...")
    command.upgrade(cfg, "head")
    print("Migraciones al dia.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - queremos el detalle en los logs del deploy
        print(f"ERROR ejecutando migraciones: {exc}", file=sys.stderr)
        sys.exit(1)
