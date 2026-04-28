"""RC522 안정성 회귀 테스트 하네스.

SPEC-RC522-001 구현체.
ESP32 conveyor_v5_serial v1.5.1 펌웨어의 RFID 서브시스템을 블랙박스로 검증한다.

의존성: stdlib + pyserial==3.5 (런타임). 테스트는 시리얼을 mock 으로 대체.

종료 코드:
  0 = 통과
  1 = 회귀 감지 (UID/NDEF 임계 미달, 펌웨어 크래시)
  2 = 운영 에러 (포트 open 실패, 권한 오류, operator abort)
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import socket
import sys
import time
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 상수 정의
# ---------------------------------------------------------------------------

# @MX:NOTE: [AUTO] UID 임계값은 v1.5.1 커밋 dd4c4eb 의 실측(30s / 6 taps / 0 miss) 및
# @MX:NOTE: acceptance REQ-RC522-002 계약에 의해 고정. 변경 시 acceptance.md 동기 업데이트 필요.
UID_THRESHOLD_DEFAULT = 99.0

NDEF_THRESHOLD_DEFAULT = 95.0
TAPS_DEFAULT = 100
TIMEOUT_DEFAULT = 300
PORT_DEFAULT = "/dev/ttyUSB0"
BAUD_DEFAULT = 115200

# @MX:ANCHOR: [AUTO] ROLLING_WINDOW_TAPS — REQ-RC522-002 literal 100-탭 계약.
# @MX:REASON: spec.md REQ-RC522-002 는 "rolling 100-tap window" 를 literal 계약으로 박제한다.
#             이 값을 --taps CLI 옵션과 분리해야 --taps 500 등 long-run 캠페인에서도
#             정확히 100 탭 윈도우로 판정된다. 변경 시 spec.md 및 acceptance.md 동기 필요.
ROLLING_WINDOW_TAPS = 100

# 모터 커맨드 — Mac 가드에서 차단 대상
MOTOR_COMMANDS: frozenset[bytes] = frozenset(
    [b"RUN\n", b"STOP\n", b"start\n", b"reset\n", b"sim_entry\n", b"sim_exit\n"]
)


# ---------------------------------------------------------------------------
# 탭 결과 (롤링 윈도우용)
# ---------------------------------------------------------------------------


@dataclass
class TapResult:
    """탭 1회 결과.

    uid_ok: UID 감지 성공 여부.
    ndef_ok: True=NDEF 성공, False=NDEF 실패, None=decode 실패(별도 버킷).
    """

    uid_ok: bool
    ndef_ok: bool | None  # None = UTF-8 디코드 실패 (별도 버킷)


# ---------------------------------------------------------------------------
# RegressionReport 데이터클래스
# ---------------------------------------------------------------------------


# @MX:ANCHOR: [AUTO] RegressionReport — 리포트 스키마 외부 계약.
# @MX:REASON: 이 dataclass 는 CLI(출력), 테스트, 향후 CI 스크립트 3곳 이상에서 참조(fan_in >= 3).
#             필드 추가는 요구사항 변경과 동등하며 acceptance.md 동기 업데이트 필요.
@dataclass
class RegressionReport:
    """SPEC-RC522-001 REQ-RC522-001 정의 리포트 스키마."""

    total_taps: int = 0
    successful_uid_reads: int = 0
    ndef_parse_successes: int = 0
    ndef_decode_failures: int = 0
    missed_reads: int = 0
    healthcheck_state: str = "off"
    firmware_version: str | None = None
    firmware_crashed: bool = False
    run_duration_seconds: float = 0.0
    exit_code: int = 0
    failure_category: str | None = None
    failure_note: str | None = None
    ndef_requirement_skipped: bool = False
    timed_out: bool = False
    first_crash_at_tap: int | None = None

    # NFR 관측성(spec.md §Non-Functional Requirements) — 재현용 환경 정보.
    # 리포트만 보고 run 을 재현할 수 있어야 한다는 계약.
    host: str | None = None
    python: str | None = None
    pyserial: str | None = None
    firmware_boot_raw: str | None = None
    run_started_at: str | None = None  # UTC ISO-8601

    def to_dict(self) -> dict:
        """JSON 직렬화용 dict 반환."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Mac 브라운아웃 가드
