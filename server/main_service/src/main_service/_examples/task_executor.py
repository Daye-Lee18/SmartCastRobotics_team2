"""Command dispatching for robot arm, conveyor, and AMR execution."""


class TaskExecutor:
    """Sends execution commands to equipment adapters."""

    def execute(self) -> None:
        """Execute an allocated task."""
        raise NotImplementedError

