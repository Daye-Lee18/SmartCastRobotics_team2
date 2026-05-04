"""Event routing and mediation between main service components."""


class EventBridge:
    """Routes events between components."""

    def publish(self) -> None:
        """Publish an event to interested components."""
        raise NotImplementedError

