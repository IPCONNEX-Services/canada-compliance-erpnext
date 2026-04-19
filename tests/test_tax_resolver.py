import pytest
from unittest.mock import MagicMock, call


class TestProvinceFromAddress:
    def test_returns_uppercased_province(self, frappe):
        frappe.db.get_value.return_value = "on"
        from canada_business_compliance.utils.tax_resolver import province_from_address
        assert province_from_address("ADDR-001") == "ON"
        frappe.db.get_value.assert_called_once_with("Address", "ADDR-001", "state")

    def test_returns_none_for_empty_string(self, frappe):
        from canada_business_compliance.utils.tax_resolver import province_from_address
        assert province_from_address("") is None
        frappe.db.get_value.assert_not_called()

    def test_returns_none_for_none(self, frappe):
        from canada_business_compliance.utils.tax_resolver import province_from_address
        assert province_from_address(None) is None

    def test_returns_none_when_address_has_no_state(self, frappe):
        frappe.db.get_value.return_value = None
        from canada_business_compliance.utils.tax_resolver import province_from_address
        assert province_from_address("ADDR-001") is None

    def test_strips_whitespace(self, frappe):
        frappe.db.get_value.return_value = " BC "
        from canada_business_compliance.utils.tax_resolver import province_from_address
        assert province_from_address("ADDR-001") == "BC"


class TestIsItemZeroRated:
    def test_returns_true_when_item_level_set(self, frappe):
        item = MagicMock()
        item.get.return_value = 1
        frappe.get_cached_doc.return_value = item
        from canada_business_compliance.utils.tax_resolver import is_item_zero_rated
        assert is_item_zero_rated("ITEM-001") is True

    def test_returns_false_when_item_level_unset(self, frappe):
        item = MagicMock()
        item.get.return_value = 0
        frappe.get_cached_doc.return_value = item
        from canada_business_compliance.utils.tax_resolver import is_item_zero_rated
        assert is_item_zero_rated("ITEM-001") is False

    def test_falls_back_to_item_group(self, frappe):
        item = MagicMock()
        item.get.return_value = None  # not set at item level
        item.item_group = "Groceries"
        group = MagicMock()
        group.get.return_value = 1
        frappe.get_cached_doc.side_effect = [item, group]
        from canada_business_compliance.utils.tax_resolver import is_item_zero_rated
        assert is_item_zero_rated("ITEM-001") is True
        assert frappe.get_cached_doc.call_args_list == [
            call("Item", "ITEM-001"),
            call("Item Group", "Groceries"),
        ]

    def test_returns_false_when_neither_set(self, frappe):
        item = MagicMock()
        item.get.return_value = None
        item.item_group = "Services"
        group = MagicMock()
        group.get.return_value = 0
        frappe.get_cached_doc.side_effect = [item, group]
        from canada_business_compliance.utils.tax_resolver import is_item_zero_rated
        assert is_item_zero_rated("ITEM-001") is False
