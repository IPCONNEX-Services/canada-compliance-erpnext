import pytest


# ── province_to_territory ─────────────────────────────────────────────────────

def test_all_13_province_codes(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    expected = {
        "AB": "Alberta",
        "BC": "British Columbia",
        "MB": "Manitoba",
        "NB": "New Brunswick",
        "NL": "Newfoundland and Labrador",
        "NS": "Nova Scotia",
        "NT": "Northwest Territories",
        "NU": "Nunavut",
        "ON": "Ontario",
        "PE": "Prince Edward Island",
        "QC": "Quebec",
        "SK": "Saskatchewan",
        "YT": "Yukon",
    }
    for code, name in expected.items():
        assert province_to_territory(code) == name, f"Failed for {code}"


def test_unknown_code_returns_none(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory("XX") is None


def test_empty_string_returns_none(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory("") is None


def test_none_returns_none(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory(None) is None


def test_lowercase_input_normalised(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory("on") == "Ontario"
    assert province_to_territory("qc") == "Quebec"


def test_whitespace_stripped(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory("  ON  ") == "Ontario"


# ── set_customer_territory ────────────────────────────────────────────────────

def test_set_customer_territory_sets_territory_from_primary_address(frappe):
    from canada_business_compliance.utils.territory import set_customer_territory
    from unittest.mock import MagicMock

    frappe.get_all.return_value = ["Addr-001"]  # pluck="parent" returns list of strings

    def get_value_side_effect(doctype, filters_or_name, field):
        if doctype == "Address" and isinstance(filters_or_name, dict) and field == "name":
            return "Addr-001"
        if doctype == "Address" and filters_or_name == "Addr-001" and field == "state":
            return "ON"
        return None

    frappe.db.get_value.side_effect = get_value_side_effect

    doc = MagicMock()
    doc.name = "CUST-001"
    doc.territory = ""

    set_customer_territory(doc)

    doc.db_set.assert_called_once_with("territory", "Ontario", update_modified=False)


def test_set_customer_territory_skips_when_already_correct(frappe):
    from canada_business_compliance.utils.territory import set_customer_territory
    from unittest.mock import MagicMock

    frappe.get_all.return_value = ["Addr-001"]

    def get_value_side_effect(doctype, filters_or_name, field):
        if doctype == "Address" and isinstance(filters_or_name, dict) and field == "name":
            return "Addr-001"
        if doctype == "Address" and filters_or_name == "Addr-001" and field == "state":
            return "ON"
        return None

    frappe.db.get_value.side_effect = get_value_side_effect

    doc = MagicMock()
    doc.name = "CUST-001"
    doc.territory = "Ontario"  # already set correctly

    set_customer_territory(doc)

    doc.db_set.assert_not_called()


def test_set_customer_territory_no_address(frappe):
    from canada_business_compliance.utils.territory import set_customer_territory
    from unittest.mock import MagicMock

    frappe.get_all.return_value = []  # no addresses linked

    doc = MagicMock()
    doc.name = "CUST-002"

    set_customer_territory(doc)

    doc.db_set.assert_not_called()


def test_set_customer_territory_unknown_province(frappe):
    from canada_business_compliance.utils.territory import set_customer_territory
    from unittest.mock import MagicMock

    frappe.get_all.return_value = ["Addr-001"]

    def get_value_side_effect(doctype, filters_or_name, field):
        if doctype == "Address" and isinstance(filters_or_name, dict) and field == "name":
            return "Addr-001"
        if doctype == "Address" and filters_or_name == "Addr-001" and field == "state":
            return "ZZ"  # unmapped province
        return None

    frappe.db.get_value.side_effect = get_value_side_effect

    doc = MagicMock()
    doc.name = "CUST-003"
    doc.territory = "All Territories"

    set_customer_territory(doc)

    doc.db_set.assert_not_called()
