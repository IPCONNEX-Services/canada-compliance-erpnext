import frappe

PROVINCE_TERRITORY = {
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

PROVINCE_TO_TEMPLATE_BASE = {
    "AB": "CA GST Only",
    "NT": "CA GST Only",
    "NU": "CA GST Only",
    "YT": "CA GST Only",
    "ON": "CA HST 13%",
    "NB": "CA HST 15%",
    "NL": "CA HST 15%",
    "NS": "CA HST 15%",
    "PE": "CA HST 15%",
    "BC": "CA GST + PST 7%",
    "MB": "CA GST + PST 7%",
    "SK": "CA GST + PST 6%",
    "QC": "CA GST + QST",
}


def _get_customer_name(doc):
    """Return customer name regardless of doctype field convention."""
    # Sales Invoice, Delivery Note, Sales Order → 'customer'
    # Quotation → 'party_name' (when quotation_to = 'Customer')
    return doc.get("customer") or doc.get("party_name")


def get_province_code(doc):
    """Return 2-letter province code: billing address state first, customer territory as fallback."""
    # 1. Billing address state
    address_name = doc.get("customer_address")
    if address_name:
        state = frappe.db.get_value("Address", address_name, "state") or ""
        code = state.strip().upper()
        if code in PROVINCE_TO_TEMPLATE_BASE:
            return code

    # 2. Territory on the doc, or customer master
    customer = _get_customer_name(doc)
    territory = doc.get("territory") or (
        frappe.db.get_value("Customer", customer, "territory") if customer else None
    )
    if territory:
        for code, name in PROVINCE_TERRITORY.items():
            if name == territory:
                return code

    return None


def auto_set_taxes(doc, method=None):
    """Set taxes_and_charges from province on before_insert. No-op if already set."""
    if doc.get("taxes_and_charges"):
        return
    if not _get_customer_name(doc):
        return

    province = get_province_code(doc)
    if not province:
        return

    base_name = PROVINCE_TO_TEMPLATE_BASE.get(province)
    if not base_name:
        return

    company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
    chosen = None
    for candidate in [f"{base_name} - {company_abbr}", base_name]:
        if frappe.db.exists("Sales Taxes and Charges Template", {"name": candidate}):
            chosen = candidate
            break

    if not chosen:
        return

    doc.taxes_and_charges = chosen
    template = frappe.get_doc("Sales Taxes and Charges Template", chosen)
    doc.set("taxes", [])
    for row in template.taxes:
        doc.append("taxes", {
            "charge_type": row.charge_type,
            "account_head": row.account_head,
            "description": row.description,
            "rate": row.rate,
            "included_in_print_rate": row.get("included_in_print_rate", 0),
        })
