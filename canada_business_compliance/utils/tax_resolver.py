import frappe
import json
from typing import Optional

PST_PROVINCES = {"BC", "SK", "MB"}


def province_from_address(address_name: str) -> Optional[str]:
    """Return uppercase province code from a Frappe Address record, or None."""
    if not address_name:
        return None
    state = frappe.db.get_value("Address", address_name, "state")
    if not state:
        return None
    return state.upper().strip()


def is_item_zero_rated(item_code: str) -> bool:
    """
    Return True if item is zero-rated for GST/HST.
    If item has zero_rated_gst = 1, return True immediately.
    Otherwise fall back to Item Group setting.
    """
    item = frappe.get_cached_doc("Item", item_code)
    if item.get("zero_rated_gst"):
        return True
    if item.item_group:
        group = frappe.get_cached_doc("Item Group", item.item_group)
        return bool(group.get("zero_rated_gst"))
    return False


@frappe.whitelist()
def resolve_taxes(doctype, shipping_address, customer_address, customer, items):
    """
    Resolve Canadian taxes for a sales document.

    Args:
        doctype: Sales Invoice, Sales Order, or Quotation (reserved for future per-doctype logic)
        shipping_address: Frappe Address name for shipping (tried first)
        customer_address: Frappe Address name for billing (fallback)
        customer: Customer docname
        items: list of item_code strings (callers must extract codes — not raw child row dicts)

    Resolution order: small supplier → address → province lookup → PST/QST exemption
    → zero-rated items → account injection.
    """
    from canada_business_compliance.utils.tax_calculator import get_tax_rows

    if isinstance(items, str):
        items = json.loads(items)

    settings = frappe.get_single("CA Tax Settings")
    if settings.is_small_supplier:
        return []

    province = province_from_address(shipping_address) or province_from_address(customer_address)
    if not province:
        return []

    tax_rows = get_tax_rows(province)
    if not tax_rows:
        return []

    if customer:
        cust = frappe.get_cached_doc("Customer", customer)
        if cust.get("pst_exempt") and province in PST_PROVINCES:
            tax_rows = [r for r in tax_rows if r["tax_key"] != "pst"]
        if cust.get("qst_exempt") and province == "QC":
            tax_rows = [r for r in tax_rows if r["tax_key"] != "qst"]

    if items:
        item_codes = [ic for ic in items if ic]
        if item_codes and all(is_item_zero_rated(ic) for ic in item_codes):
            tax_rows = [r for r in tax_rows if r["tax_key"] not in ("gst", "hst")]

    if not tax_rows:
        return []

    account_map = {
        "gst": settings.gst_account or "",
        "hst": settings.hst_account or "",
        "pst": settings.pst_account or "",
        "qst": settings.qst_account or "",
    }

    return [
        {
            "charge_type": row["charge_type"],
            "description": row["description"],
            "rate": row["rate"],
            "account_head": account_map.get(row["tax_key"], ""),
            "included_in_print_rate": 0,
        }
        for row in tax_rows
    ]
