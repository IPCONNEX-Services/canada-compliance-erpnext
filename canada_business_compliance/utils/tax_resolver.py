import frappe
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
    Item-level zero_rated_gst wins over Item Group. If neither is set, returns False.
    """
    item = frappe.get_cached_doc("Item", item_code)
    item_value = item.get("zero_rated_gst")
    if item_value is not None:
        return bool(item_value)
    if item.item_group:
        group = frappe.get_cached_doc("Item Group", item.item_group)
        return bool(group.get("zero_rated_gst"))
    return False
