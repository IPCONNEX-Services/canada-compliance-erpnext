"""
Remove the deprecated CA Tax Settings single DocType (replaced by CA Company Tax Config).

Runs post_model_sync, after v0_3_0.migrate_settings_to_company_config has copied the old
values. Idempotent: safe when the DocType or its rows are already gone.
"""
import json
import os

import frappe

DOCTYPE = "CA Tax Settings"
PRINT_FORMAT = "CA Tax Invoice"

# (table doctype, column) pairs that can point at the removed DocType.
_REFERENCES = (
    ("Singles", "doctype"),
    ("Custom Field", "dt"),
    ("Property Setter", "doc_type"),
    ("Custom DocPerm", "parent"),
    ("Workspace Link", "link_to"),
    ("Workspace Shortcut", "link_to"),
    ("Workspace Quick List", "document_type"),
)


def execute():
    _refresh_print_format()

    if frappe.db.exists("DocType", DOCTYPE):
        frappe.delete_doc(
            "DocType",
            DOCTYPE,
            force=1,
            ignore_missing=True,
            ignore_permissions=True,
        )

    for table, column in _REFERENCES:
        if not frappe.db.table_exists(table):
            continue
        frappe.db.delete(table, {column: DOCTYPE})

    frappe.db.commit()
    frappe.clear_cache()


def _refresh_print_format():
    """Sites installed before 0.3.0 still hold the old CA Tax Invoice HTML, which calls
    frappe.get_single('CA Tax Settings'). The fixed JSON kept its old `modified`, so sync
    never re-imported it. Copy the shipped HTML (reads CA Company Tax Config) and leave
    every other field (e.g. disabled) as the site has it."""
    if not frappe.db.exists("Print Format", PRINT_FORMAT):
        return
    html = frappe.db.get_value("Print Format", PRINT_FORMAT, "html") or ""
    if DOCTYPE not in html:
        return
    path = os.path.join(
        frappe.get_app_path("canada_business_compliance"),
        "ca_sales_tax", "print_format", "ca_tax_invoice", "ca_tax_invoice.json",
    )
    with open(path, encoding="utf-8") as f:
        shipped = json.load(f).get("html") or ""
    if not shipped or DOCTYPE in shipped:
        return
    frappe.db.set_value("Print Format", PRINT_FORMAT, "html", shipped)
