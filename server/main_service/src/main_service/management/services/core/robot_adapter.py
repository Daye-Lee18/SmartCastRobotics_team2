"""Protocol adapters for ROS, TCP, and internal equipment data formats."""


class Adapter:
    """Converts internal commands and external protocol messages."""

    def send_goal(self) -> None:
        """Send a command through the target equipment protocol."""
        raise NotImplementedError

