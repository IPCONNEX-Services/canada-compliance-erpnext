import sys
from unittest.mock import MagicMock
import pytest


@pytest.fixture(scope="session", autouse=True)
def mock_frappe_module():
    """Mock frappe for all tests. Logic-only tests — no running bench needed."""
    mock = MagicMock()
    sys.modules["frappe"] = mock
    sys.modules["frappe.model"] = MagicMock()
    sys.modules["frappe.model.document"] = MagicMock()
    yield mock
    del sys.modules["frappe"]
    del sys.modules["frappe.model"]
    del sys.modules["frappe.model.document"]


@pytest.fixture
def frappe(mock_frappe_module):
    """Per-test frappe mock, reset between tests."""
    mock_frappe_module.reset_mock()
    yield mock_frappe_module
