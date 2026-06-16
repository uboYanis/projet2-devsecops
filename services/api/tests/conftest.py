import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main  # import du module seul (pas de startup ici)

_cursor = MagicMock()
_cursor.__enter__ = lambda s: _cursor
_cursor.__exit__ = MagicMock(return_value=False)
_cursor.fetchone.return_value = None
_cursor.fetchall.return_value = []

_conn = MagicMock()
_conn.__enter__ = lambda s: _conn
_conn.__exit__ = MagicMock(return_value=False)
_conn.cursor.return_value = _cursor

# Patch main.get_db avant la création du TestClient (qui déclenche startup/init_db)
_patch = patch("main.get_db", return_value=_conn)
_patch.start()

from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_cursor():
    _cursor.reset_mock()
    _cursor.fetchone.return_value = None
    _cursor.fetchall.return_value = []
    _cursor.__enter__ = lambda s: _cursor
    _cursor.__exit__ = MagicMock(return_value=False)
    _conn.cursor.return_value = _cursor
    yield _cursor