import frappe
from canada_business_compliance.utils.tax_resolver import PROVINCE_TO_TEMPLATE_BASE

# Hardcoded rates used when no Sales Taxes and Charges Template exists for the province.
# account_head is left blank so the frontend can display rates without needing an account.
_FALLBACK_RATES = {
    "AB": [{"description": "GST",  "rate": 5.0,    "account_head": ""}],
    "BC": [{"description": "GST",  "rate": 5.0,    "account_head": ""}, {"description": "PST", "rate": 7.0,    "account_head": ""}],
    "MB": [{"description": "GST",  "rate": 5.0,    "account_head": ""}, {"description": "RST", "rate": 7.0,    "account_head": ""}],
    "NB": [{"description": "HST",  "rate": 15.0,   "account_head": ""}],
    "NL": [{"description": "HST",  "rate": 15.0,   "account_head": ""}],
    "NS": [{"description": "HST",  "rate": 15.0,   "account_head": ""}],
    "NT": [{"description": "GST",  "rate": 5.0,    "account_head": ""}],
    "NU": [{"description": "GST",  "rate": 5.0,    "account_head": ""}],
    "ON": [{"description": "HST",  "rate": 13.0,   "account_head": ""}],
    "PE": [{"description": "HST",  "rate": 15.0,   "account_head": ""}],
    "QC": [{"description": "GST",  "rate": 5.0,    "account_head": ""}, {"description": "QST", "rate": 9.975, "account_head": ""}],
    "SK": [{"description": "GST",  "rate": 5.0,    "account_head": ""}, {"description": "PST", "rate": 6.0,   "account_head": ""}],
    "YT": [{"description": "GST",  "rate": 5.0,    "account_head": ""}],
}


@frappe.whitelist(allow_guest=False)
def get_province_taxes(province_code: str) -> list:
    """Return tax rows for a province, suitable for Sales Order taxes child table.

    Tries the configured Sales Taxes and Charges Template first so account_heads
    are correct for the company. Falls back to hardcoded rates when no template exists.
    """
    code = (province_code or "").strip().upper()
    if code not in PROVINCE_TO_TEMPLATE_BASE:
        return []

    rows = _rows_from_template(code)
    if rows:
        return rows

    return [
        {"charge_type": "On Net Total", **row}
        for row in _FALLBACK_RATES.get(code, [])
    ]


def _rows_from_template(code: str) -> list:
    base_name = PROVINCE_TO_TEMPLATE_BASE[code]
    # Try <base> - <company_abbr> first, then bare base name
    default_company = frappe.defaults.get_global_default("company") or ""
    company_abbr = frappe.db.get_value("Company", default_company, "abbr") if default_company else ""

    candidates = [f"{base_name} - {company_abbr}", base_name] if company_abbr else [base_name]
    template_name = next(
        (c for c in candidates if frappe.db.exists("Sales Taxes and Charges Template", {"name": c})),
        None,
    )
    if not template_name:
        return []

    template = frappe.get_doc("Sales Taxes and Charges Template", template_name)
    return [
        {
            "charge_type": row.charge_type,
            "description": row.description,
            "rate": row.rate,
            "account_head": row.account_head,
        }
        for row in template.taxes
    ]
