import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.github.webhooks.dispatcher import webhook_dispatcher
from app.integrations.github.webhooks.schemas import normalize_webhook_payload
from app.integrations.github.webhooks.security import verify_github_signature
from app.integrations.github.webhooks.tracker import webhook_delivery_tracker

router = APIRouter(prefix="/webhooks/github", tags=["GitHub"])


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Receive GitHub webhooks",
    description="Securely receive, verify, and dispatch GitHub App webhook events.",
)
@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def handle_github_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    # 1. Read raw request body bytes for exact signature verification
    raw_body = await request.body()

    # 2. Extract required GitHub headers
    signature_header = request.headers.get("X-Hub-Signature-256")
    event_type = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")

    # 3. Verify HMAC-SHA256 signature (raises GitHubInvalidSignatureException -> 401 if invalid)
    verify_github_signature(raw_body, signature_header)

    # 4. Header validation
    if not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-GitHub-Event header.",
        )

    if not delivery_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-GitHub-Delivery header.",
        )

    # 5. Idempotency check: detect duplicate deliveries
    if webhook_delivery_tracker.is_duplicate(delivery_id):
        return {
            "status": "duplicate",
            "message": "Delivery already processed",
            "delivery_id": delivery_id,
            "event_type": event_type,
        }

    # Record delivery ID as processed
    webhook_delivery_tracker.record_delivery(delivery_id)

    # 6. Parse JSON payload
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {str(e)}",
        ) from e

    # 7. Normalize event
    normalized_event = normalize_webhook_payload(
        event_type=event_type,
        delivery_id=delivery_id,
        payload=payload,
    )

    # 8. Dispatch event to handler
    dispatch_result = await webhook_dispatcher.dispatch(
        event=normalized_event,
        raw_event_type=event_type,
        db=db,
    )

    return dispatch_result
