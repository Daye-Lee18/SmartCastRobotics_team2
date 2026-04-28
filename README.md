# SmartCast Robotics

SmartCast Robotics is a monorepo for the FMS UI, backend services, database
schema, and device control code.

## Repository Layout

```text
ui/       User interfaces
server/   Backend services and database schema
device/   ROS, robot, camera, and controller code
docs/     Design and test documents
scripts/  Local development scripts
```

## Test Scripts

Run all Python unit tests from the repository root:

```bash
./scripts/run_all_tests.sh
```

Use this script when:

- before creating a pull request
- after changing shared module structure, imports, or package names
- after editing more than one service/module
- before merging a pull request into `main`
- when checking that the cloned repository is set up correctly

For a small change in one module, run only that module's tests:

```bash
pytest server/main_service
pytest server/ai_service
pytest ui/pyqt/factory_operator
pytest device/smartcast_arm/control
pytest device/smartcast_amr/smartcast_amr_control
pytest device/camera
```

Run module-level tests when:

- editing code inside only one module
- adding or renaming files in a module's `src/` package
- adding unit tests under that module's `tests/unit/`
- debugging a failure before running the full test script

Each Python module follows this basic structure:

```text
module/
├── src/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── requirements.txt
└── pytest.ini
```

## Unit Test 작성 위치

팀원들은 자기 담당 모듈 안의 `tests/unit/` 폴더에 unit test 코드를 작성합니다.
실제 구현 코드는 `src/`에 두고, 테스트 코드는 같은 모듈의 `tests/unit/`에 둡니다.

예를 들어 `main_service`의 `task_manager.py`를 테스트한다면:

```text
server/main_service/
├── src/main_service/
│   └── task_manager.py
└── tests/unit/
    └── test_task_manager.py
```

담당 모듈별 unit test 작성 위치:

```text
server/main_service/tests/unit/                         # Main Service
server/ai_service/tests/unit/                           # AI Service
ui/pyqt/factory_operator/tests/unit/                    # PyQt UI
device/smartcast_arm/control/tests/unit/                # Robot Arm
device/smartcast_amr/smartcast_amr_control/tests/unit/  # AMR
device/camera/tests/unit/                               # Camera
```

테스트 파일 이름은 `test_*.py` 형식으로 작성합니다.

예:

```text
test_task_manager.py
test_robot_adapter.py
test_camera_capture.py
```

자기 담당 모듈 전체 unit test를 실행하려면:

```bash
pytest server/main_service
```

특정 테스트 파일 하나만 실행하려면:

```bash
pytest server/main_service/tests/unit/test_task_manager.py
```

여러 모듈을 수정했거나 PR을 만들기 전에는 전체 테스트를 실행합니다.

```bash
./scripts/run_all_tests.sh
```

## 공통 데이터 모델과 Enum 사용 기준

`main_service`에서 여러 모듈이 함께 사용하는 데이터 구조와 상태값은 아래 파일에서 관리합니다.

```text
server/main_service/src/main_service/
├── pydantic_models.py  # 데이터 구조, request/response, DB record 모델
└── enums.py            # 상태값, 작업 타입, 고정 코드값
```

### `pydantic_models.py`

`pydantic_models.py`는 컴포넌트 사이에서 주고받는 데이터의 형식과 검증 규칙을 정의할 때 사용합니다.

사용하는 경우:

- API request/response 데이터 구조를 정의할 때
- DB에서 조회한 record 구조를 코드에서 명확히 표현할 때
- Task, Order, Item, Equipment, AMR 관련 데이터 필드와 타입을 고정해야 할 때
- 필수값, 선택값, 숫자 범위 같은 validation이 필요할 때
- 여러 모듈이 같은 데이터 구조를 공유해야 할 때

예:

```python
from main_service.pydantic_models import CreateOrdInput

order = CreateOrdInput(user_id=1)
```

### `enums.py`

`enums.py`는 상태값이나 작업 타입처럼 정해진 값만 사용해야 하는 경우에 사용합니다.

사용하는 경우:

- 주문 상태, 설비 상태, AMR 상태처럼 값이 정해져 있을 때
- 문자열 오타로 인한 오류를 줄이고 싶을 때
- DB, API, State Diagram, Sequence Diagram에서 같은 상태명을 공유해야 할 때
- 조건문에서 상태값을 비교해야 할 때

예:

```python
from main_service.enums import OrdStat, EquipStat

if order_status == OrdStat.RCVD:
    ...

if equipment_status == EquipStat.IDLE:
    ...
```

새로운 상태값이나 작업 타입이 필요하면 문자열을 각 파일에 직접 흩어 쓰지 말고,
먼저 `enums.py`에 추가한 뒤 필요한 모듈에서 import해서 사용합니다.

새로운 데이터 구조가 필요하면 각 모듈 안에 중복 class를 만들지 말고,
공통으로 쓰는 구조인지 확인한 뒤 `pydantic_models.py`에 추가합니다.
