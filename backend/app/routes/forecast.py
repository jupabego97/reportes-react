"""
Rutas del motor de forecast (Fase 2): historial, generación, backtest,
precisión real y venta perdida.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.forecast import ForecastService

router = APIRouter(
    prefix="/api/forecast",
    tags=["forecast"],
    dependencies=[Depends(get_current_active_user)],
)


@router.post("/consolidar-historial")
async def consolidar_historial(db: AsyncSession = Depends(get_db)):
    """Vuelca la ventana rodante de ventas al historial persistente (diario, idempotente)."""
    service = ForecastService(db)
    return await service.consolidar_historial()


@router.post("/generar")
async def generar(
    horizonte_dias: int = Query(28, ge=7, le=91),
    db: AsyncSession = Depends(get_db),
):
    """Genera y persiste el forecast P10/P50/P90 por producto-día."""
    service = ForecastService(db)
    return await service.generar(horizonte_dias=horizonte_dias)


@router.post("/backtest")
async def backtest(
    dias_holdout: int = Query(14, ge=7, le=56),
    db: AsyncSession = Depends(get_db),
):
    """Backtest honesto: champion vs baseline ingenuo, con corte temporal real."""
    service = ForecastService(db)
    return await service.backtest(dias_holdout=dias_holdout)


@router.get("/backtest")
async def get_ultimo_backtest(db: AsyncSession = Depends(get_db)):
    """Último backtest ejecutado (gobernanza de modelos)."""
    service = ForecastService(db)
    resultado = await service.get_ultimo_backtest()
    return resultado or {"mensaje": "Aún no se ha ejecutado ningún backtest"}


@router.get("/precision")
async def get_precision(
    dias: int = Query(28, ge=7, le=91),
    db: AsyncSession = Depends(get_db),
):
    """Precisión real: forecasts persistidos vs venta observada."""
    service = ForecastService(db)
    return await service.get_precision(dias=dias)


@router.get("/venta-perdida")
async def get_venta_perdida(
    dias: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Venta y margen perdidos por quiebre, valorizados por producto."""
    service = ForecastService(db)
    return await service.get_venta_perdida(dias=dias)
