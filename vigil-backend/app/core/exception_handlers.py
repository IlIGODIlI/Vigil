from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import VigilException
from app.core.logging_config import logger


async def vigil_exception_handler(request: Request, exc: VigilException) -> JSONResponse:
    logger.error(f"VigilException on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "status_code": exc.status_code},
    )
