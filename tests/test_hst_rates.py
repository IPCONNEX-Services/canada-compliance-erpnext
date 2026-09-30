"""HST province mapping — NS is 14% since 2025-04-01; NB/NL/PE stay 15%, ON 13%."""
from types import SimpleNamespace

import pytest


def test_ns_maps_to_hst_14():
    from canada_business_compliance.utils.tax_resolver import (
        PROVINCE_TO_PURCHASE_TEMPLATE,
        PROVINCE_TO_TEMPLATE_BASE,
    )
    assert PROVINCE_TO_TEMPLATE_BASE["NS"] == "CA HST 14%"
    assert PROVINCE_TO_PURCHASE_TEMPLATE["NS"] == "CA HST 14%"


@pytest.mark.parametrize("code", ["NB", "NL", "PE"])
def test_other_atlantic_provinces_stay_hst_15(code):
    from canada_business_compliance.utils.tax_resolver import (
        PROVINCE_TO_PURCHASE_TEMPLATE,
        PROVINCE_TO_TEMPLATE_BASE,
    )
    assert PROVINCE_TO_TEMPLATE_BASE[code] == "CA HST 15%"
    assert PROVINCE_TO_PURCHASE_TEMPLATE[code] == "CA HST 15%"


def test_ontario_unchanged():
    from canada_business_compliance.utils.tax_resolver import PROVINCE_TO_TEMPLATE_BASE
    assert PROVINCE_TO_TEMPLATE_BASE["ON"] == "CA HST 13%"


@pytest.mark.parametrize("code,rate", [("NS", 14.0), ("NB", 15.0), ("NL", 15.0), ("PE", 15.0), ("ON", 13.0)])
def test_fallback_rates(frappe, code, rate):
    """No template on site -> hardcoded fallback rows."""
    from canada_business_compliance.utils.tax_calculator import get_province_taxes
    frappe.defaults.get_global_default.return_value = ""
    frappe.db.exists.return_value = False
    rows = get_province_taxes(code)
    assert [(r["description"], r["rate"]) for r in rows] == [("HST", rate)]


def test_setup_taxes_defines_hst_14_templates():
    """setup_company_taxes must never create an empty CA HST 14% template."""
    from canada_business_compliance.utils.setup_taxes import (
        PROVINCE_TO_PURCHASE_TEMPLATE,
        PROVINCE_TO_TEMPLATE,
        PROVINCE_TO_TEMPLATE_ADVANCED,
        _template_rows,
        _template_rows_purchase,
    )
    cfg = SimpleNamespace(
        gst_account="GST", hst_account="HST", pst_account="PST", qst_account="QST",
        gst_itc_account="GST ITC", hst_itc_account="HST ITC", qst_itc_account="QST ITC",
    )
    assert PROVINCE_TO_TEMPLATE["NS"] == PROVINCE_TO_TEMPLATE_ADVANCED["NS"] == "CA HST 14%"
    assert PROVINCE_TO_PURCHASE_TEMPLATE["NS"] == "CA HST 14%"
    assert [(r["account_head"], r["rate"]) for r in _template_rows("CA HST 14%", cfg)] == [("HST", 14.0)]
    assert [(r["account_head"], r["rate"]) for r in _template_rows_purchase("CA HST 14%", cfg)] == [("HST ITC", 14.0)]
    for base in set(PROVINCE_TO_TEMPLATE.values()):
        assert _template_rows(base, cfg), base
