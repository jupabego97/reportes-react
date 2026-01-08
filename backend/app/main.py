"""
Aplicación FastAPI principal.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import ventas_router, dashboard_router, vendedores_router, export_router
from app.routes.auth import router as auth_router
from app.routes.proveedores import router as proveedores_router
from app.routes.inventario import router as inventario_router
from app.routes.insights import router as insights_router

import os

settings = get_settings()

# Obtener orígenes permitidos desde variable de entorno o usar defaults
cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
cors_origins.extend([
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
])
# Filtrar vacíos
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

app = FastAPI(
    title=settings.app_name,
    description="API para el Dashboard de Ventas - Reportes de 30 días",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth_router)
app.include_router(ventas_router)
app.include_router(dashboard_router)
app.include_router(vendedores_router)
app.include_router(proveedores_router)
app.include_router(inventario_router)
app.include_router(insights_router)
app.include_router(export_router)


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
