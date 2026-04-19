import sys
from unittest.mock import MagicMock
import pytest


def _passthrough_whitelist(*args, **kwargs):
    """Make frappe.whitelist() act as a no-op decorator."""
    def decorator(fn):
        return fn
    # Called as @frappe.whitelist() with no args — return decorator
    if len(args) == 1 and callable(args[0]):
        # Called as @frappe.whitelist (no parentheses)
        return args[0]
    return decorator


@pytest.fixture(scope="session", autouse=True)
def mock_frappe_module():
    """Mock frappe for all tests. Logic-only tests — no running bench needed."""
    mock = MagicMock()
    mock.whitelist = _passthrough_whitelist
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
    mock_frappe_module.reset_mock(return_value=True, side_effect=True)
    # Restore whitelist as a pass-through after reset
    mock_frappe_module.whitelist = _passthrough_whitelist
    yield mock_frappe_module
