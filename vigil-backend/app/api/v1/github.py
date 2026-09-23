from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/webhooks/github", tags=["GitHub"])


@router.post(
    "",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Receive GitHub webhooks",
    description="Receive GitHub webhook events (Not Implemented - Phase 4).",
)
@router.post(
    "/",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    include_in_schema=False,
)
def handle_github_webhook() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="GitHub webhook handling is not implemented yet (Phase 4 feature).",
    )
