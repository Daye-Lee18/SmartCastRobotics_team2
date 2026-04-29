"""Smoke coverage for Management RPC folder wiring."""

from __future__ import annotations

from dataclasses import dataclass

import grpc
import management_pb2  # type: ignore
import management_pb2_grpc  # type: ignore
import pytest


@pytest.mark.parametrize(
    "method_name",
    [
        "StartProduction",
        "ListItems",
        "AllocateItem",
        "PlanRoute",
        "ExecuteCommand",
        "WatchItems",
        "WatchAlerts",
        "GetRobotStatus",
        "TransitionAmrState",
        "ReportHandoffAck",
        "ReportRfidScan",
        "ReportConveyorEvent",
        "WatchConveyorCommands",
        "WatchCameraFrames",
    ],
)
def test_management_servicer_exposes_rpc_methods(method_name: str) -> None:
    from server import ManagementServicer

    assert issubclass(ManagementServicer, management_pb2_grpc.ManagementServiceServicer)
    assert callable(getattr(ManagementServicer, method_name))


def test_image_publisher_servicer_exposes_publish_frames() -> None:
    from rpc.hardware_rpc import ImagePublisherServicer

    assert issubclass(ImagePublisherServicer, management_pb2_grpc.ImagePublisherServiceServicer)
    assert callable(getattr(ImagePublisherServicer, "PublishFrames"))


def test_start_production_rpc_delegates_batch_to_task_manager() -> None:
    from rpc.production_rpc import ProductionRpcMixin

    @dataclass(frozen=True)
    class _StartResult:
        ord_id: int
        item_id: int
        equip_task_txn_id: int
        message: str

    class _TaskManager:
        def __init__(self) -> None:
            self.received: list[str] | None = None

        def start_production_batch(self, order_ids):
            self.received = list(order_ids)
            return [
                _StartResult(
                    ord_id=42,
                    item_id=100,
                    equip_task_txn_id=200,
                    message="queued",
                )
            ]

    class _Servicer(ProductionRpcMixin):
        def __init__(self) -> None:
            self.task_manager = _TaskManager()

    servicer = _Servicer()
    response = servicer.StartProduction(
        management_pb2.StartProductionRequest(order_ids=["42"]),
        context=None,
    )

    assert servicer.task_manager.received == ["42"]
    assert len(response.work_orders) == 1
    assert response.work_orders[0].order_id == "42"
    assert response.work_orders[0].id == 100


def test_start_production_rpc_rejects_empty_request() -> None:
    from rpc.production_rpc import ProductionRpcMixin

    class _Context:
        code = None
        details = None

        def set_code(self, code) -> None:
            self.code = code

        def set_details(self, details: str) -> None:
            self.details = details

    class _Servicer(ProductionRpcMixin):
        task_manager = object()

    context = _Context()
    response = _Servicer().StartProduction(
        management_pb2.StartProductionRequest(),
        context=context,
    )

    assert context.code == grpc.StatusCode.INVALID_ARGUMENT
    assert context.details == "either ord_id or order_ids required"
    assert len(response.work_orders) == 0
