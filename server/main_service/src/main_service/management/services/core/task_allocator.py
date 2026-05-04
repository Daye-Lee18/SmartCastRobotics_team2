"""Equipment assignment and task allocation logic."""


class TaskAllocator:
    """Decides which equipment should handle each task."""

    def allocate(self) -> None:
        """Allocate a task to an available resource."""
        raise NotImplementedError

