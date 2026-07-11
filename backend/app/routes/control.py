"""Rutas de aprendizaje y control ejecutivo (Fase 5)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.aprendizaje import AprendizajeService
from app.services.control_ejecutivo import ControlEjecutivoService

router_aprendizaje = APIRouter(
    prefix="/api/aprendizaje",
    tags=["aprendizaje"],
    dependencies=[Depends(get_current_active_user)],
)

router_control = APIRouter(
    prefix="/api/control",
    tags=["control"],
    dependencies=[Depends(get_current_active_user)],
)


@router_aprendizaje.get("/metricas")
async def get_metricas(
    dias: int = Query(30, ge=7, le=180),
    db: AsyncSession = Depends(get_db),
):
    return await AprendizajeService(db).get_metricas(dias=dias)


@router_control.get("/resumen")
async def get_resumen(db: AsyncSession = Depends(get_db)):
    return await ControlEjecutivoService(db).get_resumen()


@router_control.get("/riesgos")
async def get_riesgos(db: AsyncSession = Depends(get_db)):
    return await ControlEjecutivoService(db).get_riesgos()


@router_control.get("/oportunidades")
async def get_oportunidades(db: AsyncSession = Depends(get_db)):
    return await ControlEjecutivoService(db).get_oportunidades()
