from collections import OrderedDict
import threading
from typing import Set


class WebhookDeliveryTracker:
    """
    Lightweight, thread-safe in-memory delivery tracker for Webhook idempotency.
    Prevents processing duplicate X-GitHub-Delivery requests.
    """

    def __init__(self, max_capacity: int = 10000):
        self.max_capacity = max_capacity
        self._deliveries: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def is_duplicate(self, delivery_id: str) -> bool:
        """Check if a delivery ID has already been recorded."""
        if not delivery_id:
            return False
        with self._lock:
            return delivery_id in self._deliveries

    def record_delivery(self, delivery_id: str) -> None:
        """Record a delivery ID as processed."""
        if not delivery_id:
            return
        with self._lock:
            if delivery_id in self._deliveries:
                self._deliveries.move_to_end(delivery_id)
            else:
                self._deliveries[delivery_id] = True
                if len(self._deliveries) > self.max_capacity:
                    self._deliveries.popitem(last=False)

    def clear(self) -> None:
        """Clear all stored delivery IDs (useful for unit testing)."""
        with self._lock:
            self._deliveries.clear()


# Default singleton tracker instance
webhook_delivery_tracker = WebhookDeliveryTracker()
