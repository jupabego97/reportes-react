from app.routes.ventas import router as ventas_router
from app.routes.dashboard import router as dashboard_router
from app.routes.vendedores import router as vendedores_router
from app.routes.export import router as export_router
from app.routes.insights import router as insights_router
from app.routes.metricas_sector import router as metricas_sector_router

__all__ = [
    "ventas_router",
    "dashboard_router",
    "vendedores_router",
    "export_router",
    "insights_router",
    "metricas_sector_router",
]


