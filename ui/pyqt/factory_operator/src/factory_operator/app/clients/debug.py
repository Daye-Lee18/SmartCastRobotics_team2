"""Debug 도메인 mixin — RFID/Conveyor TOF1/TOF2 시뮬 (개발 모드).

후처리 작업자 화면 (Pink GUI #4 확장 — 2026-04-26) 의 가상 시뮬 endpoint.
실 HW (ESP32 RC522 → Mgmt gRPC) 미연동 환경에서 PyQt 만으로 e2e 테스트.

Backend `/api/debug/*` endpoint 는 APP_ENV=development 일 때만 등록됨.
"""

from __future__ import annotations

from typing import Any


class DebugMixin:
    """개발 모드 가상 시뮬 endpoints (RFID + TOF1/TOF2)."""

    def lookup_item_by_rfid(self, payload: str) -> dict[str, Any] | None:
        """RFID payload(`order_<ord>_item_<YYYYMMDD>_<seq>`)로 item + 옵션 조회.

        응답: {item: {...}, pp_options: [{pp_nm, txn_stat, ...}, ...]}
        """
        from urllib.parse import quote

        return self._get(f"/api/debug/items/by-rfid?payload={quote(payload)}", mock_value=None)

    def post_sim_rfid_scan(
        self, raw_payload: str, reader_id: str = "PYQT-WORKER", zone: str = "postprocessing"
    ) -> dict[str, Any] | None:
        """가상 RFID 스캔 — rfid_scan_log INSERT + item 매칭."""
        return self._post(
            "/api/debug/sim/rfid-scan",
            {
                "reader_id": reader_id,
                "zone": zone,
                "raw_payload": raw_payload,
            },
        )

    def post_sim_conveyor_tof1(
        self, res_id: str = "CONV-01", rfid_payload: str | None = None, item_id: int | None = None
    ) -> dict[str, Any] | None:
        """가상 TOF1 진입 — pp_task_txn SUCC + item PP→ToINSP + equip_task_txn ToINSP PROC."""
        body: dict[str, Any] = {"res_id": res_id}
        if rfid_payload:
            body["rfid_payload"] = rfid_payload
        if item_id is not None:
            body["item_id"] = item_id
        op = self.current_operator_id()
        if op is not None:
            body["operator_id"] = op
        return self._post("/api/debug/sim/conveyor-tof1", body)

    def post_sim_conveyor_tof2(
        self, res_id: str = "CONV-01", item_id: int | None = None
    ) -> dict[str, Any] | None:
        """가상 TOF2 도달 — equip_task_txn ToINSP SUCC + item INSP + insp_task_txn PROC."""
        body: dict[str, Any] = {"res_id": res_id}
        if item_id is not None:
            body["item_id"] = item_id
        return self._post("/api/debug/sim/conveyor-tof2", body)
