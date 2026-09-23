from fastapi import APIRouter, Depends

from app.core.security import get_current_user

router = APIRouter(tags=["Authentication"])


@router.get("/me")
def get_authenticated_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Return the safe representation of the authenticated Microsoft Entra user."""
    return {
        "authenticated": True,
        "user": current_user,
    }

