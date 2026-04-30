"""Monitoring stream RPC methods."""

from __future__ import annotations


class MonitorRpcMixin:
    """Execution monitor streaming RPCs."""

    def WatchItems(self, request, context):
        order_filter = request.order_id or None
        for event in self.execution_monitor.stream(order_filter):
            if context.is_active() is False:
                break
            yield event

    def WatchAlerts(self, request, context):
        sev = request.severity_filter or None
        for event in self.execution_monitor.stream_alerts(sev):
            if context.is_active() is False:
                break
            yield event

