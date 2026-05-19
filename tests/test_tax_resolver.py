"""Province resolution from sales/purchase docs — shipping → billing → territory fallback chain."""
from unittest.mock import MagicMock


def _addr_state(addr_states):
    """Build a frappe.db.get_value side_effect that returns Address.state from a dict."""
    def side_effect(doctype, name, field):
        if doctype == "Address" and field == "state":
            return addr_states.get(name)
        if doctype == "Customer" and field == "territory":
            return addr_states.get("__customer_territory__")
        if doctype == "Supplier" and field == "territory":
            return addr_states.get("__supplier_territory__")
        return None
    return side_effect


# ── Sales: get_province_code ──────────────────────────────────────────────────

def test_sales_billing_address_full_name(frappe):
    """User wrote 'Ontario' in billing address state — must still resolve to ON."""
    from canada_business_compliance.utils.tax_resolver import get_province_code
    frappe.db.get_value.side_effect = _addr_state({"BILL-001": "Ontario"})
    doc = {"customer": "C-1", "customer_address": "BILL-001"}
    assert get_province_code(doc) == "ON"


def test_sales_billing_quebec_with_accent(frappe):
    from canada_business_compliance.utils.tax_resolver import get_province_code
    frappe.db.get_value.side_effect = _addr_state({"BILL-001": "Québec"})
    doc = {"customer": "C-1", "customer_address": "BILL-001"}
    assert get_province_code(doc) == "QC"


def test_sales_billing_quebec_without_accent(frappe):
    from canada_business_compliance.utils.tax_resolver import get_province_code
    frappe.db.get_value.side_effect = _addr_state({"BILL-001": "Quebec"})
    doc = {"customer": "C-1", "customer_address": "BILL-001"}
    assert get_province_code(doc) == "QC"


def test_sales_shipping_wins_over_billing(frappe):
    """Place-of-supply rules — shipping (delivery) address wins."""
    from canada_business_compliance.utils.tax_resolver import get_province_code
    frappe.db.get_value.side_effect = _addr_state({
        "BILL-001": "ON",
        "SHIP-001": "BC",
    })
    doc = {
        "customer": "C-1",
        "customer_address": "BILL-001",
        "shipping_address_name": "SHIP-001",
    }
    assert get_province_code(doc) == "BC"


def test_sales_falls_back_to_billing_when_shipping_blank(frappe):
    from canada_business_compliance.utils.tax_resolver import get_province_code
    frappe.db.get_value.side_effect = _addr_state({
        "BILL-001": "AB",
        "SHIP-001": "",  # blank state on shipping
    })
    doc = {
        "customer": "C-1",
        "customer_address": "BILL-001",
        "shipping_address_name": "SHIP-001",
    }
    assert get_province_code(doc) == "AB"


def test_sales_falls_back_to_customer_territory(frappe):
    """No address state at all — use customer.territory."""
    from canada_business_compliance.utils.tax_resolver import get_province_code
    frappe.db.get_value.side_effect = _addr_state({
        "BILL-001": "",
        "__customer_territory__": "Ontario",
    })
    doc = {"customer": "C-1", "customer_address": "BILL-001"}
    assert get_province_code(doc) == "ON"


def test_sales_returns_none_when_nothing_resolves(frappe):
    from canada_business_compliance.utils.tax_resolver import get_province_code
    frappe.db.get_value.side_effect = _addr_state({})
    doc = {"customer": "C-1"}
    assert get_province_code(doc) is None


# ── Purchase: get_supplier_province_code ──────────────────────────────────────

def test_purchase_supplier_address_full_name(frappe):
    from canada_business_compliance.utils.tax_resolver import get_supplier_province_code
    frappe.db.get_value.side_effect = _addr_state({"SUPP-001": "Saskatchewan"})
    doc = {"supplier": "S-1", "supplier_address": "SUPP-001"}
    assert get_supplier_province_code(doc) == "SK"


def test_purchase_falls_back_to_shipping(frappe):
    """Supplier address has no state — shipping (where goods received) is the fallback."""
    from canada_business_compliance.utils.tax_resolver import get_supplier_province_code
    frappe.db.get_value.side_effect = _addr_state({
        "SUPP-001": "",
        "SHIP-001": "ON",
    })
    doc = {
        "supplier": "S-1",
        "supplier_address": "SUPP-001",
        "shipping_address": "SHIP-001",
    }
    assert get_supplier_province_code(doc) == "ON"


def test_purchase_falls_back_to_supplier_territory(frappe):
    from canada_business_compliance.utils.tax_resolver import get_supplier_province_code
    frappe.db.get_value.side_effect = _addr_state({
        "__supplier_territory__": "Québec",
    })
    doc = {"supplier": "S-1"}
    assert get_supplier_province_code(doc) == "QC"