# ---------------------------------------------------------------------------


class MacBrownoutGuard:
    """Mac USB 브라운아웃 방지 가드.

    # @MX:WARN: [AUTO] Mac 호스트에서 L298N 모터 커맨드 차단.
    # @MX:REASON: L298N inrush 로 Mac USB 5V 가 떨어지면 ESP32 가 리셋되어
    #             BOOT 라인 폭주 및 RFID 세션 초기화가 발생, 회귀 측정이 오염된다.
    #             모터 테스트는 Jetson 또는 외부 12V 서플라이에서만 수행할 것.
    #             근거 메모리: feedback_motor_brownout_mac_usb
    """

    def __init__(self, port: str) -> None:
        self._port = port
        self._warned = False

    @property
    def is_mac(self) -> bool:
        """현재 호스트가 macOS(Darwin) 인지 반환."""
        return platform.system() == "Darwin"

    def check_and_warn(self) -> None:
        """Mac 호스트이면 stderr 에 경고를 출력한다. 1회만 출력."""
        if self.is_mac and not self._warned:
            print(
                "[WARN] Mac host detected. Motor commands disabled "
                "(ref: feedback_motor_brownout_mac_usb). Read-only sniff mode.",
                file=sys.stderr,
            )
            self._warned = True

    def safe_write(self, write_fn: Callable[[bytes], int], data: bytes) -> int:
        """Mac 에서는 모터 커맨드를 차단하고 0을 반환, 그 외에는 그대로 전송."""
        if self.is_mac and data in MOTOR_COMMANDS:
            # Mac 에서 모터 커맨드 차단 — no-op
            return 0
        return write_fn(data)


# ---------------------------------------------------------------------------
# 이벤트 파서
# ---------------------------------------------------------------------------


