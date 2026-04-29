"""Production-related Management gRPC methods."""

from __future__ import annotations

import grpc
import management_pb2  # type: ignore

from rpc.proto_helpers import item_to_proto, result_to_legacy_work_order, start_result_to_proto


class ProductionRpcMixin:
    """Production start and item read RPCs."""

    def StartProduction(self, request, context):
        """Dual-input StartProduction.

        - ord_id > 0: smartcast v2 single order path.
        - order_ids non-empty: legacy PyQt batch path.
        - both empty: INVALID_ARGUMENT.
        """
        if request.ord_id and request.ord_id > 0:
            try:
                result = self.task_manager.start_production_single(request.ord_id)
            except Exception as e:  # noqa: BLE001
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(str(e))
                return management_pb2.StartProductionResponse()
            return management_pb2.StartProductionResponse(
                result=start_result_to_proto(result),
            )

        order_ids = list(request.order_ids)
        if not order_ids:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("either ord_id or order_ids required")
            return management_pb2.StartProductionResponse()

        results = self.task_manager.start_production_batch(order_ids)
        proto_wos = [result_to_legacy_work_order(r) for r in results]
        return management_pb2.StartProductionResponse(work_orders=proto_wos)

    def ListItems(self, request, context):
        stage_filter = (
            management_pb2.ItemStage.Name(request.stage_filter).replace("ITEM_STAGE_", "")
            if request.stage_filter
            else None
        )
        items = self.task_manager.list_items(
            order_id=request.order_id or None,
            stage=stage_filter if stage_filter and stage_filter != "UNSPECIFIED" else None,
            limit=request.limit or 100,
        )
        return management_pb2.ListItemsResponse(items=[item_to_proto(it) for it in items])

