"""
Aplicación FastAPI principal.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API para el Dashboard de Ventas - Reportes de 30 días",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar CORS desde variables de entorno
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
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