class RegressionParser:
    """ESP32 시리얼 라인을 소비해 탭·UID·NDEF 이벤트를 집계하는 파서.

    의존성 주입 설계: line_source 이터레이터를 외부에서 주입해
    실기기 없이도 단위 테스트 가능.
    """

    def __init__(self, line_source: Iterator[str]) -> None:
        self._line_source = line_source

        # 집계 카운터
        self.total_taps: int = 0
        self.successful_uid_reads: int = 0
        self.ndef_parse_successes: int = 0
        self.ndef_decode_failures: int = 0
        self.missed_reads: int = 0

        # 상태
        self.healthcheck_state: str = "off"
        self.firmware_version: str | None = None
        self.firmware_boot_raw: str | None = None  # NFR: BOOT 라인 원문 (spec.md §관측성)
        self.firmware_crashed: bool = False
        self.first_crash_at_tap: int | None = None

        # 탭 추적
        self._last_uid: str | None = None
        self._after_clear: bool = False  # rfid_clear 이후 플래그

        # 폴백 상태 (JSON 실패 시 사용)
        self._pending_fallback_uid: str | None = None
        self._fallback_active: bool = False  # 현재 라인이 폴백 컨텍스트인지

        # 롤링 윈도우 (deque(maxlen=100) — 최악 윈도우 검출)
        self._tap_window: deque[TapResult] = deque()

        # BOOT 라인 카운터
        self._boot_count: int = 0

        # RFID 활동 관측 플래그 (mid-run attach 이후 BOOT = 크래시 판정용).
        # 펌웨어는 jetson_publisher 종료 후 RESET 없이 serial 재open 이 가능해,
        # 초기 BOOT 배너를 놓친 상태에서 runtime 에 크래시가 발생하면 유일한 BOOT
        # 라인이 "첫 BOOT" 로 오판된다. RFID 활동 이후 도착한 BOOT 는 crash 로 본다.
        self._rfid_activity_seen: bool = False

    # ------------------------------------------------------------------
    # 테스트 전용 주입 메서드 (단위 테스트에서 직접 탭 결과를 주입)
    # ------------------------------------------------------------------

    def _inject_tap(self, uid: str, ndef_ok: bool | None) -> None:
        """테스트 전용: 탭 결과를 직접 주입한다.

        ndef_ok:
          True  = NDEF 성공
          False = NDEF 실패(텍스트 없음)
          None  = NDEF UTF-8 디코드 실패 (별도 버킷)
        """
        self.total_taps += 1
        self.successful_uid_reads += 1
        if ndef_ok is True:
            self.ndef_parse_successes += 1
        elif ndef_ok is None:
            self.ndef_decode_failures += 1
        result = TapResult(uid_ok=True, ndef_ok=ndef_ok)
        self._tap_window.append(result)

    def _inject_missed_tap(self) -> None:
        """테스트 전용: UID 감지 실패(missed read) 를 주입한다."""
        self.total_taps += 1
        self.missed_reads += 1
        result = TapResult(uid_ok=False, ndef_ok=None)
        self._tap_window.append(result)

    # ------------------------------------------------------------------
    # 내부 처리 메서드
    # ------------------------------------------------------------------

    def _handle_boot_line(self, line: str) -> None:
        """BOOT 라인 처리: 최초 = 버전 기록, 이후(또는 RFID 활동 뒤) = 크래시 감지.

        bug_010 fix: RFID 활동(_rfid_activity_seen)이 먼저 관측된 뒤 도착한 BOOT 는
        boot_count 와 무관하게 크래시로 분류한다. 이렇게 해야 jetson_publisher 종료로
        포트를 확보했을 때 ESP32 가 리셋되지 않은 상태에서 접속한 뒤 runtime 에 크래시가
        발생해도 AC-E5 (firmware_crash) 가 감지된다.
        """
        # "BOOT:conveyor_v5_serial 1.5.1" → "conveyor_v5_serial 1.5.1"
        version = line[len("BOOT:") :].strip()
        self._boot_count += 1

        # NFR 관측성: BOOT 라인 원문은 펌웨어 빌드 재현의 1차 증거다.
        if self.firmware_boot_raw is None:
            self.firmware_boot_raw = line

        # 최초 BOOT 여도 RFID 활동이 선행됐으면 mid-run 크래시로 판정.
        is_mid_run_crash = self._boot_count > 1 or self._rfid_activity_seen
        if is_mid_run_crash:
            self.firmware_crashed = True
            if self.first_crash_at_tap is None:
                self.first_crash_at_tap = self.total_taps

        # 버전 문자열은 최초 1회만 기록 (크래시 시 재부팅이라도 버전은 동일 펌웨어).
        if self.firmware_version is None:
            self.firmware_version = version

    def _handle_rfid_reader(self, data: dict) -> None:
        """rfid_reader 이벤트: healthcheck 상태를 기록한다."""
        self._rfid_activity_seen = True  # bug_010: mid-run attach 이후 BOOT 판정용
        if "healthcheck" in data:
            self.healthcheck_state = data["healthcheck"]

    def _handle_rfid_tag(self, data: dict) -> None:
        """rfid_tag 이벤트: 탭 집계 규칙을 적용한다.

        탭 집계 규칙 (REQ-RC522-002):
        - uid != lastUid  → 새 탭
        - 직전이 rfid_clear → 새 탭
        - 동일 uid && rfid_clear 없음 → 중복, 집계 안 함
        """
        self._rfid_activity_seen = True  # bug_010: mid-run attach 이후 BOOT 판정용
        uid = data.get("uid", "")
        is_new_tap = (uid != self._last_uid) or self._after_clear

        if is_new_tap:
            self._last_uid = uid
            self._after_clear = False

            # NDEF text 처리
            text = data.get("text", "")
            if text:
                # bug_002 fix: main() 의 _readline_from_serial() 이 bytes 를 이미
                # errors="replace" 로 디코드하므로, 펌웨어가 emit 한 UTF-8 손상 바이트는
                # 이 시점에 U+FFFD 치환 문자로 도달한다. str 재-encode/decode 는 U+FFFD
                # 를 통과시켜 decode_failure 로 판정되지 않는다. 치환 문자를 직접 찾아
                # AC-E3 (NDEF UTF-8 손상) 에 대응한다.
                if "\ufffd" in text:
                    ndef_ok: bool | None = None
                    self.ndef_decode_failures += 1
                else:
                    try:
                        text.encode("utf-8").decode("utf-8")
                        ndef_ok = True
                        self.ndef_parse_successes += 1
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        ndef_ok = None
                        self.ndef_decode_failures += 1
            else:
                ndef_ok = False

            self.total_taps += 1
            self.successful_uid_reads += 1
            self._tap_window.append(TapResult(uid_ok=True, ndef_ok=ndef_ok))
        # 동일 UID 중복 수신은 무시

    def _handle_rfid_clear(self) -> None:
        """rfid_clear 이벤트: 탭 경계 플래그를 설정한다."""
        self._rfid_activity_seen = True  # bug_010
        self._last_uid = None
        self._after_clear = True

    def _handle_fallback_uid_token(self, line: str) -> None:
        """JSON 실패 후 RFID_UID: 토큰으로 폴백 집계.

        동일 폴백 흐름에서 동일 UID 는 1탭으로만 집계한다.
        """
        self._rfid_activity_seen = True  # bug_010
        uid = line[len("RFID_UID:") :].strip()
        if uid != self._last_uid or self._after_clear:
            self._last_uid = uid
            self._after_clear = False
            self._pending_fallback_uid = uid
            self.total_taps += 1
            self.successful_uid_reads += 1
            # NDEF 는 RFID_TEXT 토큰이 올 때 추가됨
            self._tap_window.append(TapResult(uid_ok=True, ndef_ok=False))

    def _handle_fallback_text_token(self, line: str) -> None:
        """RFID_TEXT: 토큰 — 가장 최근 폴백 탭에 NDEF 성공을 기록한다."""
        if self._pending_fallback_uid is not None:
            # 마지막 탭 결과를 NDEF 성공으로 업데이트
            if self._tap_window:
                last = self._tap_window[-1]
                if not last.ndef_ok:
                    self._tap_window[-1] = TapResult(uid_ok=last.uid_ok, ndef_ok=True)
                    self.ndef_parse_successes += 1
            self._pending_fallback_uid = None

    def _process_line(self, line: str) -> None:
        """라인 1개를 처리한다. 우선순위: BOOT > JSON > fallback 토큰."""
        line = line.strip()
        if not line:
            return

        # 1. BOOT 라인
        if line.startswith("BOOT:"):
            self._handle_boot_line(line)
            self._pending_fallback_uid = None
            return

        # 2. JSON 파싱 시도
        if line.startswith("{"):
            try:
                data = json.loads(line)
                event = data.get("event", "")
                if event == "rfid_reader":
                    self._handle_rfid_reader(data)
                elif event == "rfid_tag":
                    self._handle_rfid_tag(data)
                elif event == "rfid_clear":
                    self._handle_rfid_clear()
                self._pending_fallback_uid = None
                return
            except json.JSONDecodeError:
                # JSON 파싱 실패 → 폴백 토큰 대기
                pass

        # 3. 폴백 토큰
        if line.startswith("RFID_UID:"):
            self._handle_fallback_uid_token(line)
            return

        if line.startswith("RFID_TEXT:"):
            self._handle_fallback_text_token(line)
            return

    def run(self) -> None:
        """line_source 를 소진할 때까지 모든 라인을 처리한다."""
        for line in self._line_source:
            self._process_line(line)

    def uid_success_rate_worst_window(self, window_size: int = 100) -> float:
        """롤링 윈도우에서 최악의 UID 성공률을 반환한다.

        롤링 100탭 윈도우에서 가장 낮은 UID 성공률을 반환한다.
        전체 평균이 아니라 최악 윈도우를 검사해야 REQ-RC522-002 를 올바르게 판정할 수 있다.
        """
        window = list(self._tap_window)
        if not window:
            return 0.0
        total = len(window)
        if total < window_size:
            # 탭이 충분하지 않으면 현재까지의 성공률 반환
            successes = sum(1 for t in window if t.uid_ok)
            return (successes / total) * 100.0
        # 슬라이딩 윈도우로 최악 구간 탐색
        worst = 100.0
        for i in range(total - window_size + 1):
            segment = window[i : i + window_size]
            rate = sum(1 for t in segment if t.uid_ok) / window_size * 100.0
            if rate < worst:
                worst = rate
        return worst

    def ndef_success_rate(self) -> float:
        """전체 성공 UID 탭 중 NDEF 성공 비율을 반환한다."""
        base = self.successful_uid_reads
        if base == 0:
            return 0.0
        return (self.ndef_parse_successes / base) * 100.0


