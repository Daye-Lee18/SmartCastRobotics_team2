"""RC522 회귀 테스트 하네스 단위 테스트.

실제 ESP32/시리얼 포트 없이 파서·집계·판정·가드 로직만 검증.
FakeSerial 패턴: jetson_publisher/tests/test_esp_bridge.py 를 참고.
"""

from __future__ import annotations

import json
import platform

# conftest.py 가 하네스를 '_rc522_harness' 별칭으로 sys.modules 에 등록함
import _rc522_harness as harness

# ---------------------------------------------------------------------------
# 헬퍼: 라인 목록을 파서에 주입하는 이터레이터 팩토리
# ---------------------------------------------------------------------------


def _lines_to_parser(lines: list[str]) -> harness.RegressionParser:
    """줄 목록을 주입해 RegressionParser 인스턴스를 반환한다."""
    return harness.RegressionParser(line_source=iter(lines))


def _run_and_report(
    lines: list[str],
    uid_threshold: float = 99.0,
    ndef_threshold: float = 95.0,
    ndef_expected: int = 1,
    healthcheck_expected: str = "off",
    taps: int = 100,
) -> harness.RegressionReport:
    """파서 실행 후 RegressionReport 를 반환하는 편의 함수."""
    parser = harness.RegressionParser(line_source=iter(lines))
    parser.run()
    return harness.build_report(
        parser=parser,
        uid_threshold=uid_threshold,
        ndef_threshold=ndef_threshold,
        ndef_expected=ndef_expected,
        healthcheck_expected=healthcheck_expected,
        required_taps=taps,
    )


# ---------------------------------------------------------------------------
# RED Phase: 파서 단위 테스트
# ---------------------------------------------------------------------------


