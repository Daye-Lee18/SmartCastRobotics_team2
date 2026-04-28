"""Single source of truth for equipment and task state."""


class StateManager:
    """Stores and updates task and equipment states."""

    def update_state(self) -> None:
        """Update a task or equipment state."""
        raise NotImplementedError