# ---------------------------------------------------------------------------
# 판정 로직
# ---------------------------------------------------------------------------


def build_report(
    parser: RegressionParser,
    uid_threshold: float,
    ndef_threshold: float,
    ndef_expected: int,
    healthcheck_expected: str,
    required_taps: int,
    run_duration: float = 0.0,
    timed_out: bool = False,
    expected_taps: int | None = None,
) -> RegressionReport:
    """파서 결과로 RegressionReport 를 생성하고 판정한다.

    판정 우선순위:
    1. 펌웨어 크래시 → exit 1, firmware_crash
    2. healthcheck=on + UID 미달 (탭 충분 시) → exit 1, healthcheck_regression
    3. 탭 횟수 부족 → exit 1, insufficient_taps
    4. UID 성공률 미달 → exit 1, uid_detection_below_threshold
    5. NDEF 성공률 미달 → exit 1, ndef_parse_below_threshold
    6. 모두 통과 → exit 0

    Args:
        expected_taps: operator 실측 총 탭 횟수 (REQ-RC522-002 100탭 윈도우 정확도 향상).
            지정 시 parser.total_taps 와 차이를 missed_reads 로 환산하여 롤링 윈도우에
            주입한다. 이는 ESP32 펌웨어가 성공한 탭에 대해서만 rfid_tag 이벤트를
            emit 하므로, 누락된 탭을 외부에서 알려주지 않으면 AC-2 healthcheck_regression
            시나리오(100탭 중 15회 miss 등) 를 하네스가 감지할 수 없다는 한계를 해소한다.
    """
    # bug_008: expected_taps 주어졌으면 missed slot 을 tap_window 에 주입해 보정.
    # parser 의 tap 집계는 이미 완료된 상태이므로 여기서만 덧붙인다.
    if expected_taps is not None and expected_taps > parser.total_taps:
        inferred_misses = expected_taps - parser.total_taps
        for _ in range(inferred_misses):
            parser._tap_window.append(TapResult(uid_ok=False, ndef_ok=None))
        parser.missed_reads += inferred_misses
        parser.total_taps = expected_taps

    report = RegressionReport(
        total_taps=parser.total_taps,
        successful_uid_reads=parser.successful_uid_reads,
        ndef_parse_successes=parser.ndef_parse_successes,
        ndef_decode_failures=parser.ndef_decode_failures,
        missed_reads=parser.missed_reads,
        healthcheck_state=parser.healthcheck_state,
        firmware_version=parser.firmware_version,
        firmware_boot_raw=parser.firmware_boot_raw,
        firmware_crashed=parser.firmware_crashed,
        run_duration_seconds=run_duration,
        first_crash_at_tap=parser.first_crash_at_tap,
        timed_out=timed_out,
        ndef_requirement_skipped=(ndef_expected == 0),
    )

    # ---- 판정 1: 펌웨어 크래시 ----
    if parser.firmware_crashed:
        report.exit_code = 1
        report.failure_category = "firmware_crash"
        return report

    # bug_016: REQ-RC522-002 의 literal 100-탭 윈도우 계약. --taps 와 무관.
    uid_rate = parser.uid_success_rate_worst_window(window_size=ROLLING_WINDOW_TAPS)

    # ---- 판정 2: healthcheck 재도입 회귀 ----
    # healthcheck=on (런타임 감지 OR CLI 플래그) + 충분한 탭 + UID 미달.
    # bug_020 fix: required_taps 미달 상태에서 healthcheck_regression 판정을 내리면
    # 0-tap SIGINT / 포트 재open 직후 abort 등에서 거짓 양성이 발생하므로
    # parser.total_taps >= required_taps 조건을 선행한다.
    effective_healthcheck = parser.healthcheck_state
    if healthcheck_expected == "on" and effective_healthcheck != "on":
        effective_healthcheck = "on"

    if (
        effective_healthcheck == "on"
        and parser.total_taps >= required_taps
        and uid_rate < uid_threshold
    ):
        report.exit_code = 1
        report.failure_category = "healthcheck_regression"
        # bug_025: CLI override 로 결정된 effective_healthcheck 가 리포트에도 반영돼야
        # AC-2 L44 ("healthcheck_state == 'on' 로 기록") 가 지켜진다.
        report.healthcheck_state = effective_healthcheck
        report.failure_note = (
            "regression reference: dd4c4eb — "
            "v1.5.1 fix (VersionReg healthcheck 제거) 가 재도입되었을 가능성이 있습니다. "
            "v1.5.1 수정 커밋 dd4c4eb 를 참조하세요."
        )
        # bug_025: AC-2 L45 — stderr 에 운영자 가시 경고 출력.
        print(
            "[WARN] healthcheck_regression detected — "
            "v1.5.1 fix may have been reverted (ref: dd4c4eb).",
            file=sys.stderr,
        )
        return report

    # ---- 판정 3: 탭 횟수 부족 ----
    if parser.total_taps < required_taps:
        report.exit_code = 1
        report.failure_category = "insufficient_taps"
        return report

    # ---- 판정 4: UID 성공률 미달 ----
    if uid_rate < uid_threshold:
        report.exit_code = 1
        report.failure_category = "uid_detection_below_threshold"
        return report

    # ---- 판정 5: NDEF 성공률 미달 ----
    if ndef_expected == 1:
        ndef_rate = parser.ndef_success_rate()
        if ndef_rate < ndef_threshold:
            report.exit_code = 1
            report.failure_category = "ndef_parse_below_threshold"
            return report

    # ---- 판정 6: 통과 ----
    report.exit_code = 0
    return report


