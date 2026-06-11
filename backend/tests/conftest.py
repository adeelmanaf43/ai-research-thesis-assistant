import shutil
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_TMP_ROOT = PROJECT_ROOT / "data" / "test_tmp"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def workspace_tmp_path() -> Path:
    test_path = TEST_TMP_ROOT / uuid.uuid4().hex
    test_path.mkdir(parents=True, exist_ok=False)
    try:
        yield test_path
    finally:
        shutil.rmtree(test_path, ignore_errors=True)
