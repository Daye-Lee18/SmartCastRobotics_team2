"""Auth 도메인 mixin — operator 로그인 + 핸드오프 ACK.

operator 가 PyQt 에서 이메일 로그인 → 모든 operator-tagged API 호출에 user_id 자동 첨부.
"""

from __future__ import annotations

from typing import Any


class AuthMixin:
    """operator 로그인 + handoff ACK endpoints."""

    def __init_operator__(self) -> None:
        """ApiClient 인스턴스에 operator 슬롯 보장 (lazy init)."""
        if not hasattr(self, "_operator"):
            self._operator: dict[str, Any] | None = None

    def auth_lookup(self, email: str) -> dict[str, Any] | None:
        """이메일로 user_account 조회 → user_id, role 등.

        성공 시 self._operator 에 저장 → 이후 모든 API 호출에 자동 첨부.
        """
        try:
            r = self._post("/api/auth/lookup", {"email": email})
        except Exception:
            self.__init_operator__()
            self._operator = None
            raise
        self.__init_operator__()
        if isinstance(r, dict) and r.get("user_id"):
            self._operator = r
        else:
            self._operator = None
        return r

    def current_operator_id(self) -> int | None:
        self.__init_operator__()
        if self._operator and self._operator.get("user_id"):
            return int(self._operator["user_id"])
        return None

    def current_operator_label(self) -> str:
        self.__init_operator__()
        if not self._operator:
            return "비로그인"
        return f"{self._operator.get('user_nm', '?')} ({self._operator.get('role', '?')}) #{self._operator.get('user_id')}"

    def post_handoff_ack(self) -> dict[str, Any] | None:
        """SPEC-AMR-001 핸드오프 ACK — 시퀀서가 정지시킨 ToPP AMR 1건 풀기.

        로그인된 operator_id 가 있으면 자동 첨부 (pp_task_txn.operator_id 기록).
        """
        body: dict[str, Any] = {}
        op = self.current_operator_id()
        if op is not None:
            body["operator_id"] = op
        return self._post("/api/debug/handoff-ack", body)
