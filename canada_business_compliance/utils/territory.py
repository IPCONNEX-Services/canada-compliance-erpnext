import frappe

from canada_business_compliance.utils.province import (
    PROVINCE_NAME as PROVINCE_TERRITORY,
    normalize_province,
    code_to_name,
)


def province_to_territory(province_code):
    """Map any province input (code, full name, French, abbreviation) to ERPNext Territory name."""
    return code_to_name(normalize_province(province_code))


def set_customer_territory(doc, method=None):
    links = frappe.get_all(
        "Dynamic Link",
        filters={"link_doctype": "Customer", "link_name": doc.name, "parenttype": "Address"},
        pluck="parent",
    )
    if not links:
        return
    address_name = (
        frappe.db.get_value("Address", {"name": ["in", links], "is_primary_address": 1}, "name")
        or links[0]
    )
    state = frappe.db.get_value("Address", address_name, "state") or ""
    territory = province_to_territory(state)
    if territory and doc.territory != territory:
        doc.db_set("territory", territory, update_modified=False)
