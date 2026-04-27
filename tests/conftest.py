from pathlib import Path

import pytest

from db import bootstrap_database


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.sqlite"
    bootstrap_database(path)
    return path
