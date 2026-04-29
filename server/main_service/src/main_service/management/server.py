"""Management Service gRPC 서버 (port 50051).

공장 가동 SPOF 제거 목적으로 FastAPI(Interface Service)와 독립 프로세스로 실행된다.
Factory Operator PC(PyQt)가 직접 gRPC 로 호출하며, Interface Service 장애/이관 시에도
공장 운영이 중단되지 않는다.

실행:
    cd backend/management
    python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/management.proto
    python server.py

환경 변수:
    MANAGEMENT_GRPC_HOST  기본 0.0.0.0
    MANAGEMENT_GRPC_PORT  기본 50051
    MANAGEMENT_DB_URL     SQLAlchemy URL (Interface Service 와 동일 DB 공유)

@MX:ANCHOR: V6 Phase 1~8 의 단일 진입점. ManagementServicer + ImagePublisherServicer 등록.
        모든 PyQt gRPC 호출이 본 서버를 통과 — 변경 시 호환성 영향 큼.
@MX:REASON: 5개 service 모듈 + 2개 servicer 의 wiring 책임. RPC 추가 시 servicer 메서드 + proto 동시 갱신 필요.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
from concurrent import futures

import grpc

# `python server.py` 로 직접 실행 가능하도록 sys.path 보장
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_THIS_DIR)  # backend/ — app.models 접근용
for p in (_THIS_DIR, _BACKEND_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

# protoc 로 생성된 모듈 (Makefile: make proto)
from datetime import UTC

import management_pb2  # type: ignore  # noqa: E402
import management_pb2_grpc  # type: ignore  # noqa: E402
from services.ai_client import AIServerConfig, AIUploader  # noqa: E402
from services.amr_battery import AmrBatteryService  # noqa: E402
from services.amr_state_machine import AmrStateMachine  # noqa: E402
from services.command_queue import queue as command_queue  # noqa: E402
from services.execution_monitor import ExecutionMonitor  # noqa: E402

# Phase B: Interface 로부터 이관된 FMS 자동 진행 시퀀서 + ROS2 publisher
from services.fms_sequencer import (
    is_enabled as fms_is_enabled,  # noqa: E402
    run_sequencer as run_fms_sequencer,  # noqa: E402
)
from services.image_forwarder import ForwarderConfig, ImageForwarder  # noqa: E402
from services.image_sink import sink as image_sink  # noqa: E402
from services.rfid_service import RfidService, RfidServiceError  # noqa: E402
from services.robot_executor import RobotExecutor  # noqa: E402
from services.ros2_publisher import init_ros2, is_real_ros2, shutdown_ros2  # noqa: E402
from services.task_allocator import TaskAllocator  # noqa: E402
from services.task_manager import TaskManager  # noqa: E402
from services.traffic_manager import TrafficManager  # noqa: E402

logger = logging.getLogger(__name__)

HOST = os.environ.get("MANAGEMENT_GRPC_HOST", "0.0.0.0")
PORT = int(os.environ.get("MANAGEMENT_GRPC_PORT", "50051"))


class ManagementServicer(management_pb2_grpc.ManagementServiceServicer):
    """gRPC servicer — 5개 내부 모듈을 조율한다.

    실제 비즈니스 로직은 services/ 하위 모듈에 분리되어 있다.
    """

    def __init__(self) -> None:
        self.task_manager = TaskManager()
        self.rfid_service = RfidService()
        self.task_allocator = TaskAllocator()
        self.traffic_manager = TrafficManager()
        # V6 AI 학습 데이터 브리지: Jetson → image_sink → forwarder → AI Server SSH 업로드
        self.image_forwarder = _build_image_forwarder()
        self.execution_monitor = ExecutionMonitor(
            image_forwarder=self.image_forwarder,
        )
        # AMR 배터리 폴링 (SSH → pinkylib)
        self.amr_battery = AmrBatteryService()
        self.amr_battery.start()
        # AMR 운송 상태 머신
        self.amr_state_machine = AmrStateMachine()
        for s in self.amr_battery.get_all():
            self.amr_state_machine.register(s.id)
        # RobotExecutor 에 state_machine 주입
        self.robot_executor = RobotExecutor(state_machine=self.amr_state_machine)

    # ---------- Task Manager (SPEC-C2 Iteration 3: dual-input) ----------
    def StartProduction(self, request, context):
        """Dual-input StartProduction.

        - ord_id > 0   → smartcast v2 단건 (Interface proxy) · result 필드 반환
        - order_ids 비어있지 않음 → legacy PyQt 다중 · work_orders 리스트 반환 (호환)
        - 둘 다 비어있음 → INVALID_ARGUMENT
        """
        # smartcast v2 단건 경로 우선
        if request.ord_id and request.ord_id > 0:
            try:
                result = self.task_manager.start_production_single(request.ord_id)
            except Exception as e:  # noqa: BLE001
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(str(e))
                return management_pb2.StartProductionResponse()
            return management_pb2.StartProductionResponse(
                result=_start_result_to_proto(result),
            )

        # legacy PyQt 다중 경로
        order_ids = list(request.order_ids)
        if not order_ids:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("either ord_id or order_ids required")
            return management_pb2.StartProductionResponse()

        results = self.task_manager.start_production_batch(order_ids)
        # 레거시 호환: smartcast 결과를 WorkOrder shape 로 변환 (PyQt schedule 페이지 호환)
        proto_wos = [_result_to_legacy_work_order(r) for r in results]
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
        return management_pb2.ListItemsResponse(items=[_item_to_proto(it) for it in items])

    # ---------- Task Allocator ----------
    def AllocateItem(self, request, context):
        result = self.task_allocator.allocate(request.item_id)
        return management_pb2.AllocateResponse(
            item_id=request.item_id,
            chosen_robot_id=result.robot_id,
            score=result.score,
            rationale=result.rationale,
        )

    # ---------- Traffic Manager ----------
    def PlanRoute(self, request, context):
        # priority 가 RoutePoint.waypoint_id 자리에 임시로 들어올 가능성 회피 — 별도 메타 없으니
        # 단순 plan_with_yield 를 호출 (priority=5 기본). 향후 PlanRouteRequest 에 priority 필드 추가.
        plan = self.traffic_manager.plan_with_yield(
            robot_id=request.robot_id,
            priority=5,
            start=(request.start.x, request.start.y),
            goal=(request.goal.x, request.goal.y),
        )
        proto_points = [
            management_pb2.RoutePoint(x=x, y=y, waypoint_id=wid) for (x, y, wid) in plan.points
        ]
        return management_pb2.PlanRouteResponse(
            path=proto_points,
            reserved_edges=plan.reserved_edges,
            estimated_duration_sec=plan.duration_sec,
        )

    # ---------- Robot Executor ----------
    def ExecuteCommand(self, request, context):
        accepted, reason = self.robot_executor.dispatch(
            item_id=request.item_id,
            robot_id=request.robot_id,
            command=request.command,
            payload=request.payload,
        )
        return management_pb2.ExecuteCommandResponse(accepted=accepted, reason=reason)

    # ---------- Execution Monitor (Server Streaming) ----------
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

    # ---------- Robot Status ----------
    def GetRobotStatus(self, request, context):
        entries = []
        for s in self.amr_battery.get_all():
            ctx = self.amr_state_machine.get(s.id)
            entries.append(
                management_pb2.RobotStatusEntry(
                    id=s.id,
                    type=management_pb2.ROBOT_TYPE_AMR,
                    host=s.host,
                    status=s.status,
                    battery=s.battery,
                    voltage=s.voltage,
                    location=s.location,
                    task_state=ctx.state.value,
                    task_id=ctx.task_id,
                    loaded_item=ctx.loaded_item,
                )
            )
        return management_pb2.GetRobotStatusResponse(robots=entries)

    # ---------- AMR State Transition ----------
    def TransitionAmrState(self, request, context):
        from services.amr_state_machine import TaskState

        try:
            new_state = TaskState(request.new_state)
        except ValueError:
            return management_pb2.TransitionAmrStateResponse(
                accepted=False,
                reason=f"invalid_state: {request.new_state}",
            )
        # 수리 전 상태 확인 (FAILED → IDLE 전이 시 DB 동기화용)
        prev_state = self.amr_state_machine.get(request.robot_id).state
        ok = self.amr_state_machine.transition(
            robot_id=request.robot_id,
            new_state=new_state,
            task_id=request.task_id or None,
            loaded_item=request.loaded_item or None,
        )
        if ok:
            # 수리 완료(FAILED → IDLE) 시 DB transport_tasks 동기화
            if prev_state == TaskState.FAILED and new_state == TaskState.IDLE:
                self._sync_repair_to_db(request.robot_id)
            return management_pb2.TransitionAmrStateResponse(
                accepted=True,
                reason=f"{request.robot_id} → {new_state.name}",
            )
        ctx = self.amr_state_machine.get(request.robot_id)
        return management_pb2.TransitionAmrStateResponse(
            accepted=False,
            reason=f"invalid_transition: {ctx.state.name} → {new_state.name}",
        )

    def _sync_repair_to_db(self, robot_id: str) -> None:
        """수리 완료 시 DB transport_tasks 의 failed 작업을 completed 로 변경."""
        from datetime import datetime

        from app.database import SessionLocal
        from app.models import TransportTask

        now = datetime.now(UTC)
        db = SessionLocal()
        try:
            failed_tasks = (
                db.query(TransportTask)
                .filter(
                    TransportTask.assigned_robot_id == robot_id,
                    TransportTask.status == "failed",
                )
                .all()
            )
            for task in failed_tasks:
                task.status = "completed"
                task.completed_at = now.isoformat()
            db.commit()
            if failed_tasks:
                logger.info(
                    "수리 완료 DB 동기화: %s 실패 작업 %d건 → completed",
                    robot_id,
                    len(failed_tasks),
                )
        except Exception:
            logger.exception("수리 완료 DB 업데이트 실패: %s", robot_id)
            db.rollback()
        finally:
            db.close()

    # ---------- Handoff ACK (SPEC-AMR-001) ----------
    def ReportHandoffAck(self, request, context):
        """후처리존 인수인계 버튼 이벤트 수신 → 5단계 DB 트랜잭션 + FSM 전이.

        ESP32 GPIO33 → Jetson esp_bridge.py → 본 RPC → handoff_pipeline.apply_handoff()
        가상 모드 (FastAPI /api/debug/handoff-ack) 와 동일 결과를 보장한다.

        DB 트랜잭션 (apply_handoff 내부):
          (1) trans_stat.cur_stat: WAIT_HANDOFF → WAIT_DLD
          (2) trans_task_txn(ToPP).txn_stat: PROC → SUCC
          (3) item.cur_stat: ToPP → PP, equip_task_type=PP, cur_res=NULL
          (4) pp_task_txn 다건 INSERT (ord_pp_map 기준)
          (5) handoff_acks 감사 INSERT

        그 후:
          - in-memory AmrStateMachine.confirm_handoff(amr_id) → UNLOAD_COMPLETED
          - FastAPI WebSocket notify (best-effort)
        """
        from datetime import datetime

        from services.handoff_pipeline import apply_handoff

        from app.database import SessionLocal
        from app.models import HandoffAck

        zone = request.zone or "postprocessing"
        source_device = request.source_device or "unknown"
        idempotency_key = request.idempotency_key or None

        # 0. idempotency 중복 체크 (별도 짧은 세션)
        now_utc = datetime.now(UTC)
        if idempotency_key:
            dup_db = SessionLocal()
            try:
                dup = (
                    dup_db.query(HandoffAck)
                    .filter(HandoffAck.idempotency_key == idempotency_key)
                    .first()
                )
                if dup is not None:
                    logger.info("ReportHandoffAck: 중복 이벤트 skip key=%s", idempotency_key)
                    return management_pb2.HandoffAckResponse(
                        accepted=True,
                        task_id=dup.extra.get("trans_task_txn_id")
                        if isinstance(dup.extra, dict)
                        else "",
                        amr_id=dup.amr_id or "",
                        reason="duplicate",
                        ack_at=dup.ack_at.isoformat() if dup.ack_at else now_utc.isoformat(),
                    )
            finally:
                dup_db.close()

        # 1. 5단계 DB 트랜잭션 (공유 헬퍼)
        db = SessionLocal()
        try:
            try:
                result = apply_handoff(
                    db,
                    button_device_id=source_device,
                    ack_source="esp32_button",
                    via="grpc",
                    idempotency_key=idempotency_key,
                )
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()
                raise
        finally:
            db.close()

        # 2. in-memory FSM 전이 (DB 트랜잭션 밖)
        fsm_reason = result.reason
        if result.amr_id:
            ok, _r = self.amr_state_machine.confirm_handoff(result.amr_id)
            if ok:
                fsm_reason = "released"
            else:
                fsm_reason = f"db_committed_fsm_reject:{_r}"

        # 3. FastAPI WebSocket 브로드캐스트 (best-effort)
        try:
            import json as _json
            import urllib.request  # noqa: E401

            notify_url = os.environ.get(
                "INTERFACE_NOTIFY_URL",
                "http://localhost:8000/api/debug/_notify/handoff-ack",
            )
            body = _json.dumps(
                {
                    "task_id": result.task_id,
                    "amr_id": result.amr_id or "",
                    "item_id": result.item_id,
                    "ord_id": result.ord_id,
                    "zone": zone,
                    "ack_at": now_utc.isoformat(),
                    "orphan": result.orphan,
                    "source": "management_grpc",
                    "pp_task_txn_ids": result.pp_task_txn_ids,
                    "item_cur_stat": result.item_cur_stat,
                }
            ).encode()
            req = urllib.request.Request(
                notify_url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=1.0).read()
        except Exception as e:  # noqa: BLE001
            logger.warning("Handoff WebSocket notify 실패 (무시): %s", e)

        return management_pb2.HandoffAckResponse(
            accepted=True,
            task_id=str(result.task_id) if result.task_id else "",
            amr_id=result.amr_id or "",
            reason=fsm_reason,
            ack_at=now_utc.isoformat(),
        )

    # ---------- RFID Scan Logging (SPEC-RFID-001 Wave 2 + Wave 3 lookup) ----------
    def ReportRfidScan(self, request, context):
        try:
            result = self.rfid_service.report_scan(
                reader_id=request.reader_id,
                zone=request.zone or None,
                raw_payload=request.raw_payload,
                scanned_at_iso=request.scanned_at.iso8601 or None,
                idempotency_key=request.idempotency_key or None,
            )
        except RfidServiceError as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return management_pb2.RfidScanAck()

        # Wave 3: item 매칭 시 후처리 옵션 정의+진행 현황을 응답에 포함
        item_cur_stat = ""
        ord_id_int = 0
        pp_options_proto: list = []
        if result.accepted and result.item_id:
            from services.handoff_pipeline import build_pp_options_view

            from app.database import SessionLocal
            from app.models import Item

            db = SessionLocal()
            try:
                item = db.get(Item, result.item_id)
                if item is not None:
                    item_cur_stat = item.cur_stat or ""
                    ord_id_int = int(item.ord_id) if item.ord_id else 0
                    for opt in build_pp_options_view(db, item):
                        pp_options_proto.append(
                            management_pb2.PpOptionView(
                                pp_id=int(opt.get("pp_id") or 0),
                                pp_nm=opt.get("pp_nm") or "",
                                extra_cost=float(opt.get("extra_cost") or 0.0),
                                txn_stat=str(opt.get("txn_stat") or ""),
                                txn_id=int(opt.get("txn_id") or 0),
                                map_id=int(opt.get("map_id") or 0),
                            )
                        )
            finally:
                db.close()

        return management_pb2.RfidScanAck(
            accepted=result.accepted,
            item_id=result.item_id,
            parse_status=result.parse_status,
            reason=result.reason,
            item_cur_stat=item_cur_stat,
            ord_id=ord_id_int,
            pp_options=pp_options_proto,
        )

    # ---------- Conveyor TOF Event (2026-04-26) ----------
    def ReportConveyorEvent(self, request, context):
        """ESP32 conveyor v5 의 TOF1/TOF2 이벤트를 DB 에 반영.

        event_type:
          tof1_entry → apply_tof1() (pp SUCC + item ToINSP + ToINSP PROC)
          tof2_exit  → apply_tof2() (ToINSP SUCC + item INSP + insp_task PROC)

        가상 모드(/api/debug/sim/conveyor-tof1, /sim/conveyor-tof2)와 동일 결과.
        """
        from services.handoff_pipeline import apply_tof1, apply_tof2

        from app.database import SessionLocal

        res_id = request.res_id or "CONV-01"
        event = (request.event_type or "").strip().lower()
        rfid_payload = request.rfid_payload or None
        item_id = int(request.item_id) if request.item_id else None

        if event not in ("tof1_entry", "tof2_exit"):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"unknown event_type={event!r} (expected tof1_entry|tof2_exit)")
            return management_pb2.ConveyorEventAck()

        db = SessionLocal()
        try:
            try:
                if event == "tof1_entry":
                    r1 = apply_tof1(db, res_id=res_id, rfid_payload=rfid_payload, item_id=item_id)
                    db.commit()
                    return management_pb2.ConveyorEventAck(
                        accepted=r1.ok,
                        item_id=int(r1.item_id or 0),
                        item_cur_stat=r1.item_cur_stat or "",
                        equip_task_txn_id=int(r1.equip_task_txn_id or 0),
                        insp_task_txn_id=0,
                        reason=r1.reason,
                    )
                else:
                    r2 = apply_tof2(db, res_id=res_id, item_id=item_id)
                    db.commit()
                    return management_pb2.ConveyorEventAck(
                        accepted=r2.ok,
                        item_id=int(r2.item_id or 0),
                        item_cur_stat=r2.item_cur_stat or "",
                        equip_task_txn_id=int(r2.equip_task_txn_succ_id or 0),
                        insp_task_txn_id=int(r2.insp_task_txn_id or 0),
                        reason=r2.reason,
                    )
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                logger.exception("ReportConveyorEvent 실패 res=%s event=%s: %s", res_id, event, exc)
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(exc))
                return management_pb2.ConveyorEventAck()
        finally:
            db.close()

    # ---------- Health ----------
    def Health(self, request, context):
        return management_pb2.Empty()

    # ---------- Conveyor Command Streaming (V6 canonical Phase D) ----------
    def WatchConveyorCommands(self, request, context):
        """Jetson 이 구독하는 server streaming. Management → ESP32 명령 relay.

        robot_executor 가 JetsonRelayAdapter 로 enqueue 한 명령을 pull 해서 Jetson 에 push.
        keepalive: queue.wait_next 가 10s timeout → context.is_active() 체크 후 재진입.
        """
        subscriber_id = request.subscriber_id or "unknown"
        filter_ = request.robot_id_filter or ""
        logger.info(
            "WatchConveyorCommands subscriber=%s filter=%s",
            subscriber_id,
            filter_ or "<all>",
        )
        while context.is_active():
            cmd = command_queue.wait_next(filter_ or None, timeout=10.0)
            if cmd is None:
                continue  # keepalive tick
            yield management_pb2.ConveyorCommand(
                robot_id=cmd.robot_id,
                command=cmd.command,
                payload=cmd.payload,
                item_id=cmd.item_id,
                issued_at=management_pb2.Timestamp(iso8601=cmd.issued_at_iso),
                issued_by=cmd.issued_by,
            )
        logger.info("WatchConveyorCommands closed subscriber=%s", subscriber_id)

    # ---------- Camera Frames Streaming (Stage B) ----------
    def WatchCameraFrames(self, request, context):
        """image_sink condvar 기반 pub/sub. Jetson push 즉시 yield."""
        cam = request.camera_id or ""
        if not cam:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("camera_id required")
            return
        last_seq = int(request.after_sequence)
        logger.info("WatchCameraFrames subscriber camera=%s after_seq=%d", cam, last_seq)
        while context.is_active():
            frame = image_sink.wait_new(cam, last_seq, timeout=10.0)
            if frame is None:
                continue  # keepalive timeout — 루프 재진입, 클라 여전히 살아있으면 OK
            last_seq = int(frame.get("sequence", 0))
            yield self._frame_to_response(cam, frame)
        logger.info("WatchCameraFrames subscriber closed camera=%s", cam)

    @staticmethod
    def _frame_to_response(cam: str, frame: dict):
        return management_pb2.CameraFrameResponse(
            available=True,
            camera_id=cam,
            encoding=frame.get("encoding", ""),
            width=int(frame.get("width", 0) or 0),
            height=int(frame.get("height", 0) or 0),
            data=frame.get("data", b""),
            sequence=int(frame.get("sequence", 0) or 0),
            captured_at=management_pb2.Timestamp(iso8601=frame.get("captured_at", "") or ""),
            received_at=management_pb2.Timestamp(iso8601=frame.get("received_at", "") or ""),
        )


# ---------- ORM → proto 변환 헬퍼 ----------

_STAGE_NAME_TO_ENUM = {
    "QUE": 1,
    "MM": 2,
    "DM": 3,
    "TR_PP": 4,
    "PP": 5,
    "IP": 6,
    "TR_LD": 7,
    "SH": 8,
}

_WO_STATUS_TO_ENUM = {"QUE": 1, "PROC": 2, "SUCC": 3, "FAIL": 4}


def _ts(iso_str):
    return management_pb2.Timestamp(iso8601=iso_str or "")


def _item_to_proto(item):
    """smartcast Item → proto Item (SPEC-C3 · 2026-04-20).

    smartcast 필드명 매핑:
      item.item_id → proto.id
      item.ord_id  → proto.order_id (str 변환)
      item.cur_stat → proto.cur_stage enum (unmapped 값은 0)
      item.cur_res  → proto.curr_res
    smartcast 미보유 필드는 기본값:
      proto.insp_id → 0 (smartcast 에 inspection_id 직접 연결 없음)
      proto.mfg_at  → updated_at (제조 시각 근사치)
    """
    updated = item.updated_at.isoformat() if getattr(item, "updated_at", None) else ""
    return management_pb2.Item(
        id=item.item_id,
        order_id=str(item.ord_id or ""),
        cur_stage=_STAGE_NAME_TO_ENUM.get(item.cur_stat or "", 0),
        curr_res=item.cur_res or "",
        insp_id=0,
        mfg_at=_ts(updated),
    )


def _start_result_to_proto(r):
    """StartProductionResult dataclass → proto (SPEC-C2 신규 필드)."""
    return management_pb2.StartProductionResult(
        ord_id=r.ord_id,
        item_id=r.item_id,
        equip_task_txn_id=r.equip_task_txn_id,
        message=r.message or "",
    )


def _result_to_legacy_work_order(r):
    """smartcast start_production_single 결과 → legacy WorkOrder proto (PyQt 호환).

    smartcast 에는 WorkOrder 엔티티가 없으므로 item_id 를 work_order.id 로 매핑,
    pattern_id 는 빈 문자열 (PyQt UI 는 pattern_id 를 최소 표시만 사용).
    """
    return management_pb2.WorkOrder(
        id=r.item_id,  # smartcast item_id 를 work_order id 로 매핑
        order_id=str(r.ord_id),
        pattern_id="",
        qty=1,  # smartcast 는 item 단건 생성
        status=_WO_STATUS_TO_ENUM.get("QUE", 0),
        plan_start=_ts(None),
        act_start=_ts(None),
        act_end=_ts(None),
    )


class ImagePublisherServicer(management_pb2_grpc.ImagePublisherServiceServicer):
    """HW Image Publishing Service (Jetson) → Server.

    gRPC client streaming. 클라이언트가 ImageFrame 을 연속 보내고, 서버는 마지막 ack 1번 응답.
    """

    def PublishFrames(self, request_iterator, context):
        last_seq = 0
        count = 0
        for frame in request_iterator:
            try:
                image_sink.push(
                    camera_id=frame.camera_id,
                    encoding=frame.encoding,
                    width=frame.width,
                    height=frame.height,
                    data=frame.data,
                    sequence=frame.sequence,
                    captured_at_iso=frame.captured_at.iso8601
                    if frame.HasField("captured_at")
                    else "",
                )
                last_seq = frame.sequence
                count += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("ImagePublisher push 실패: %s", exc)
        logger.info("ImagePublisher 스트림 종료: %d frames, last_seq=%d", count, last_seq)
        return management_pb2.ImageAck(
            sequence=last_seq,
            accepted=True,
            message=f"received {count} frames",
        )


def _build_image_forwarder():
    """ImageForwarder 를 구성. AI Server 설정이 없으면 None 반환 → 훅 비활성."""
    ai_cfg = AIServerConfig.from_env()
    if not ai_cfg.enabled:
        logger.info("image_forwarder 비활성: AI Server 환경변수 미설정")
        return None
    fwd = ImageForwarder(
        config=ForwarderConfig.from_env(),
        sink_latest=image_sink.latest,
        uploader=AIUploader(ai_cfg),
    )
    fwd.start()
    logger.info(
        "image_forwarder 활성: spool=%s batch=%.1fs", fwd.cfg.spool_dir, fwd.cfg.batch_interval_sec
    )
    return fwd


def _load_tls_credentials():
    """V6 S-001: mTLS 환경변수 활성 시 ssl_server_credentials 반환, 아니면 None.

    환경변수:
        MGMT_GRPC_TLS_ENABLED  = 1 면 활성
        MGMT_TLS_CERT_DIR      = cert 디렉터리 (기본 ./certs/)
        MGMT_TLS_SERVER_KEY    = 서버 private key 경로 (기본 ${CERT_DIR}/server.key)
        MGMT_TLS_SERVER_CRT    = 서버 cert 경로 (기본 ${CERT_DIR}/server.crt)
        MGMT_TLS_CA_CRT        = CA cert (클라이언트 검증용, 기본 ${CERT_DIR}/ca.crt)
        MGMT_TLS_REQUIRE_CLIENT_CERT = 1 면 mTLS, 0 이면 server-only TLS (기본 1)
    """
    if os.environ.get("MGMT_GRPC_TLS_ENABLED", "0") not in ("1", "true", "yes"):
        return None
    cert_dir = os.environ.get(
        "MGMT_TLS_CERT_DIR",
        os.path.join(_THIS_DIR, "certs"),
    )
    key_path = os.environ.get("MGMT_TLS_SERVER_KEY", os.path.join(cert_dir, "server.key"))
    crt_path = os.environ.get("MGMT_TLS_SERVER_CRT", os.path.join(cert_dir, "server.crt"))
    ca_path = os.environ.get("MGMT_TLS_CA_CRT", os.path.join(cert_dir, "ca.crt"))

    for p in (key_path, crt_path, ca_path):
        if not os.path.exists(p):
            raise FileNotFoundError(
                f"mTLS 활성화됐으나 cert 파일 없음: {p}\nscripts/gen_certs.sh 를 먼저 실행하세요."
            )

    with open(key_path, "rb") as f:
        server_key = f.read()
    with open(crt_path, "rb") as f:
        server_crt = f.read()
    with open(ca_path, "rb") as f:
        ca_crt = f.read()

    require_client = os.environ.get("MGMT_TLS_REQUIRE_CLIENT_CERT", "1") in ("1", "true", "yes")
    creds = grpc.ssl_server_credentials(
        [(server_key, server_crt)],
        root_certificates=ca_crt,
        require_client_auth=require_client,
    )
    logger.info(
        "mTLS 활성: cert_dir=%s require_client_auth=%s",
        cert_dir,
        require_client,
    )
    return creds


def _start_fms_sequencer_thread():
    """FMS 자동 진행 시퀀서를 daemon thread + asyncio loop 로 기동.

    V6 canonical (Phase B): Interface Service 로부터 이관됨.
    FMS_AUTOPLAY=1 일 때만 가동. 실기 연동 시 OFF.
    ROS2 publisher 는 MGMT_ROS2_ENABLED=1 + rclpy 설치 시 실 publish, 아니면 print 폴백.
    gRPC 서버는 ThreadPoolExecutor 기반이라 별도 이벤트 루프 스레드 필요.
    """
    import asyncio
    import threading

    if not fms_is_enabled():
        logger.info("FMS_AUTOPLAY 비활성 — 시퀀서 미가동 (실기 연동 모드)")
        print("[FMS] FMS_AUTOPLAY 비활성 — sequencer 미가동", flush=True)
        return None

    init_ros2()
    ros2_mode = "real" if is_real_ros2() else "mock-print"
    print(f"[FMS] FMS_AUTOPLAY=1 — sequencer 백그라운드 시작 (ROS2={ros2_mode})", flush=True)
    logger.info("FMS sequencer 백그라운드 시작 (ROS2 %s)", ros2_mode)

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_fms_sequencer())
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.exception("FMS sequencer 스레드 오류: %s", exc)
        finally:
            try:
                shutdown_ros2()
            except Exception:  # noqa: BLE001
                pass
            loop.close()

    t = threading.Thread(target=_run, daemon=True, name="fms-sequencer")
    t.start()
    return t


def serve() -> None:
    # WatchItems + WatchAlerts + WatchCameraFrames 등 스트리밍이 워커 점유.
    # 다중 PyQt 클라이언트 + 내부 모니터링 대비 여유있게 32로 확장.
    # keepalive: 죽은 클라이언트(단절된 TCP) 를 빠르게 정리. 구독자 수 가볍게 유지.
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=32),
        options=[
            ("grpc.keepalive_time_ms", 30000),
            ("grpc.keepalive_timeout_ms", 10000),
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.http2.min_ping_interval_without_data_ms", 20000),
            ("grpc.http2.max_pings_without_data", 0),
        ],
    )
    management_pb2_grpc.add_ManagementServiceServicer_to_server(ManagementServicer(), server)
    management_pb2_grpc.add_ImagePublisherServiceServicer_to_server(
        ImagePublisherServicer(), server
    )
    bind_addr = f"{HOST}:{PORT}"

    creds = _load_tls_credentials()
    if creds is not None:
        server.add_secure_port(bind_addr, creds)
        scheme = "TLS"
    else:
        server.add_insecure_port(bind_addr)
        scheme = "INSECURE (V6 S-001: MGMT_GRPC_TLS_ENABLED=1 권장)"

    server.start()
    logger.info("Management Service listening on %s [%s]", bind_addr, scheme)

    # Phase B: FMS 자동 진행 시퀀서 (Interface 로부터 이관)
    _start_fms_sequencer_thread()

    # Graceful shutdown
    def _stop(_signum, _frame):
        logger.info("Shutting down...")
        server.stop(grace=5)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    serve()