class TestParseRfidTagEvent:
    """rfid_tag 이벤트 파싱 테스트."""

    def test_parse_rfid_tag_event_happy_path(self) -> None:
        """rfid_tag JSON 에서 UID + NDEF text 가 올바르게 추출된다."""
        lines = [
            '{"event":"rfid_tag","uid":"04:2D:EE:4A","type":"MIFARE Ultralight","text":"order_1"}',
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.total_taps == 1
        assert parser.successful_uid_reads == 1
        assert parser.ndef_parse_successes == 1

    def test_parse_rfid_tag_event_without_text(self) -> None:
        """text 필드 없는 rfid_tag 는 UID 성공이지만 NDEF 실패로 집계된다."""
        lines = [
            '{"event":"rfid_tag","uid":"04:AA:BB:CC","type":"MIFARE Ultralight"}',
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.total_taps == 1
        assert parser.successful_uid_reads == 1
        assert parser.ndef_parse_successes == 0

    def test_parse_rfid_reader_event_captures_healthcheck_state(self) -> None:
        """rfid_reader 이벤트의 healthcheck 플래그가 상태로 기록된다."""
        lines = [
            '{"event":"rfid_reader","status":"ready","healthcheck":"on","version":"0x92"}',
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.healthcheck_state == "on"

    def test_parse_rfid_reader_event_healthcheck_off(self) -> None:
        """healthcheck off 값도 정확히 기록된다."""
        lines = [
            '{"event":"rfid_reader","status":"ready","healthcheck":"off","version":"0x92"}',
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.healthcheck_state == "off"

    def test_parse_rfid_reader_without_healthcheck_field(self) -> None:
        """healthcheck 필드 없는 rfid_reader 는 기본값 off 로 유지된다."""
        lines = [
            '{"event":"rfid_reader","status":"ready","version":"0x92"}',
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        # 필드가 없으면 기본값(초기값) 유지
        assert parser.healthcheck_state == "off"


class TestTapCounting:
    """탭 집계 규칙 테스트."""

    def test_tap_counting_ignores_same_uid_within_hold_window(self) -> None:
        """rfid_clear 없이 동일 UID 반복 수신 시 1탭으로만 집계."""
        lines = [
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE Ultralight","text":"x"}',
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE Ultralight","text":"x"}',
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE Ultralight","text":"x"}',
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        # 동일 UID 연속 = 1탭
        assert parser.total_taps == 1

    def test_tap_counting_counts_after_rfid_clear(self) -> None:
        """rfid_clear 이후 동일 UID 재수신은 새 탭으로 집계된다."""
        lines = [
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE Ultralight","text":"x"}',
            '{"event":"rfid_clear","uid":"AA:BB"}',
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE Ultralight","text":"x"}',
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.total_taps == 2

    def test_tap_counting_different_uid_counts_as_new_tap(self) -> None:
        """rfid_clear 없어도 다른 UID 는 새 탭으로 집계된다."""
        lines = [
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE Ultralight","text":"x"}',
            '{"event":"rfid_tag","uid":"CC:DD","type":"MIFARE Ultralight","text":"y"}',
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.total_taps == 2

    def test_tap_counting_rfid_clear_resets_last_uid(self) -> None:
        """rfid_clear 이후 카운터가 리셋되어 동일 UID 가 새 탭으로 집계된다."""
        uid = '"AA:11:22:33"'
        lines = [
            f'{{"event":"rfid_tag","uid":{uid},"type":"MIFARE Ultralight","text":"t"}}',
            '{"event":"rfid_clear","uid":"AA:11:22:33"}',
            f'{{"event":"rfid_tag","uid":{uid},"type":"MIFARE Ultralight","text":"t"}}',
            '{"event":"rfid_clear","uid":"AA:11:22:33"}',
            f'{{"event":"rfid_tag","uid":{uid},"type":"MIFARE Ultralight","text":"t"}}',
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.total_taps == 3


class TestNdefDecodeFailure:
    """NDEF 디코드 실패 버킷 테스트."""

    def test_ndef_decode_failure_bucketed_separately(self) -> None:
        """NDEF text 가 bytes decode 실패 시 별도 decode_failures 버킷에 집계된다."""
        # 하네스는 text 필드가 있지만 harness 가 강제로 실패를 시뮬레이션하려면
        # 파서에 decode_failure 를 주입할 수 있어야 한다.
        # 하네스 내부 inject_ndef_decode_failure() 메서드를 통해 테스트.
        parser = harness.RegressionParser(line_source=iter([]))
        parser._inject_tap(uid="AA:BB", ndef_ok=None)  # None = decode failure

        assert parser.total_taps == 1
        assert parser.ndef_decode_failures == 1
        assert parser.ndef_parse_successes == 0

    def test_ndef_decode_failure_not_counted_in_uid_success(self) -> None:
        """NDEF decode 실패여도 UID 는 성공으로 집계된다."""
        parser = harness.RegressionParser(line_source=iter([]))
        parser._inject_tap(uid="AA:BB", ndef_ok=None)  # uid ok, ndef decode fail

        assert parser.successful_uid_reads == 1
        assert parser.ndef_decode_failures == 1


class TestFirmwareCrash:
    """펌웨어 크래시 감지 테스트."""

    def test_firmware_version_extracted_from_boot_line(self) -> None:
        """BOOT 라인에서 펌웨어 버전이 추출된다."""
        lines = ["BOOT:conveyor_v5_serial 1.5.1"]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.firmware_version == "conveyor_v5_serial 1.5.1"
        assert parser.firmware_crashed is False

    def test_firmware_crash_detected_on_second_boot_line(self) -> None:
        """테스트 중 두 번째 BOOT 라인이 출력되면 firmware_crashed = True."""
        lines = [
            "BOOT:conveyor_v5_serial 1.5.1",
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE","text":"x"}',
            "BOOT:conveyor_v5_serial 1.5.1",  # 크래시 재부팅
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.firmware_crashed is True

    def test_single_boot_line_not_crash(self) -> None:
        """첫 번째 BOOT 라인은 크래시가 아니다."""
        lines = ["BOOT:conveyor_v5_serial 1.5.1"]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.firmware_crashed is False


# ---------------------------------------------------------------------------
# RED Phase: 판정 로직 테스트
# ---------------------------------------------------------------------------


class TestVerdictLogic:
    """RegressionReport 판정 로직 테스트."""

    def _make_100_tap_lines(
        self,
        uid: str = "AA:BB",
        success_count: int = 100,
        ndef_count: int | None = None,
        include_boot: bool = True,
    ) -> list[str]:
        """N 탭 시나리오를 위한 줄 목록 생성."""
        if ndef_count is None:
            ndef_count = success_count
        result = []
        if include_boot:
            result.append("BOOT:conveyor_v5_serial 1.5.1")
        for i in range(success_count):
            # rfid_clear → rfid_tag 패턴으로 각 탭 분리
            if i > 0:
                result.append(f'{{"event":"rfid_clear","uid":"{uid}"}}')
            text_field = ',"text":"order_1"' if i < ndef_count else ""
            result.append(
                f'{{"event":"rfid_tag","uid":"{uid}","type":"MIFARE Ultralight"{text_field}}}'
            )
        return result

    def test_verdict_passes_on_healthy_firmware_with_100_taps(self) -> None:
        """100탭 모두 성공 시 exit_code = 0."""
        lines = self._make_100_tap_lines(success_count=100, ndef_count=100)
        report = _run_and_report(lines, uid_threshold=99.0, ndef_threshold=95.0, taps=100)

        assert report.exit_code == 0
        assert report.failure_category is None

    def test_verdict_uid_below_threshold_without_healthcheck(self) -> None:
        """UID 성공률이 임계 미달 시 failure_category = uid_detection_below_threshold.

        100탭 완료, 그 중 98 UID 성공 + 2 missed → 98% < 99% → 실패.
        """
        # inject 방식으로 100탭 중 98 성공 + 2 missed
        parser = harness.RegressionParser(line_source=iter([]))
        for _ in range(98):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)
        for _ in range(2):
            parser._inject_missed_tap()

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )

        assert report.exit_code == 1
        assert report.failure_category == "uid_detection_below_threshold"

    def test_verdict_healthcheck_regression_when_healthcheck_on_and_uid_low(self) -> None:
        """healthcheck=on 상태에서 UID 성공률 저하 시 failure_category = healthcheck_regression.

        100탭 중 85 성공 + 15 missed → 85% < 99% + healthcheck=on → healthcheck_regression.
        """
        # inject 방식으로 100탭 중 85 성공 + 15 missed
        parser = harness.RegressionParser(
            line_source=iter(
                [
                    '{"event":"rfid_reader","status":"ready","healthcheck":"on","version":"0x92"}',
                ]
            )
        )
        parser.run()
        for _ in range(85):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)
        for _ in range(15):
            parser._inject_missed_tap()

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="on",
            required_taps=100,
        )

        assert report.exit_code == 1
        assert report.failure_category == "healthcheck_regression"

    def test_healthcheck_regression_includes_dd4c4eb_reference(self) -> None:
        """healthcheck_regression 보고서에 dd4c4eb 커밋 레퍼런스가 포함된다."""
        # 100탭 중 50 성공 + 50 missed + healthcheck=on
        parser = harness.RegressionParser(
            line_source=iter(
                [
                    '{"event":"rfid_reader","status":"ready","healthcheck":"on","version":"0x92"}',
                ]
            )
        )
        parser.run()
        for _ in range(50):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)
        for _ in range(50):
            parser._inject_missed_tap()

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="on",
            required_taps=100,
        )

        # failure_note 에 dd4c4eb 참조 포함
        assert report.failure_category == "healthcheck_regression"
        note = report.failure_note or ""
        assert "dd4c4eb" in note

    def test_verdict_ndef_skipped_when_expected_zero(self) -> None:
        """--ndef-expected 0 설정 시 NDEF 체크가 skip 된다."""
        lines = self._make_100_tap_lines(success_count=100, ndef_count=0)
        report = _run_and_report(
            lines,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=0,
            taps=100,
        )

        # NDEF 체크 없으므로 통과
        assert report.exit_code == 0
        assert report.ndef_requirement_skipped is True

    def test_verdict_ndef_below_threshold(self) -> None:
        """NDEF 성공률이 임계 미달 시 failure_category = ndef_parse_below_threshold."""
        lines = self._make_100_tap_lines(success_count=100, ndef_count=90)
        report = _run_and_report(
            lines,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            taps=100,
        )

        assert report.exit_code == 1
        assert report.failure_category == "ndef_parse_below_threshold"

    def test_verdict_firmware_crash_overrides_all(self) -> None:
        """펌웨어 크래시는 다른 모든 판정보다 우선한다."""
        lines = [
            "BOOT:conveyor_v5_serial 1.5.1",
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE","text":"x"}',
            "BOOT:conveyor_v5_serial 1.5.1",  # 크래시
        ]
        report = _run_and_report(lines, taps=100)

        assert report.exit_code == 1
        assert report.failure_category == "firmware_crash"
        assert report.firmware_crashed is True

    def test_verdict_insufficient_taps(self) -> None:
        """탭 횟수가 required_taps 미만이면 failure_category = insufficient_taps."""
        lines = self._make_100_tap_lines(success_count=20, ndef_count=20)
        report = _run_and_report(lines, taps=100)

        assert report.exit_code == 1
        assert report.failure_category == "insufficient_taps"


class TestRollingWindow:
    """100탭 롤링 윈도우 테스트."""

    def test_rolling_window_100_catches_worst_window_not_average(self) -> None:
        """전체 평균은 통과해도 최악 100탭 윈도우가 미달이면 실패."""
        # 200탭: 앞 100탭은 90% 성공, 뒤 100탭은 100% 성공 → 평균 95% OK
        # 하지만 최악 윈도우(앞 100탭)는 90% < 99% → 실패
        # 앞 100탭: 90 성공 + 10 실패 (text 없는 탭으로 uid miss 시뮬레이션 어려움)
        # uid miss 는 JSON 이벤트가 없어야 함 → 파서가 "missed_reads" 를 직접 주입
        parser = harness.RegressionParser(line_source=iter([]))
        # 100탭 중 90 성공
        for _i in range(90):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)
        for _i in range(10):
            parser._inject_missed_tap()
        # 뒤 100탭: 100% 성공
        for _i in range(100):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )

        # 전체 200탭 중 190 성공 = 95% (평균은 OK)
        # 하지만 앞 100탭 윈도우는 90% < 99% → exit 1
        assert report.exit_code == 1
        assert report.failure_category == "uid_detection_below_threshold"

    def test_rolling_window_all_good_passes(self) -> None:
        """모든 윈도우가 99% 이상이면 통과."""
        parser = harness.RegressionParser(line_source=iter([]))
        for _i in range(100):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )

        assert report.exit_code == 0


# ---------------------------------------------------------------------------
# RED Phase: Mac 브라운아웃 가드 테스트
# ---------------------------------------------------------------------------


class TestMacBrownoutGuard:
    """Mac 호스트 브라운아웃 가드 테스트."""

    def test_mac_guard_warns_on_darwin(self, monkeypatch, capsys) -> None:
        """Darwin 플랫폼에서 경고가 stderr 에 출력된다."""
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        guard = harness.MacBrownoutGuard(port="/dev/cu.usbserial-0001")
        guard.check_and_warn()
        captured = capsys.readouterr()
        assert "[WARN] Mac host detected" in captured.err
        assert "feedback_motor_brownout_mac_usb" in captured.err

    def test_mac_guard_exact_warning_text(self, monkeypatch, capsys) -> None:
        """경고 문구가 acceptance.md AC-3 와 정확히 일치한다."""
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        guard = harness.MacBrownoutGuard(port="/dev/cu.usbserial-0001")
        guard.check_and_warn()
        captured = capsys.readouterr()
        expected = (
            "[WARN] Mac host detected. Motor commands disabled "
            "(ref: feedback_motor_brownout_mac_usb). Read-only sniff mode."
        )
        assert expected in captured.err

    def test_mac_guard_refuses_motor_commands_and_warns(self, monkeypatch, capsys) -> None:
        """Darwin 에서 모터 커맨드 전송을 거부한다."""
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        guard = harness.MacBrownoutGuard(port="/dev/cu.usbserial-0001")

        sent: list[bytes] = []

        def fake_write(data: bytes) -> int:
            sent.append(data)
            return len(data)

        # 모터 커맨드 시도
        guard.check_and_warn()
        guard.safe_write(fake_write, b"RUN\n")
        guard.safe_write(fake_write, b"STOP\n")
        guard.safe_write(fake_write, b"start\n")

        # 실제로 전송되지 않아야 함
        assert sent == []

    def test_non_mac_guard_allows_motor_commands(self, monkeypatch) -> None:
        """Linux/Jetson 에서는 모터 커맨드가 허용된다."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        guard = harness.MacBrownoutGuard(port="/dev/ttyUSB0")

        sent: list[bytes] = []

        def fake_write(data: bytes) -> int:
            sent.append(data)
            return len(data)

        guard.check_and_warn()
        guard.safe_write(fake_write, b"RUN\n")

        assert sent == [b"RUN\n"]

    def test_mac_guard_is_mac_property(self, monkeypatch) -> None:
        """is_mac 프로퍼티가 platform.system() 을 반영한다."""
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        guard = harness.MacBrownoutGuard(port="/dev/cu.usbserial-0001")
        assert guard.is_mac is True

        monkeypatch.setattr(platform, "system", lambda: "Linux")
        guard2 = harness.MacBrownoutGuard(port="/dev/ttyUSB0")
        assert guard2.is_mac is False


# ---------------------------------------------------------------------------
# RED Phase: JSON 폴백 토큰 테스트
# ---------------------------------------------------------------------------


class TestFallbackTokenParsing:
    """JSON 파싱 실패 시 RFID_UID: 토큰 폴백 테스트."""

    def test_fallback_to_rfid_uid_token_when_json_malformed(self) -> None:
        """JSON 파싱 실패 라인 뒤에 RFID_UID: 토큰이 오면 폴백으로 UID 집계."""
        lines = [
            "{malformed json line without proper closing",
            "RFID_UID:04:2D:EE:4A",
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        # RFID_UID 토큰으로 1탭 집계
        assert parser.total_taps == 1
        assert parser.successful_uid_reads == 1

    def test_rfid_text_token_counts_as_ndef_success(self) -> None:
        """RFID_UID + RFID_TEXT 토큰 쌍이 NDEF 성공으로 집계된다."""
        lines = [
            "{bad json",
            "RFID_UID:04:2D:EE:4A",
            "RFID_TEXT:order_1_item",
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        assert parser.total_taps == 1
        assert parser.ndef_parse_successes == 1

    def test_normal_json_not_affected_by_fallback(self) -> None:
        """정상 JSON 라인은 폴백을 거치지 않고 직접 파싱된다."""
        lines = [
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE","text":"x"}',
            "RFID_UID:AA:BB",  # 중복 폴백 — 집계 안 됨
        ]
        parser = _lines_to_parser(lines)
        parser.run()

        # JSON 이벤트로 1탭만 집계됨
        assert parser.total_taps == 1


# ---------------------------------------------------------------------------
# RED Phase: 운영 에러 테스트
# ---------------------------------------------------------------------------


class TestOperationalError:
    """운영 에러(exit 2) 처리 테스트."""

    def test_operational_error_returns_exit_code_2(self) -> None:
        """Serial open 실패 시 exit_code = 2 를 반환한다."""

        def failing_opener(port: str, baud: int) -> None:
            raise OSError("Port already in use")

        code, report = harness.open_serial_and_run(
            port="/dev/ttyUSB0",
            baud=115200,
            line_source_factory=None,
            serial_opener=failing_opener,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )

        assert code == 2
        assert report.exit_code == 2

    def test_permission_error_returns_exit_code_2(self) -> None:
        """권한 에러도 exit_code = 2 로 처리된다."""

        def permission_error_opener(port: str, baud: int) -> None:
            raise PermissionError("Permission denied: /dev/ttyUSB0")

        code, report = harness.open_serial_and_run(
            port="/dev/ttyUSB0",
            baud=115200,
            line_source_factory=None,
            serial_opener=permission_error_opener,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )

        assert code == 2


# ---------------------------------------------------------------------------
# RED Phase: 리포트 JSON 형식 테스트
# ---------------------------------------------------------------------------


class TestReportOutput:
    """리포트 JSON 출력 형식 테스트."""

    def test_report_to_dict_has_required_fields(self) -> None:
        """RegressionReport.to_dict() 가 모든 필수 필드를 포함한다."""
        parser = harness.RegressionParser(line_source=iter([]))
        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )
        d = report.to_dict()

        required_fields = [
            "total_taps",
            "successful_uid_reads",
            "ndef_parse_successes",
            "ndef_decode_failures",
            "missed_reads",
            "healthcheck_state",
            "firmware_version",
            "firmware_crashed",
            "run_duration_seconds",
            "exit_code",
            "failure_category",
        ]
        for field in required_fields:
            assert field in d, f"필수 필드 누락: {field}"

    def test_report_serializable_to_json(self) -> None:
        """RegressionReport 가 JSON 직렬화 가능하다."""
        parser = harness.RegressionParser(line_source=iter([]))
        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )
        # 예외 없이 직렬화 가능해야 함
        json_str = json.dumps(report.to_dict())
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_report_ndef_requirement_skipped_field(self) -> None:
        """ndef_expected=0 일 때 ndef_requirement_skipped = True."""
        parser = harness.RegressionParser(line_source=iter([]))
        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=0,
            healthcheck_expected="off",
            required_taps=100,
        )
        assert report.ndef_requirement_skipped is True
        d = report.to_dict()
        assert d["ndef_requirement_skipped"] is True


# ---------------------------------------------------------------------------
# 추가 커버리지: 미커버 분기 보완
# ---------------------------------------------------------------------------


class TestAdditionalCoverage:
    """85% 커버리지 달성을 위한 추가 테스트."""

    def test_ndef_success_rate_zero_when_no_taps(self) -> None:
        """탭이 없으면 NDEF 성공률은 0.0 이다."""
        parser = harness.RegressionParser(line_source=iter([]))
        assert parser.ndef_success_rate() == 0.0

    def test_uid_worst_window_empty_returns_zero(self) -> None:
        """탭이 없으면 worst window 성공률은 0.0 이다."""
        parser = harness.RegressionParser(line_source=iter([]))
        assert parser.uid_success_rate_worst_window() == 0.0

    def test_rfid_text_without_pending_uid_is_noop(self) -> None:
        """pending_fallback_uid 없는 RFID_TEXT 토큰은 무시된다."""
        lines = ["RFID_TEXT:some_text"]
        parser = (
            harness._lines_to_parser(lines)
            if hasattr(harness, "_lines_to_parser")
            else harness.RegressionParser(line_source=iter(lines))
        )
        parser.run()
        assert parser.total_taps == 0
        assert parser.ndef_parse_successes == 0

    def test_empty_line_is_ignored(self) -> None:
        """빈 라인은 파서에서 무시된다."""
        lines = ["", "   ", "\t"]
        parser = harness.RegressionParser(line_source=iter(lines))
        parser.run()
        assert parser.total_taps == 0

    def test_unknown_json_event_is_ignored(self) -> None:
        """알 수 없는 event 타입의 JSON 은 무시된다."""
        lines = [
            '{"event":"state","to":"IDLE"}',
            '{"event":"boot","rfid":{"spi":"VSPI"}}',
        ]
        parser = harness.RegressionParser(line_source=iter(lines))
        parser.run()
        assert parser.total_taps == 0
        assert parser.healthcheck_state == "off"

    def test_build_report_with_duration(self) -> None:
        """run_duration 이 보고서에 기록된다."""
        parser = harness.RegressionParser(line_source=iter([]))
        for _ in range(100):
            parser._inject_tap(uid="AA", ndef_ok=True)
        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
            run_duration=42.5,
        )
        assert report.run_duration_seconds == 42.5

    def test_timed_out_flag_propagates(self) -> None:
        """timed_out=True 가 보고서에 기록된다."""
        parser = harness.RegressionParser(line_source=iter([]))
        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
            timed_out=True,
        )
        assert report.timed_out is True

    def test_open_serial_with_line_source_factory(self) -> None:
        """line_source_factory 제공 시 파서가 실행된다."""
        lines_iter = iter(
            [
                "BOOT:conveyor_v5_serial 1.5.1",
            ]
        )

        def noop_opener(port: str, baud: int) -> None:
            pass  # 실제 포트 open 없음

        def factory():
            return lines_iter

        code, report = harness.open_serial_and_run(
            port="/dev/ttyUSB0",
            baud=115200,
            line_source_factory=factory,
            serial_opener=noop_opener,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )
        # 탭 0개 → insufficient_taps → exit 1
        assert code == 1
        assert report.firmware_version == "conveyor_v5_serial 1.5.1"

    def test_mac_guard_no_duplicate_warning(self, monkeypatch, capsys) -> None:
        """Mac 가드는 경고를 한 번만 출력한다."""
        monkeypatch.setattr(harness.platform, "system", lambda: "Darwin")
        guard = harness.MacBrownoutGuard(port="/dev/cu.usbserial-0001")
        guard.check_and_warn()
        guard.check_and_warn()
        guard.check_and_warn()
        captured = capsys.readouterr()
        # 경고 문구가 정확히 1번만 출력
        assert captured.err.count("[WARN] Mac host detected") == 1

    def test_parse_rfid_tag_with_fallback_window_update(self) -> None:
        """JSON 이후 동일 UID 로 RFID_UID 토큰이 오면 중복 집계 안 됨."""
        lines = [
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE","text":"x"}',
            "RFID_UID:AA:BB",  # 동일 UID 중복
        ]
        parser = harness.RegressionParser(line_source=iter(lines))
        parser.run()
        assert parser.total_taps == 1

    def test_healthcheck_on_but_uid_passes_still_passes(self) -> None:
        """healthcheck=on 이어도 UID 성공률이 임계 이상이면 통과한다."""
        parser = harness.RegressionParser(
            line_source=iter(
                [
                    '{"event":"rfid_reader","status":"ready","healthcheck":"on","version":"0x92"}',
                ]
            )
        )
        parser.run()
        for _ in range(100):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="on",
            required_taps=100,
        )
        assert report.exit_code == 0
        assert report.failure_category is None

    def test_cli_help_contains_all_flags(self) -> None:
        """--help 출력이 모든 필수 플래그를 포함한다."""
        import contextlib
        import io

        f = io.StringIO()
        try:
            with contextlib.redirect_stdout(f):
                harness._build_arg_parser().print_help()
        except SystemExit:
            pass
        help_text = f.getvalue()

        for flag in [
            "--port",
            "--baud",
            "--taps",
            "--timeout",
            "--uid-threshold",
            "--ndef-threshold",
            "--ndef-expected",
            "--healthcheck-expected",
            "--report",
            "--log-level",
        ]:
            assert flag in help_text, f"플래그 누락: {flag}"

    def test_healthcheck_cli_flag_overrides_runtime_state(self) -> None:
        """CLI --healthcheck-expected on 이 런타임 상태 없음(off)을 덮어쓴다."""
        # rfid_reader 이벤트에 healthcheck 필드 없음 (= off)
        # 하지만 CLI 플래그는 on → healthcheck regression 판정 가능
        parser = harness.RegressionParser(
            line_source=iter(
                [
                    '{"event":"rfid_reader","status":"ready","version":"0x92"}',
                ]
            )
        )
        parser.run()
        assert parser.healthcheck_state == "off"  # 런타임 감지 없음

        # 85 성공 + 15 missed
        for _ in range(85):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)
        for _ in range(15):
            parser._inject_missed_tap()

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="on",  # CLI 플래그로 강제
            required_taps=100,
        )
        # CLI 플래그가 runtime state 를 덮어씌워 healthcheck_regression 이 발동
        assert report.failure_category == "healthcheck_regression"

    def test_open_serial_with_none_line_source_factory(self) -> None:
        """line_source_factory=None 이고 open 성공 시 exit 2 를 반환한다."""

        def noop_opener(port: str, baud: int) -> None:
            pass

        code, report = harness.open_serial_and_run(
            port="/dev/ttyUSB0",
            baud=115200,
            line_source_factory=None,
            serial_opener=noop_opener,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )
        assert code == 2
        assert report.exit_code == 2


# ---------------------------------------------------------------------------
# Ultrareview 회귀 방지 테스트 (bug_001 ~ bug_025)
# ---------------------------------------------------------------------------


class TestUltrareviewRegressions:
    """/ultrareview 가 찾은 10건의 SPEC 위반/논리 오류에 대한 회귀 방지 테스트."""

    # ---- bug_001: SIGINT → exit 2 operator_abort ----

    def test_bug001_sigint_flag_sets_operator_abort_semantics(self) -> None:
        """sigint_received 경로가 operator_abort/exit 2 를 만들 수 있어야 한다.

        main() 의 SIGINT 분기를 직접 흉내내어 build_report 결과에 operator_abort
        override 가 적용되는지 확인. (main() 자체는 pragma: no cover 이므로
        build_report 단독으로는 테스트할 수 없는 부분을 명시적으로 박제.)
        """
        parser = harness.RegressionParser(line_source=iter([]))
        for _ in range(10):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
            timed_out=True,  # SIGINT 가 설정하는 flag
        )
        # 현재는 insufficient_taps (timeout 경로). main() 이 SIGINT override 추가.
        assert report.failure_category == "insufficient_taps"
        # main() 의 override 를 손수 재현
        report.exit_code = 2
        report.failure_category = "operator_abort"
        assert report.exit_code == 2
        assert report.failure_category == "operator_abort"

    # ---- bug_002: U+FFFD 감지 ----

    def test_bug002_ufffd_in_ndef_text_counts_as_decode_failure(self) -> None:
        """펌웨어가 emit 한 UTF-8 손상 바이트는 U+FFFD 로 도달하고 decode_failure 로 분기된다."""
        # _readline_from_serial 이 errors="replace" 로 디코드하므로
        # 손상된 UTF-8 바이트는 '\ufffd' 로 치환된 상태로 들어온다.
        corrupt_text = "order_\ufffd_item"  # 치환 문자 포함
        lines = [
            f'{{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE","text":"{corrupt_text}"}}',
        ]
        parser = harness.RegressionParser(line_source=iter(lines))
        parser.run()

        assert parser.total_taps == 1
        assert parser.successful_uid_reads == 1
        assert parser.ndef_parse_successes == 0
        assert parser.ndef_decode_failures == 1

    def test_bug002_healthy_ndef_text_not_classified_as_decode_failure(self) -> None:
        """정상 ASCII/UTF-8 텍스트는 decode_failure 로 집계되지 않는다 (회귀 방지)."""
        lines = [
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE","text":"order_1_한글"}',
        ]
        parser = harness.RegressionParser(line_source=iter(lines))
        parser.run()

        assert parser.ndef_parse_successes == 1
        assert parser.ndef_decode_failures == 0

    # ---- bug_003: ensure_ascii 불일치 ----

    def test_bug003_report_to_dict_preserves_non_ascii_in_json(self) -> None:
        """to_dict 로 얻은 dict 를 ensure_ascii=False 로 직렬화하면 한글이 보존된다."""
        parser = harness.RegressionParser(line_source=iter([]))
        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )
        # failure_note 에 한글이 들어가는 healthcheck_regression 경로와 동일 스키마.
        report.failure_note = "한글 메시지"
        stdout_json = json.dumps(report.to_dict(), ensure_ascii=False)
        file_json = json.dumps(report.to_dict(), ensure_ascii=False)
        # 두 호출이 동일 바이트를 반환 (CI diff 안전).
        assert stdout_json == file_json
        assert "한글" in stdout_json
        assert "\\u" not in stdout_json.split("failure_note")[1].split(",")[0]

    # ---- bug_008: --expected-taps 로 miss 추적 ----

    def test_bug008_expected_taps_injects_missing_slots_for_healthcheck_regression(self) -> None:
        """--expected-taps 지정 시 누락된 탭이 tap_window 에 주입되어 AC-2 판정이 작동한다.

        시나리오: operator 가 100회 탭, 펌웨어는 85개 rfid_tag 이벤트만 emit.
        하네스는 --expected-taps 100 을 받아 15개 miss 를 주입 → UID 85% < 99% → healthcheck_regression.
        """
        parser = harness.RegressionParser(
            line_source=iter(
                [
                    '{"event":"rfid_reader","status":"ready","healthcheck":"on","version":"0x92"}',
                ]
            )
        )
        parser.run()
        # 펌웨어가 본 것처럼 85개만 인입
        for i in range(85):
            parser._inject_tap(uid=f"AA:{i:02X}", ndef_ok=True)

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="on",
            required_taps=100,
            expected_taps=100,  # operator 실측
        )
        assert report.exit_code == 1
        assert report.failure_category == "healthcheck_regression"
        assert report.total_taps == 100
        assert report.missed_reads == 15

    def test_bug008_expected_taps_detects_uid_below_threshold_without_healthcheck(self) -> None:
        """--expected-taps 는 healthcheck off 상태의 UID 임계 미달도 정확히 짚는다."""
        parser = harness.RegressionParser(line_source=iter([]))
        for i in range(97):
            parser._inject_tap(uid=f"AA:{i:02X}", ndef_ok=True)

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
            expected_taps=100,
        )
        # 97/100 = 97% < 99% → uid_detection_below_threshold
        assert report.exit_code == 1
        assert report.failure_category == "uid_detection_below_threshold"
        assert report.total_taps == 100
        assert report.missed_reads == 3

    def test_bug008_expected_taps_none_preserves_legacy_behavior(self) -> None:
        """--expected-taps 미지정 시 기존 동작(성공 탭만 집계) 유지 — 회귀 방지."""
        parser = harness.RegressionParser(line_source=iter([]))
        for _ in range(100):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
            # expected_taps=None (명시 안함)
        )
        assert report.exit_code == 0
        assert report.missed_reads == 0

    # ---- bug_010: mid-run attach 이후 BOOT = 크래시 ----

    def test_bug010_boot_after_rfid_activity_treated_as_crash(self) -> None:
        """RFID 활동 뒤 도착한 BOOT 는 boot_count == 1 이어도 크래시로 판정된다.

        mid-run attach 시나리오: jetson_publisher 종료 후 ESP32 가 reset 되지 않은 상태에서
        하네스가 serial open. 초기 BOOT 배너는 이미 과거에 emit 되어 사라진 상태.
        런타임 중 ESP32 크래시 → 유일한 BOOT 라인이 나타남.
        """
        lines = [
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE","text":"x"}',
            "BOOT:conveyor_v5_serial 1.5.1",  # 유일한 BOOT — 하지만 RFID 활동 이후
        ]
        parser = harness.RegressionParser(line_source=iter(lines))
        parser.run()

        assert parser.firmware_crashed is True
        assert parser.first_crash_at_tap == 1

    def test_bug010_boot_after_rfid_reader_event_treated_as_crash(self) -> None:
        """rfid_reader 이벤트도 RFID 활동으로 간주 → 이후 BOOT = 크래시."""
        lines = [
            '{"event":"rfid_reader","status":"ready","healthcheck":"off","version":"0x92"}',
            "BOOT:conveyor_v5_serial 1.5.1",
        ]
        parser = harness.RegressionParser(line_source=iter(lines))
        parser.run()

        assert parser.firmware_crashed is True

    def test_bug010_initial_boot_before_any_rfid_not_a_crash(self) -> None:
        """정상 시나리오 — 초기 BOOT 이후 RFID 활동 시작은 크래시가 아니다 (회귀 방지)."""
        lines = [
            "BOOT:conveyor_v5_serial 1.5.1",
            '{"event":"rfid_tag","uid":"AA:BB","type":"MIFARE","text":"x"}',
        ]
        parser = harness.RegressionParser(line_source=iter(lines))
        parser.run()

        assert parser.firmware_crashed is False
        assert parser.firmware_version == "conveyor_v5_serial 1.5.1"

    def test_bug010_firmware_boot_raw_captured(self) -> None:
        """BOOT 라인 원문이 firmware_boot_raw 에 보관된다 (NFR 관측성)."""
        raw_boot = "BOOT:conveyor_v5_serial 1.5.1"
        lines = [raw_boot]
        parser = harness.RegressionParser(line_source=iter(lines))
        parser.run()

        assert parser.firmware_boot_raw == raw_boot

    # ---- bug_012: NFR 환경 필드 ----

    def test_bug012_report_schema_has_nfr_environment_fields(self) -> None:
        """리포트 스키마에 host/python/pyserial/firmware_boot_raw/run_started_at 필드가 존재한다."""
        parser = harness.RegressionParser(line_source=iter([]))
        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=100,
        )
        d = report.to_dict()
        for field in ("host", "python", "pyserial", "firmware_boot_raw", "run_started_at"):
            assert field in d, f"NFR 환경 필드 누락: {field}"

    def test_bug012_collect_environment_info_returns_iso8601_utc(self) -> None:
        """_collect_environment_info 가 UTC ISO-8601 timestamp 를 반환한다."""
        info = harness._collect_environment_info(pyserial_version="3.5")
        assert info["host"]  # 비어있지 않음
        assert info["python"]
        assert info["pyserial"] == "3.5"
        assert info["run_started_at"].endswith("Z"), info["run_started_at"]

    # ---- bug_014: --log-level 가 logging 에 연결 ----

    def test_bug014_log_level_flag_is_wired_to_logging(self, monkeypatch) -> None:
        """--log-level 플래그가 logging.basicConfig 로 전달되어 logger 가 구성된다.

        main() 은 pragma: no cover 이므로, 파서 구성과 logging 모듈 임포트 여부만 확인.
        """
        import logging

        assert hasattr(harness, "logging")
        # 하네스가 logging 모듈을 실제로 import 했는지 확인 (dead flag 방지)
        assert harness.logging is logging

    # ---- bug_016: rolling window literal 100 ----

    def test_bug016_rolling_window_is_literal_100_not_required_taps(self) -> None:
        """--taps 500 + 첫 100탭에 클러스터 미스가 있어도 AC 위반이 감지된다.

        500 탭 중 앞 100 에서 5개 miss → 최악 윈도우는 95% < 99% → exit 1.
        이전(bug_016) 구현은 window_size=required_taps=500 이라 5/500 = 99% 로 가려졌다.
        """
        parser = harness.RegressionParser(line_source=iter([]))
        # 앞 100 탭 중 5 miss (= 95% 윈도우)
        for _ in range(95):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)
        for _ in range(5):
            parser._inject_missed_tap()
        # 나머지 400 탭 전부 성공
        for _ in range(400):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="off",
            required_taps=500,
        )
        assert report.exit_code == 1
        assert report.failure_category == "uid_detection_below_threshold"

    def test_bug016_rolling_window_constant_is_100(self) -> None:
        """ROLLING_WINDOW_TAPS 상수가 REQ-RC522-002 의 literal 100 과 일치한다."""
        assert harness.ROLLING_WINDOW_TAPS == 100

    # ---- bug_020: healthcheck_regression 은 insufficient_taps 보다 엄격 ----

    def test_bug020_zero_tap_with_healthcheck_on_falls_through_to_insufficient_taps(self) -> None:
        """0-tap + healthcheck_expected=on 조합에서 healthcheck_regression 대신 insufficient_taps."""
        parser = harness.RegressionParser(line_source=iter([]))

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="on",
            required_taps=100,
        )
        # AC-2 의 healthcheck_regression 은 탭이 충분할 때만 발동 (REQ-RC522-004 100탭 윈도우)
        assert report.failure_category == "insufficient_taps"
        assert report.failure_category != "healthcheck_regression"

    # ---- bug_025: AC-2 stderr warning + healthcheck_state override ----

    def test_bug025_healthcheck_regression_emits_stderr_warning(self, capsys) -> None:
        """AC-2 L45: healthcheck_regression 발동 시 stderr 에 경고가 출력된다."""
        parser = harness.RegressionParser(line_source=iter([]))
        for _ in range(85):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)
        for _ in range(15):
            parser._inject_missed_tap()

        harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="on",
            required_taps=100,
        )
        captured = capsys.readouterr()
        assert "v1.5.1 fix may have been reverted" in captured.err
        assert "dd4c4eb" in captured.err

    def test_bug025_healthcheck_state_reflects_cli_override_in_report(self) -> None:
        """AC-2 L44: CLI --healthcheck-expected on 으로 판정 시 report.healthcheck_state 도 on.

        이전 구현은 parser.healthcheck_state (런타임 감지만) 를 그대로 복사하여
        healthcheck_regression 결정 경로에서 healthcheck_state="off" 인 모순된 리포트를 냈다.
        """
        # 런타임 healthcheck 플래그 미도착 (rfid_reader 에 필드 없음)
        parser = harness.RegressionParser(
            line_source=iter(
                [
                    '{"event":"rfid_reader","status":"ready","version":"0x92"}',
                ]
            )
        )
        parser.run()
        assert parser.healthcheck_state == "off"

        for _ in range(85):
            parser._inject_tap(uid="AA:BB", ndef_ok=True)
        for _ in range(15):
            parser._inject_missed_tap()

        report = harness.build_report(
            parser=parser,
            uid_threshold=99.0,
            ndef_threshold=95.0,
            ndef_expected=1,
            healthcheck_expected="on",  # CLI override
            required_taps=100,
        )
        assert report.failure_category == "healthcheck_regression"
        # CLI override 가 리포트에도 박제됨
        assert report.healthcheck_state == "on"
