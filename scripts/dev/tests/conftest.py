"""pytest conftest: 하네스 모듈을 올바른 경로로 먼저 등록한다.

문제: scripts/tests/test_rc522_regression.py 와 scripts/test_rc522_regression.py
가 동일한 basename 을 가져 pytest 가 이름 충돌을 일으킨다.

해결: conftest.py 에서 importlib 로 하네스를 '_harness' 별칭으로 등록하고,
pytest 의 자동 수집 전에 sys.modules 에 올바른 파일을 바인딩한다.
테스트 파일은 'import test_rc522_regression as harness' 가 아니라
conftest 가 주입한 모듈을 사용한다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
HARNESS_PATH = SCRIPTS_DIR / "test_rc522_regression.py"


# pytest 수집 전에 하네스를 올바른 경로로 sys.modules 에 등록.
# 'test_rc522_regression' 키는 pytest 가 tests/ 파일을 로드하기 전에 덮어쓴다.
# '_rc522_harness' 별칭도 함께 등록해 테스트 파일이 명시적으로 사용 가능.
def _load_harness():
    spec = importlib.util.spec_from_file_location("_rc522_harness", HARNESS_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"하네스 파일을 로드할 수 없습니다: {HARNESS_PATH}")
    mod = importlib.util.module_from_spec(spec)
    # dataclasses 등이 __module__ 로 sys.modules 를 조회하므로 exec 전에 등록 필요
    sys.modules["_rc522_harness"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# 두 이름 모두 등록 (테스트 파일에서 어느 이름으로 import 해도 동일 객체)
if "_rc522_harness" not in sys.modules:
    _harness_mod = _load_harness()
    sys.modules["_rc522_harness"] = _harness_mod
    # test_rc522_regression 이름도 올바른 모듈로 사전 등록
    # pytest 가 tests/ 파일을 이 이름으로 등록하기 전에 scripts/ 버전을 선점
    sys.modules["test_rc522_regression"] = _harness_mod
