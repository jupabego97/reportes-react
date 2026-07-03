"""
Rutas de maestros únicos y calidad de datos (Fase 1).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.maestros import MaestrosService

router = APIRouter(
    prefix="/api/maestros",
    tags=["maestros"],
    dependencies=[Depends(get_current_active_user)],
)


@router.post("/sincronizar")
async def sincronizar(db: AsyncSession = Depends(get_db)):
    """Reconstruye familias, proveedores y productos desde las fuentes crudas."""
    service = MaestrosService(db)
    return await service.sincronizar()


@router.get("/calidad")
async def get_calidad(db: AsyncSession = Depends(get_db)):
    """Reporte de calidad de datos: cada problema indica qué decisión contamina."""
    service = MaestrosService(db)
    return await service.get_calidad_datos()


@router.get("/resumen")
async def get_resumen(db: AsyncSession = Depends(get_db)):
    """Conteos de los maestros únicos."""
    service = MaestrosService(db)
    return await service.get_resumen()
