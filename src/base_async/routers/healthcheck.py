from fastapi import APIRouter
from sqlmodel import SQLModel

router = APIRouter()

class HealthCheckResponse(SQLModel, table=False):
    status: str

@router.get('/healthcheck')
async def health_check() -> HealthCheckResponse:
    """Endpoint for health check"""
    return HealthCheckResponse(status="ok")