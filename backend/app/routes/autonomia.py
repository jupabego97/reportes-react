"""Rutas de autonomía Nivel 1 (Fase 5)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.autonomia import AutonomiaService

router = APIRouter(
    prefix="/api/autonomia",
    tags=["autonomia"],
    dependencies=[Depends(get_current_active_user)],
)


class PoliticaUpdate(BaseModel):
    auto_max_impacto: Optional[float] = None
    habilitado: Optional[bool] = None


@router.get("/politicas")
async def get_politicas(db: AsyncSession = Depends(get_db)):
    return await AutonomiaService(db).get_politicas()


@router.put("/politicas/{codigo}")
async def actualizar_politica(
    codigo: str,
    payload: PoliticaUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await AutonomiaService(db).actualizar_politica(
            codigo=codigo,
            auto_max_impacto=payload.auto_max_impacto,
            habilitado=payload.habilitado,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ejecutar")
async def ejecutar_nivel1(db: AsyncSession = Depends(get_db)):
    """Ejecuta solo la auto-aprobación Nivel 1 (sin el ciclo completo)."""
    return await AutonomiaService(db).ejecutar_nivel1()
