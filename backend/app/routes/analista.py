"""
Rutas del analista de datos con IA.
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.analista import AnalistaService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/analista",
    tags=["analista"],
    dependencies=[Depends(get_current_active_user)],
)


class PreguntaRequest(BaseModel):
    pregunta: str = Field(..., min_length=3, max_length=1000)
    historial: Optional[List[dict]] = None


class AnalistaResponse(BaseModel):
    respuesta: str
    sql: Optional[str] = None
    datos: Optional[List[dict]] = None
    error: Optional[str] = None


@router.post("/preguntar", response_model=AnalistaResponse)
async def preguntar(
    request: PreguntaRequest,
    db: AsyncSession = Depends(get_db),
):
    """Recibe una pregunta en lenguaje natural y devuelve una respuesta basada en datos."""
    service = AnalistaService(db)
    try:
        result = await service.ask(
            question=request.pregunta,
            conversation_history=request.historial,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error en analista")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la consulta: {str(e)}",
        )