# ---------------------------------------------------------------------------
# 시리얼 open + 실행 (의존성 주입으로 테스트 가능)
# ---------------------------------------------------------------------------


def open_serial_and_run(
    port: str,
    baud: int,
    line_source_factory: Callable | None,
    serial_opener: Callable,
    uid_threshold: float,
    ndef_threshold: float,
    ndef_expected: int,
    healthcheck_expected: str,
    required_taps: int,
    expected_taps: int | None = None,
) -> tuple[int, RegressionReport]:
    """시리얼 포트 open 후 파서를 실행한다.

    serial_opener 가 예외를 던지면 exit_code=2 (운영 에러) 를 반환한다.
    line_source_factory 가 None 이면 serial_opener 만 호출하고 즉시 반환(테스트용).
    """
    empty_report = RegressionReport(exit_code=2)
    try:
        serial_opener(port, baud)
    except (OSError, PermissionError) as exc:
        print(
            f"[ERROR] 시리얼 포트 열기 실패: {exc}\n"
            "Port already in use. Stop jetson_publisher / esp_bridge before running this suite.",
            file=sys.stderr,
        )
        empty_report.exit_code = 2
        return 2, empty_report

    if line_source_factory is None:
        return 2, empty_report

    source = line_source_factory()
    t0 = time.monotonic()
    parser = RegressionParser(line_source=source)
    parser.run()
    duration = time.monotonic() - t0

    report = build_report(
        parser=parser,
        uid_threshold=uid_threshold,
        ndef_threshold=ndef_threshold,
        ndef_expected=ndef_expected,
        healthcheck_expected=healthcheck_expected,
        required_taps=required_taps,
        run_duration=duration,
        expected_taps=expected_taps,
    )
    return report.exit_code, report


