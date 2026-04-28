"""Protocol adapters for ROS, TCP, and internal equipment data formats."""


class RobotAdapter:
    """Converts internal commands and external protocol messages."""

    def send_command(self) -> None:
        """Send a command through the target equipment protocol."""
        raise NotImplementedError

