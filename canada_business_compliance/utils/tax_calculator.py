import frappe

# Province code → applicable taxes and rates (2025)
PROVINCE_TAXES = {
    "AB": {"gst": 5.0},
    "BC": {"gst": 5.0, "pst": 7.0},
    "MB": {"gst": 5.0, "pst": 7.0},
    "NB": {"hst": 15.0},
    "NL": {"hst": 15.0},
    "NS": {"hst": 15.0},
    "NT": {"gst": 5.0},
    "NU": {"gst": 5.0},
    "ON": {"hst": 13.0},
    "PE": {"hst": 15.0},
    "QC": {"gst": 5.0, "qst": 9.975},
    "SK": {"gst": 5.0, "pst": 6.0},
    "YT": {"gst": 5.0},
}

TAX_LABELS = {
    "gst": "GST (5%)",
    "hst": "HST",
    "pst": "PST",
    "qst": "QST (9.975%)",
}


def get_tax_rows(province_code: str) -> list:
    """Return tax row dicts (without account_head) for a given province code."""
    rates = PROVINCE_TAXES.get(province_code.upper(), {})
    rows = []
    for key, rate in rates.items():
        label = TAX_LABELS.get(key, key.upper())
        if key == "hst":
            label = f"HST ({rate}%)"
        elif key == "pst":
            label = f"PST ({rate}%)"
        rows.append({
            "charge_type": "On Net Total",
            "description": label,
            "tax_key": key,
            "rate": rate,
        })
    return rows


@frappe.whitelist()
def get_province_taxes(province_code):
    """
    Legacy API — kept for backward compatibility.
    Resolves by province code only (no address fallback, no exemption checks).
    Respects the small supplier toggle from CA Tax Settings.
    For full resolution, call resolve_taxes() directly.
    """
    settings = frappe.get_single("CA Tax Settings")
    if settings.is_small_supplier:
        return []

    rows = get_tax_rows(province_code)
    if not rows:
        return []

    account_map = {
        "gst": settings.gst_account or "",
        "hst": settings.hst_account or "",
        "pst": settings.pst_account or "",
        "qst": settings.qst_account or "",
    }

    result = []
    for row in rows:
        account = account_map.get(row["tax_key"], "")
        result.append({
            "charge_type": row["charge_type"],
            "description": row["description"],
            "rate": row["rate"],
            "account_head": account,
            "included_in_print_rate": 0,
        })
    return result
