import frappe

from canada_business_compliance.utils.province import (
    PROVINCE_NAME as PROVINCE_TERRITORY,
    normalize_province,
)

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


@frappe.whitelist()
def get_company_tax_config(company):
    """Return the CA Company Tax Config for a company, or None if not applicable."""
    if not company:
        return None
    names = frappe.get_all("CA Company Tax Config", filters={"company": company}, pluck="name", limit=1)
    if not names:
        return None
    config = frappe.get_doc("CA Company Tax Config", names[0])
    if not config.enabled or not config.collects_canada_sales_tax:
        return None
    return config.as_dict()


def _get_company_config_doc(company):
    """Internal: return config Document or None."""
    if not company:
        return None
    names = frappe.get_all("CA Company Tax Config", filters={"company": company}, pluck="name", limit=1)
    if not names:
        return None
    config = frappe.get_doc("CA Company Tax Config", names[0])
    if not config.enabled or not config.collects_canada_sales_tax:
        return None
    return config


def _get_customer_name(doc):
    return doc.get("customer") or doc.get("party_name")


def _address_province(address_name):
    """Read an Address.state field and normalise to a 2-letter code, or None."""
    if not address_name:
        return None
    state = frappe.db.get_value("Address", address_name, "state") or ""
    return normalize_province(state)


def get_province_code(doc):
    """Return 2-letter province code, trying shipping → billing → customer territory.

    Accepts any state format (code, full English/French name, abbreviation) thanks
    to normalize_province. Shipping wins over billing because Canadian place-of-supply
    rules use the delivery location.
    """
    for field in ("shipping_address_name", "customer_address"):
        code = _address_province(doc.get(field))
        if code:
            return code

    customer = _get_customer_name(doc)
    territory = doc.get("territory") or (
        frappe.db.get_value("Customer", customer, "territory") if customer else None
    )
    code = normalize_province(territory)
    if code:
        return code

    return None


# PST non-recoverable — BC/MB/SK purchases only get GST ITC
PROVINCE_TO_PURCHASE_TEMPLATE = {
    "AB": "CA GST Only",
    "NT": "CA GST Only",
    "NU": "CA GST Only",
    "YT": "CA GST Only",
    "ON": "CA HST 13%",
    "NB": "CA HST 15%",
    "NL": "CA HST 15%",
    "NS": "CA HST 15%",
    "PE": "CA HST 15%",
    "BC": "CA GST Only",
    "MB": "CA GST Only",
    "SK": "CA GST Only",
    "QC": "CA GST + QST",
}


def _get_supplier_name(doc):
    return doc.get("supplier") or doc.get("party_name")


def get_supplier_province_code(doc):
    """Return 2-letter province code, trying supplier_address → shipping_address → supplier territory."""
    for field in ("supplier_address", "shipping_address", "billing_address"):
        code = _address_province(doc.get(field))
        if code:
            return code

    supplier = _get_supplier_name(doc)
    territory = doc.get("territory") or (
        frappe.db.get_value("Supplier", supplier, "territory") if supplier else None
    )
    code = normalize_province(territory)
    if code:
        return code

    return None


def auto_set_purchase_taxes(doc, method=None):
    """Set taxes_and_charges from supplier province on before_insert. No-op if already set."""
    if doc.get("taxes_and_charges"):
        return
    if not _get_supplier_name(doc):
        return

    config = _get_company_config_doc(doc.company)
    if not config:
        return
    if config.is_small_supplier:
        return

    province = get_supplier_province_code(doc)
    if not province:
        return

    base_name = PROVINCE_TO_PURCHASE_TEMPLATE.get(province)
    if not base_name:
        return

    company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
    chosen = None
    for candidate in [f"{base_name} - {company_abbr}", base_name]:
        if frappe.db.exists("Purchase Taxes and Charges Template", {"name": candidate}):
            chosen = candidate
            break

    if not chosen:
        return

    doc.taxes_and_charges = chosen
    template = frappe.get_doc("Purchase Taxes and Charges Template", chosen)
    doc.set("taxes", [])
    for row in template.taxes:
        doc.append("taxes", {
            "charge_type": row.charge_type,
            "account_head": row.account_head,
            "description": row.description,
            "rate": row.rate,
            "included_in_print_rate": row.get("included_in_print_rate", 0),
        })


def auto_set_taxes(doc, method=None):
    """Set taxes_and_charges from province on before_insert. No-op if already set."""
    if doc.get("taxes_and_charges"):
        return
    if not _get_customer_name(doc):
        return

    config = _get_company_config_doc(doc.company)
    if not config:
        return
    if config.is_small_supplier:
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
