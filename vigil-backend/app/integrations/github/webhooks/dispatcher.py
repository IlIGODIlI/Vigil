from typing import Any, Dict, Optional

from app.core.logging_config import logger
from app.integrations.github.webhooks.handlers import (
    BaseWebhookHandler,
    PullRequestEventHandler,
    PushEventHandler,
)
from app.integrations.github.webhooks.schemas import GitHubNormalizedEvent


class WebhookDispatcher:
    """
    Extensible dispatcher that routes normalized GitHub events to registered handlers.
    """

    def __init__(self):
        self._handlers: Dict[str, BaseWebhookHandler] = {}
        # Register default phase 2 event handlers
        self.register_handler("push", PushEventHandler())
        self.register_handler("pull_request", PullRequestEventHandler())

    def register_handler(self, event_type: str, handler: BaseWebhookHandler) -> None:
        """Register a handler for a specific GitHub event type."""
        self._handlers[event_type.lower()] = handler

    async def dispatch(
        self,
        event: Optional[GitHubNormalizedEvent],
        raw_event_type: str,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Dispatch normalized event to registered handler.
        If event is None or unsupported, handle gracefully without error.
        """
        if event is None:
            logger.info("Ignoring unsupported GitHub event type: '%s'", raw_event_type)
            return {
                "status": "ignored",
                "reason": f"Unsupported event type: '{raw_event_type}'",
                "event_type": raw_event_type,
            }

        handler = self._handlers.get(event.event_type.lower())
        if not handler:
            logger.info("No handler registered for GitHub event type: '%s'", event.event_type)
            return {
                "status": "ignored",
                "reason": f"No handler registered for event type '{event.event_type}'",
                "event_type": event.event_type,
            }

        return await handler.handle(event, db=db)


# Default singleton dispatcher instance
webhook_dispatcher = WebhookDispatcher()
