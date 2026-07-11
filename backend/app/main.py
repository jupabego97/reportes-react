"""
Aplicación FastAPI principal.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.routes import (
    ventas_router,
    dashboard_router,
    vendedores_router,
    export_router,
    insights_router,
)
from app.routes.auth import router as auth_router
from app.routes.proveedores import router as proveedores_router
from app.routes.facturas_proveedor import router as facturas_proveedor_router
from app.routes.inventario import router as inventario_router
from app.routes.compras_v2 import router as compras_v2_router
from app.routes.analista import router as analista_router
from app.routes.metricas_sector import router as metricas_sector_router
from app.routes.decisiones import router as decisiones_router
from app.routes.maestros import router as maestros_router
from app.routes.inventario_perpetuo import router as inventario_perpetuo_router
from app.routes.forecast import router as forecast_router
from app.routes.reabastecimiento import router as reabastecimiento_router
from app.routes.ordenes_compra import router as ordenes_compra_router
from app.routes.scorecard_proveedores import router as scorecard_proveedores_router
from app.routes.merma import router as merma_router
from app.routes.pricing import router as pricing_router
from app.routes.surtido import router as surtido_router
from app.routes.diagnostico import router as diagnostico_router
from app.routes.orquestador import router as orquestador_router
from app.routes.autonomia import router as autonomia_router
from app.routes.control import router_aprendizaje, router_control

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API para el Dashboard de Ventas - Reportes de 30 días",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

logger = logging.getLogger("app")


class ErroresComoJSONMiddleware(BaseHTTPMiddleware):
    """Convierte excepciones no controladas en JSON 500.

    Sin esto, una excepción no controlada corta la respuesta antes de que
    CORSMiddleware agregue sus cabeceras, y el navegador la reporta como
    'Failed to fetch' en lugar de mostrar el error real.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Error no controlado en %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=500,
                content={"detail": "Error interno del servidor. Revisa los logs del backend."},
            )


# Se registra antes que CORS para que CORS quede por fuera y siempre
# agregue sus cabeceras, incluso en errores 500.
app.add_middleware(ErroresComoJSONMiddleware)

# Configurar CORS desde variables de entorno
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.up\.railway\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Incluir routers
app.include_router(auth_router)
app.include_router(ventas_router)
app.include_router(dashboard_router)
app.include_router(vendedores_router)
app.include_router(proveedores_router)
app.include_router(facturas_proveedor_router)
app.include_router(inventario_router)
app.include_router(export_router)
app.include_router(insights_router)
app.include_router(compras_v2_router)
app.include_router(analista_router)
app.include_router(metricas_sector_router)
app.include_router(decisiones_router)
app.include_router(maestros_router)
app.include_router(inventario_perpetuo_router)
app.include_router(forecast_router)
app.include_router(reabastecimiento_router)
app.include_router(ordenes_compra_router)
app.include_router(scorecard_proveedores_router)
app.include_router(merma_router)
app.include_router(pricing_router)
app.include_router(surtido_router)
app.include_router(diagnostico_router)
app.include_router(orquestador_router)
app.include_router(autonomia_router)
app.include_router(router_aprendizaje)
app.include_router(router_control)


@app.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "message": "Ventas Dashboard API",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/ping")
async def ping():
    """Simple ping endpoint."""
    return {"ping": "pong"}