# ---------------------------------------------------------------------------
# CLI 엔트리포인트
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 반환한다."""
    p = argparse.ArgumentParser(
        prog="test_rc522_regression",
        description=(
            "SPEC-RC522-001: RC522 안정성 회귀 테스트 하네스. "
            "ESP32 conveyor_v5_serial v1.5.1 의 RFID 서브시스템을 블랙박스로 검증한다."
        ),
    )
    p.add_argument(
        "--port",
        default=PORT_DEFAULT,
        help=f"시리얼 포트 경로 (기본: {PORT_DEFAULT})",
    )
    p.add_argument(
        "--baud",
        type=int,
        default=BAUD_DEFAULT,
        help=f"보드레이트 (기본: {BAUD_DEFAULT})",
    )
    p.add_argument(
        "--taps",
        type=int,
        default=TAPS_DEFAULT,
        help=f"검증할 탭 횟수 — 파서가 관측한 rfid_tag 이벤트 도달 종료 조건 (기본: {TAPS_DEFAULT})",
    )
    p.add_argument(
        "--expected-taps",
        type=int,
        default=None,
        dest="expected_taps",
        help=(
            "operator 실측 총 탭 횟수. 지정 시 parser.total_taps 와 차이를 "
            "missed_reads 로 환산 (REQ-RC522-002 100-탭 윈도우 정확도, AC-2 감지용)."
        ),
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=TIMEOUT_DEFAULT,
        help=f"최대 대기 시간 (초, 기본: {TIMEOUT_DEFAULT})",
    )
    p.add_argument(
        "--uid-threshold",
        type=float,
        default=UID_THRESHOLD_DEFAULT,
        dest="uid_threshold",
        help=f"UID 감지 성공률 임계값 %% (기본: {UID_THRESHOLD_DEFAULT})",
    )
    p.add_argument(
        "--ndef-threshold",
        type=float,
        default=NDEF_THRESHOLD_DEFAULT,
        dest="ndef_threshold",
        help=f"NDEF 파싱 성공률 임계값 %% (기본: {NDEF_THRESHOLD_DEFAULT})",
    )
    p.add_argument(
        "--ndef-expected",
        type=int,
        default=1,
        choices=[0, 1],
        dest="ndef_expected",
        help="NDEF 텍스트 기대 여부 (1=기대, 0=skip REQ-RC522-003, 기본: 1)",
    )
    p.add_argument(
        "--healthcheck-expected",
        default="off",
        choices=["on", "off"],
        dest="healthcheck_expected",
        help="healthcheck 재도입 여부 플래그 (on/off, 기본: off)",
    )
    p.add_argument(
        "--report",
        default=None,
        metavar="PATH",
        help="리포트 JSON 을 저장할 파일 경로 (선택)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING"],
        dest="log_level",
        help="로그 레벨 (기본: INFO)",
    )
    return p


def _collect_environment_info(pyserial_version: str | None) -> dict:
    """NFR 관측성 필드 수집 (spec.md §Non-Functional Requirements).

    리포트 JSON 만 보고 run 을 재현하기 위해 호스트/인터프리터/라이브러리 버전을 박제한다.
    """
    return {
        "host": socket.gethostname(),
        "python": platform.python_version(),
        "pyserial": pyserial_version,
        "run_started_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    """CLI 메인 함수. exit code 를 반환한다."""
    args = _build_arg_parser().parse_args(argv)

    # bug_014 fix: --log-level 플래그를 실제로 logging 설정에 연결한다.
    logging.basicConfig(
        level=getattr(logging, args.log_level, logging.INFO),
        format="%(levelname)s: %(message)s",
    )

    # Mac 브라운아웃 가드
    guard = MacBrownoutGuard(port=args.port)
    guard.check_and_warn()

    # pyserial import (런타임에만 필요)
    try:
        import serial  # type: ignore[import-untyped]
    except ImportError:
        print(
            "[ERROR] pyserial 이 설치되어 있지 않습니다. "
            "pip install pyserial==3.5 로 설치 후 재실행하세요.",
            file=sys.stderr,
        )
        return 2

    pyserial_version: str | None = getattr(serial, "__version__", None)
    env_info = _collect_environment_info(pyserial_version)

    # 시리얼 포트 열기
    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.5)
    except (OSError, PermissionError) as exc:
        print(
            f"[ERROR] 시리얼 포트 열기 실패: {exc}\n"
            "Port already in use. Stop jetson_publisher / esp_bridge before running this suite.",
            file=sys.stderr,
        )
        report = RegressionReport(
            exit_code=2,
            host=env_info["host"],
            python=env_info["python"],
            pyserial=env_info["pyserial"],
            run_started_at=env_info["run_started_at"],
        )
        # bug_003: stdout / 파일 JSON 의 ensure_ascii 설정을 통일.
        print(json.dumps(report.to_dict(), ensure_ascii=False))
        return 2

    t_start = time.monotonic()
    t_deadline = t_start + args.timeout
    buf = bytearray()
    parser = RegressionParser(line_source=iter([]))  # 라인별로 직접 주입

    def _readline_from_serial() -> Iterator[str]:
        """시리얼에서 라인을 읽는 제너레이터 (timeout/taps 종료 조건 포함)."""
        nonlocal buf
        while True:
            if time.monotonic() >= t_deadline:
                break
            if parser.total_taps >= args.taps:
                break
            try:
                chunk = ser.read(256)
            except Exception:
                break
            if chunk:
                buf.extend(chunk)
            while b"\n" in buf:
                idx = buf.index(b"\n")
                raw = buf[:idx]
                buf = buf[idx + 1 :]
                try:
                    yield raw.decode("utf-8", errors="replace").strip()
                except Exception:
                    pass

    timed_out = False
    sigint_received = False  # bug_001: SIGINT 와 timeout 을 구분
    try:
        for line in _readline_from_serial():
            parser._process_line(line)
        if time.monotonic() >= t_deadline and parser.total_taps < args.taps:
            timed_out = True
    except KeyboardInterrupt:
        sigint_received = True
    finally:
        ser.close()

    duration = time.monotonic() - t_start
    report = build_report(
        parser=parser,
        uid_threshold=args.uid_threshold,
        ndef_threshold=args.ndef_threshold,
        ndef_expected=args.ndef_expected,
        healthcheck_expected=args.healthcheck_expected,
        required_taps=args.taps,
        run_duration=duration,
        timed_out=timed_out or sigint_received,
        expected_taps=args.expected_taps,
    )

    # bug_012: NFR 환경 정보 필드를 리포트에 주입 (spec.md §관측성).
    report.host = env_info["host"]
    report.python = env_info["python"]
    report.pyserial = env_info["pyserial"]
    report.run_started_at = env_info["run_started_at"]

    # bug_001: SIGINT 는 operator_abort(운영 에러, exit 2) 로, timeout 은 기존 판정 유지.
    if sigint_received:
        report.exit_code = 2
        report.failure_category = "operator_abort"
        report.failure_note = "operator aborted the run via SIGINT — 현재까지 수집된 데이터만 기록."
        report.timed_out = True

    # stdout / 파일 JSON 모두 ensure_ascii=False 로 통일 (bug_003).
    json_payload = json.dumps(report.to_dict(), ensure_ascii=False)
    print(json_payload)
    if args.report:
        Path(args.report).write_text(json_payload, encoding="utf-8")

    return report.exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
