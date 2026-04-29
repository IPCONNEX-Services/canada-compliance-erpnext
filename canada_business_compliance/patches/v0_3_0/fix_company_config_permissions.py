import frappe


def execute():
    if not frappe.db.exists("DocType", "CA Company Tax Config"):
        return

    # Force-reload the DocType from JSON so permissions in tabDocPerm are
    # synced. bench migrate skips re-importing when the timestamp is
    # unchanged, so the create/write permissions never get written on
    # existing installs.
    frappe.reload_doc("ca_sales_tax", "doctype", "ca_company_tax_config", force=True)
    frappe.db.commit()
