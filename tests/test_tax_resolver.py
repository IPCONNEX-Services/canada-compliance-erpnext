import pytest
from unittest.mock import MagicMock, patch, call


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
        item.get.return_value = 0   # unchecked at item level
        item.item_group = "Standard"
        group = MagicMock()
        group.get.return_value = 0  # also unchecked at group level
        frappe.get_cached_doc.side_effect = [item, group]
        from canada_business_compliance.utils.tax_resolver import is_item_zero_rated
        assert is_item_zero_rated("ITEM-001") is False

    def test_falls_back_to_group_when_item_unchecked(self, frappe):
        item = MagicMock()
        item.get.return_value = 0   # item explicitly unchecked
        item.item_group = "Groceries"
        group = MagicMock()
        group.get.return_value = 1  # group is zero-rated
        frappe.get_cached_doc.side_effect = [item, group]
        from canada_business_compliance.utils.tax_resolver import is_item_zero_rated
        assert is_item_zero_rated("ITEM-001") is True

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


class TestResolveTaxes:
    def _settings(self, frappe, small_supplier=False,
                  gst="GST Payable - CA", hst="HST Payable - CA",
                  pst="PST Payable - CA", qst="QST Payable - CA"):
        s = MagicMock()
        s.is_small_supplier = small_supplier
        s.gst_account = gst
        s.hst_account = hst
        s.pst_account = pst
        s.qst_account = qst
        frappe.get_single.return_value = s
        return s

    def _customer(self, frappe, pst_exempt=False, qst_exempt=False):
        c = MagicMock()
        c.get.side_effect = lambda k: {"pst_exempt": pst_exempt, "qst_exempt": qst_exempt}.get(k)
        frappe.get_cached_doc.return_value = c
        return c

    def test_returns_empty_for_small_supplier(self, frappe):
        self._settings(frappe, small_supplier=True)
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        assert resolve_taxes("Sales Invoice", "A", "B", "CUST-001", []) == []

    def test_uses_shipping_address_first(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.side_effect = lambda dt, name, f: "AB" if name == "SHIP" else None
        self._customer(frappe)
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "SHIP", "BILL", "CUST-001", [])
        assert len(result) == 1
        assert result[0]["rate"] == 5.0

    def test_falls_back_to_billing_when_shipping_empty(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.side_effect = lambda dt, name, f: "ON" if name == "BILL" else None
        self._customer(frappe)
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "", "BILL", "CUST-001", [])
        assert len(result) == 1
        assert result[0]["rate"] == 13.0

    def test_returns_empty_when_no_address(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.return_value = None
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        assert resolve_taxes("Sales Invoice", "", "", "CUST-001", []) == []

    def test_removes_pst_in_bc_for_exempt_customer(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.return_value = "BC"
        self._customer(frappe, pst_exempt=True)
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "ADDR", "", "CUST-001", [])
        assert len(result) == 1
        assert result[0]["rate"] == 5.0
        assert result[0]["account_head"] == "GST Payable - CA"

    def test_removes_pst_in_sk_for_exempt_customer(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.return_value = "SK"
        self._customer(frappe, pst_exempt=True)
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "ADDR", "", "CUST-001", [])
        assert len(result) == 1
        assert result[0]["rate"] == 5.0

    def test_pst_exemption_does_not_affect_hst_province(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.return_value = "ON"
        self._customer(frappe, pst_exempt=True)
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "ADDR", "", "CUST-001", [])
        assert len(result) == 1
        assert result[0]["rate"] == 13.0

    def test_removes_qst_in_qc_for_exempt_customer(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.return_value = "QC"
        self._customer(frappe, qst_exempt=True)
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "ADDR", "", "CUST-001", [])
        assert len(result) == 1
        assert result[0]["rate"] == 5.0

    def test_removes_gst_when_all_items_zero_rated(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.return_value = "AB"
        customer = MagicMock()
        customer.get.return_value = False
        item = MagicMock()
        item.get.return_value = 1
        frappe.get_cached_doc.side_effect = lambda dt, name: customer if dt == "Customer" else item
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "ADDR", "", "CUST-001", ["GROCERY-001"])
        assert result == []

    def test_keeps_gst_when_items_list_empty(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.return_value = "AB"
        self._customer(frappe)
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "ADDR", "", "CUST-001", [])
        assert len(result) == 1
        assert result[0]["rate"] == 5.0

    def test_keeps_gst_when_one_item_not_zero_rated(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.return_value = "AB"
        customer = MagicMock()
        customer.get.return_value = False

        def cached_doc(dt, name):
            if dt == "Customer":
                return customer
            item = MagicMock()
            item.get.return_value = 1 if name == "GROCERY" else 0
            return item

        frappe.get_cached_doc.side_effect = cached_doc
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "ADDR", "", "CUST-001", ["GROCERY", "SERVICE"])
        assert len(result) == 1
        assert result[0]["rate"] == 5.0

    def test_returns_empty_account_head_when_unconfigured(self, frappe):
        self._settings(frappe, gst="")
        frappe.db.get_value.return_value = "AB"
        self._customer(frappe)
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "ADDR", "", "CUST-001", [])
        assert result[0]["account_head"] == ""

    def test_injects_correct_account_head(self, frappe):
        self._settings(frappe)
        frappe.db.get_value.return_value = "AB"
        self._customer(frappe)
        from canada_business_compliance.utils.tax_resolver import resolve_taxes
        result = resolve_taxes("Sales Invoice", "ADDR", "", "CUST-001", [])
        assert result[0]["account_head"] == "GST Payable - CA"
