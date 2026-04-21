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


def province_to_territory(province_code: str):
    """Map a province code (e.g. 'ON') to an ERPNext Territory name."""
    return PROVINCE_TERRITORY.get((province_code or "").strip().upper())


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
