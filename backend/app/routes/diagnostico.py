"""Rutas de diagnóstico causal (Fase 4): descomposición volumen/precio/mix."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.diagnostico_causal import DiagnosticoCausalService

router = APIRouter(
    prefix="/api/diagnostico",
    tags=["diagnostico"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/descomposicion")
async def get_descomposicion(
    dias_reciente: int = Query(7, ge=3, le=30),
    dias_previo: int = Query(7, ge=3, le=30),
    db: AsyncSession = Depends(get_db),
):
    """Descomposición de variación de venta: volumen, precio y mix."""
    service = DiagnosticoCausalService(db)
    return await service.get_descomposicion(
        dias_reciente=dias_reciente, dias_previo=dias_previo
    )
