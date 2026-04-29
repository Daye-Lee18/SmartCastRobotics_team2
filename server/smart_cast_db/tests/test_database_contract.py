import importlib
import os
import sys
from pathlib import Path

import pytest


TESTS_DIR = Path(__file__).resolve().parent
DB_ROOT = TESTS_DIR.parent
SERVER_ROOT = DB_ROOT.parent
MAIN_SERVICE_ROOT = SERVER_ROOT / "main_service"
SRC_DIR = MAIN_SERVICE_ROOT / "src"
APP_ROOT = SRC_DIR / "main_service"

for path in (str(SERVER_ROOT), str(SRC_DIR), str(APP_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture
def database_env(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("sqlalchemy")
    monkeypatch.setenv(
        "DATABASE_URL",
        os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://test:test@localhost:5432/test_db",
        ),
    )


def test_shared_database_and_models_modules_are_importable(database_env: None) -> None:
    shared_db = importlib.import_module("smart_cast_db.database")
    shared_models = importlib.import_module("smart_cast_db.models")

    assert shared_db.DATABASE_URL
    assert shared_db.Base
    assert shared_db.SessionLocal
    assert shared_db.engine
    assert shared_db.get_db

    for symbol in (
        "Item",
        "Ord",
        "OrdStat",
        "EquipTaskTxn",
        "TransTaskTxn",
        "RfidScanLog",
    ):
        assert hasattr(shared_models, symbol), symbol


@pytest.mark.parametrize(
    "module_name",
    [
        "app.main",
        "app.routes.orders",
        "app.routes.production.lifecycle",
        "app.routes.websocket",
    ],
)
def test_web_modules_using_app_database_remain_importable(
    database_env: None,
    module_name: str,
) -> None:
    module = importlib.import_module(module_name)
    assert module is not None


@pytest.mark.parametrize(
    "module_name",
    [
        "management.services.task_manager",
        "management.services.rfid_service",
        "management.services.handoff_pipeline",
        "management.services.fms_sequencer",
    ],
)
def test_management_modules_using_app_database_remain_importable(
    database_env: None,
    module_name: str,
) -> None:
    module = importlib.import_module(module_name)
    assert module is not None
