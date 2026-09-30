"""
Migrate the global CA Tax Settings singleton to a per-company CA Company Tax Config record.

Runs post_model_sync (the CA Company Tax Config table must exist) and reads the old
values straight from tabSingles, so it works after the CA Tax Settings DocType has been
removed (v0.3.3). Skips if a config already exists for the default company.
"""
import frappe

OLD_DOCTYPE = "CA Tax Settings"

_CHECK_FIELDS_DEFAULT_ON = (
    "apply_to_sales_order",
    "apply_to_quotation",
    "apply_to_sales_invoice",
    "use_tax_rules",
)
_TEXT_FIELDS = (
    "gst_account",
    "hst_account",
    "pst_account",
    "qst_account",
    "gst_registration_number",
    "qst_registration_number",
)


def execute():
    if not frappe.db.exists("DocType", "CA Company Tax Config"):
        return

    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        return

    if frappe.get_all("CA Company Tax Config", filters={"company": company}, limit=1):
        return

    old = _read_old_settings()

    config = frappe.new_doc("CA Company Tax Config")
    config.company = company
    config.enabled = 1
    config.collects_canada_sales_tax = 1
    config.is_small_supplier = frappe.utils.cint(old.get("is_small_supplier"))
    for field in _CHECK_FIELDS_DEFAULT_ON:
        value = old.get(field)
        config.set(field, 1 if value in (None, "") else frappe.utils.cint(value))
    for field in _TEXT_FIELDS:
        if old.get(field):
            config.set(field, old[field])
    config.insert(ignore_permissions=True)
    frappe.db.commit()


def _read_old_settings():
    """Raw CA Tax Settings values ({} when never saved or already removed)."""
    rows = frappe.db.sql(
        "SELECT field, value FROM `tabSingles` WHERE doctype = %s",
        OLD_DOCTYPE,
    )
    return {field: value for field, value in rows or ()}
