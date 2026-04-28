"""ApiClient 베이스 + 공통 helpers.

`BaseClient` 가 `_get`, `_post`, `_patch` 와 dead_paths/transient_failures 캐시를 제공.
다른 mixin 들이 `BaseClient` 메서드를 사용해 endpoint 호출.

2026-04-27: monitoring/app/api_client.py (830 LOC) 분할 산출.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests
from config import API_BASE_URL

logger = logging.getLogger("app.clients")

DATA_MODE: str = os.environ.get("CASTING_DATA_MODE", "fallback").lower()

# 일시적 실패(ConnectionError/Timeout)는 TTL 동안 재시도 차단 → 메인 스레드 블록 최소화
_TRANSIENT_FAILURE_TTL_SEC: float = 60.0

_ORD_STAT_TO_LEGACY_STATUS = {
    "RCVD": "pending",
    "APPR": "approved",
    "MFG": "in_production",
    "DONE": "production_completed",
    "SHIP": "shipping_ready",
    "COMP": "completed",
    "REJT": "rejected",
    "CNCL": "rejected",
}


def _normalize_rack_id(item: dict[str, Any]) -> str:
    raw_id = str(item.get("id", "")).strip()
    if raw_id.isdigit():
        return raw_id

    row = item.get("row")
    col = item.get("col")
    if row is not None and col is not None:
        try:
            return str((int(row) - 1) * 6 + int(col))
        except (TypeError, ValueError):
            pass

    rack_number = str(item.get("rack_number", item.get("rackNumber", ""))).strip()
    parts = rack_number.replace("_", "-").split("-")
    if len(parts) >= 2:
        try:
            return str((int(parts[-2]) - 1) * 6 + int(parts[-1]))
        except ValueError:
            pass

    return raw_id


def _normalize_rack_status(status: str) -> str:
    status_key = status.strip().lower()
    return {
        "occupied": "full",
        "unavailable": "locked",
        "disabled": "locked",
    }.get(status_key, status_key or "empty")


class BaseClient:
    """REST 호출 베이스 — _get/_post/_patch 제공.

    mixin 들이 self._get(...), self._post(...) 호출. fallback 모드에서 mock 자동 대체.
    """

    def __init__(self, base_url: str = API_BASE_URL, timeout: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._mock_only = DATA_MODE == "mock_only"
        self._fallback = DATA_MODE in ("fallback", "mock_only")
        self._dead_paths: set[str] = set()  # 404 엔드포인트 (영구 캐시)
        # 일시적 실패 경로 → 마지막 실패 시각 (TTL 경과 후 재시도 허용)
        self._transient_failures: dict[str, float] = {}

    def _get(self, path: str, *, mock_value: Any = None) -> Any:
        """GET 요청. 실패/빈 응답 시 mock_value 반환 (fallback 모드일 때)."""
        if self._mock_only:
            return mock_value

        # 이전에 404 로 실패한 경로는 재시도하지 않음 (로그 스팸 방지)
        if path in self._dead_paths:
            return mock_value if self._fallback else None

        # 일시적 실패 TTL 동안은 재호출 차단 → 메인 스레드 블록 방지
        last_fail = self._transient_failures.get(path)
        if last_fail is not None and (time.monotonic() - last_fail) < _TRANSIENT_FAILURE_TTL_SEC:
            return mock_value if self._fallback else None

        url = f"{self._base}{path}"
        try:
            response = self._session.get(url, timeout=self._timeout)
            if response.status_code == 404:
                # 해당 엔드포인트 미구현 - 조용히 mock 사용, 이후 호출은 스킵
                self._dead_paths.add(path)
                logger.info("Endpoint %s not available, using mock", path)
                return mock_value if self._fallback else None
            response.raise_for_status()
            data = response.json()
            # 성공 시 일시적 실패 기록 삭제
            self._transient_failures.pop(path, None)
        except requests.RequestException as exc:
            logger.warning("GET %s failed: %s (skip %.0fs)", url, exc, _TRANSIENT_FAILURE_TTL_SEC)
            self._transient_failures[path] = time.monotonic()
            return mock_value if self._fallback else None

        # 빈 응답이면 mock으로 대체 (fallback 모드)
        if self._fallback and (data is None or (isinstance(data, list | dict) and len(data) == 0)):
            logger.info("Empty response from %s, using mock", url)
            return mock_value
        return data

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        """POST 요청. 실패 시 예외 발생. mock_only 모드에선 None 반환.

        상태 변경 계열(생산 승인, 우선순위 계산 등)은 mock fallback 대신
        명시적으로 실패를 알려야 하므로 GET과 동작이 다름.
        """
        if self._mock_only:
            logger.info("mock_only mode — skipping POST %s", path)
            return None

        url = f"{self._base}{path}"
        try:
            response = self._session.post(
                url,
                json=payload,
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("POST %s failed: %s", url, exc)
            raise  # 호출자가 처리하도록 재전파

    def _patch(self, path: str, payload: dict[str, Any]) -> Any:
        """PATCH 요청. 실패 시 예외 발생."""
        if self._mock_only:
            return None

        url = f"{self._base}{path}"
        try:
            response = self._session.patch(
                url,
                json=payload,
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("PATCH %s failed: %s", url, exc)
            raise

    @staticmethod
    def _calc_util(item: dict[str, Any]) -> int:
        """utilization 이 없을 때 status 로 유추."""
        status = str(item.get("status", "")).lower()
        if status == "running":
            return 85
        if status == "idle":
            return 20
        if status == "charging":
            return 0
        if status == "error":
            return 0
        return 50
