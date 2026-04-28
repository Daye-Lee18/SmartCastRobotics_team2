"""Monitoring data processing for UI dashboards and performance metrics."""


class MonitorAgent:
    """Builds monitoring views from state manager data."""

    def collect_metrics(self) -> None:
        """Collect service, task, and equipment metrics."""
        raise NotImplementedError

