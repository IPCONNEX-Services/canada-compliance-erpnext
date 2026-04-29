"""
Migrate the global CA Tax Settings singleton to a per-company CA Company Tax Config record.
Safe to run on existing installs — skips if the config already exists for the default company.
"""
import frappe


def execute():
    if not frappe.db.exists("DocType", "CA Company Tax Config"):
        return

    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        return

    existing = frappe.get_all("CA Company Tax Config", filters={"company": company}, limit=1)
    if existing:
        return

    if not frappe.db.exists("DocType", "CA Tax Settings"):
        _create_default(company)
        return

    try:
        old = frappe.get_single("CA Tax Settings")
    except Exception:
        _create_default(company)
        return

    config = frappe.new_doc("CA Company Tax Config")
    config.company = company
    config.enabled = 1
    config.collects_canada_sales_tax = 1
    config.is_small_supplier = old.is_small_supplier or 0
    config.gst_account = old.gst_account
    config.hst_account = old.hst_account
    config.pst_account = old.pst_account
    config.qst_account = old.qst_account
    config.gst_registration_number = old.gst_registration_number
    config.qst_registration_number = old.qst_registration_number
    config.apply_to_sales_order = old.apply_to_sales_order if old.apply_to_sales_order is not None else 1
    config.apply_to_quotation = old.apply_to_quotation if old.apply_to_quotation is not None else 1
    config.apply_to_sales_invoice = old.apply_to_sales_invoice if old.apply_to_sales_invoice is not None else 1
    config.use_tax_rules = old.use_tax_rules if old.use_tax_rules is not None else 1
    config.insert(ignore_permissions=True)
    frappe.db.commit()


def _create_default(company):
    config = frappe.new_doc("CA Company Tax Config")
    config.company = company
    config.enabled = 1
    config.collects_canada_sales_tax = 1
    config.apply_to_sales_order = 1
    config.apply_to_quotation = 1
    config.apply_to_sales_invoice = 1
    config.use_tax_rules = 1
    config.insert(ignore_permissions=True)
    frappe.db.commit()
