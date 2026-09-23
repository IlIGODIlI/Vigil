from fastapi import APIRouter

router = APIRouter(tags=["Authentication"])


@router.get("/me")
def get_current_user() -> dict[str, str]:
    """Return the currently authenticated user (Microsoft Entra ID placeholder)."""
    return {"message": "Endpoint under development", "service": "auth"}

