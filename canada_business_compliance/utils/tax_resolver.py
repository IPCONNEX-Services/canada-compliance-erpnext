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
    "NS": "CA HST 14%",  # NS HST cut 15% -> 14% effective 2025-04-01
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
    "NS": "CA HST 14%",  # NS HST cut 15% -> 14% effective 2025-04-01
    "PE": "CA HST 15%",
    "BC": "CA GST Only",
    "MB": "CA GST Only",
    "SK": "CA GST Only",
    "QC": "CA GST + QST",
}

# Length of the ca_tax_basis Data field (see utils/custom_fields.py).
CA_TAX_BASIS_MAX = 140


def _get_supplier_name(doc):
    return doc.get("supplier") or doc.get("party_name")


def _supplier_territory(supplier):
    """Supplier.territory, or None — standard ERPNext Supplier has no territory field."""
    if not supplier:
        return None
    if not frappe.get_meta("Supplier").has_field("territory"):
        return None
    return frappe.db.get_value("Supplier", supplier, "territory")


def _party_address(link_doctype, link_name, order_by):
    """Best enabled Address linked to a party (Company / Customer / Supplier), or None.

    Flags are used for ordering only, never as filters: a company whose single address
    is neither primary nor shipping (e.g. an "Office" address) must still resolve.
    """
    if not link_name:
        return None
    rows = frappe.db.sql(
        f"""
        SELECT addr.name
        FROM `tabAddress` addr
        JOIN `tabDynamic Link` dl ON dl.parent = addr.name AND dl.parenttype = 'Address'
        WHERE dl.link_doctype = %s AND dl.link_name = %s AND IFNULL(addr.disabled, 0) = 0
        ORDER BY {order_by}, addr.creation ASC
        LIMIT 1
        """,
        (link_doctype, link_name),
    )
    return rows[0][0] if rows else None


def _address_location(address_name):
    """Return (province_code or None, is_foreign) for an Address.

    is_foreign is True only when the address has a country set that is not Canada;
    a blank country is treated as domestic (most local addresses leave it empty).
    """
    if not address_name:
        return None, False
    vals = frappe.db.get_value("Address", address_name, ["state", "country"], as_dict=True) or {}
    country = (vals.get("country") or "").strip()
    if country and country.lower() != "canada":
        return None, True
    return normalize_province(vals.get("state") or ""), False


def get_supplier_province_code(doc):
    """Legacy supplier-province chain: supplier_address → shipping_address → billing_address → territory.

    Kept for backward compatibility. auto_set_purchase_taxes no longer uses it; see
    get_purchase_tax_province (place of supply = delivery destination).
    """
    for field in ("supplier_address", "shipping_address", "billing_address"):
        code = _address_province(doc.get(field))
        if code:
            return code

    code = normalize_province(doc.get("territory") or _supplier_territory(_get_supplier_name(doc)))
    if code:
        return code

    return None


def get_supplier_origin_province(doc):
    """The supplier's own province: supplier_address → supplier's primary address → Supplier.territory.

    Uses supplier data only (never the company's shipping/billing address on the doc), so a
    foreign supplier resolves to None.
    """
    code = _address_province(doc.get("supplier_address"))
    if code:
        return code

    supplier = _get_supplier_name(doc)
    code = _address_province(
        _party_address("Supplier", supplier, "addr.is_primary_address DESC, addr.is_shipping_address DESC")
    )
    if code:
        return code

    return normalize_province(_supplier_territory(supplier))


def _drop_ship_sales_orders(doc):
    orders = []
    for item in doc.get("items") or []:
        so = item.get("sales_order")
        if so and item.get("delivered_by_supplier") and so not in orders:
            orders.append(so)
    return orders


def get_purchase_destination(doc):
    """Place of supply for a purchase of tangible goods = where the goods are delivered.

    Returns (province_code or None, basis) where basis is a short audit string:
      (a) drop-ship (PO.customer set, or items delivered_by_supplier against a Sales Order):
          doc.shipping_address → linked Sales Order shipping/billing address → customer's address
      (b) doc.shipping_address (company delivery address)
      (c) company billing address on the doc → company's default address (shipping, then primary)
      (d) fallback: the supplier's own province (pre-0.3.2 behaviour) — only used when no
          destination is known at all.
    A destination outside Canada returns (None, basis) so no Canadian template is applied.
    """
    so_list = _drop_ship_sales_orders(doc)
    customer = doc.get("customer")
    if customer or so_list:
        candidates = [doc.get("shipping_address")]
        for so in so_list:
            vals = frappe.db.get_value(
                "Sales Order", so, ["shipping_address_name", "customer_address"], as_dict=True
            ) or {}
            candidates += [vals.get("shipping_address_name"), vals.get("customer_address")]
        if customer:
            candidates.append(
                _party_address("Customer", customer, "addr.is_shipping_address DESC, addr.is_primary_address DESC")
            )
        for addr in candidates:
            code, foreign = _address_location(addr)
            if foreign:
                return None, f"Destination outside Canada (drop-ship to {addr})"
            if code:
                return code, f"Destination {code} (drop-ship to {addr})"

    addr = doc.get("shipping_address")
    code, foreign = _address_location(addr)
    if foreign:
        return None, f"Destination outside Canada (ship to {addr})"
    if code:
        return code, f"Destination {code} (ship to {addr})"

    company_addresses = [
        doc.get("billing_address"),
        _party_address("Company", doc.get("company"), "addr.is_shipping_address DESC, addr.is_primary_address DESC"),
    ]
    for addr in company_addresses:
        code, _foreign = _address_location(addr)
        if code:
            return code, f"Destination {code} (company address {addr})"

    # (d) No delivery location known anywhere — fall back to the supplier's province.
    code = get_supplier_origin_province(doc)
    if code:
        return code, f"Supplier fallback {code}"
    return None, "No destination or supplier province"


def _find_template(doctype, base_name, company):
    company_abbr = frappe.db.get_value("Company", company, "abbr")
    for candidate in [f"{base_name} - {company_abbr}", base_name]:
        if frappe.db.exists(doctype, {"name": candidate}):
            return candidate
    return None


def auto_set_purchase_taxes(doc, method=None):
    """before_insert on Purchase Order / Receipt / Invoice: set the purchase tax template
    from the place of supply (delivery destination) and record why in ca_tax_basis.

    No-op when the doc is not a draft or already carries a template or tax rows
    (chosen by the user or mapped from the source document).
    """
    if doc.get("docstatus"):
        return
    if doc.get("taxes_and_charges") or doc.get("taxes"):
        return
    if not _get_supplier_name(doc):
        return

    config = _get_company_config_doc(doc.get("company"))
    if not config:
        return
    if config.is_small_supplier:
        return

    # Only Canadian-registered suppliers charge GST/HST/QST on their invoice; a foreign
    # supplier (no Canadian province) stays untaxed as before — import GST is paid at customs.
    # The destination rule only decides WHICH Canadian template applies.
    if not get_supplier_origin_province(doc):
        return

    province, basis = get_purchase_destination(doc)
    if not province:
        return

    base_name = PROVINCE_TO_PURCHASE_TEMPLATE.get(province)
    if not base_name:
        return

    chosen = _find_template("Purchase Taxes and Charges Template", base_name, doc.get("company"))
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
    doc.ca_tax_basis = basis[:CA_TAX_BASIS_MAX]


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
