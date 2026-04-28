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
