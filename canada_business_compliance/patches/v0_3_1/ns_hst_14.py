"""Nova Scotia HST dropped from 15% to 14% effective 2025-04-01.

For every company that has a `CA HST 15%` template, create a matching `CA HST 14%`
template (same account head / structure, rate 14) and repoint Nova Scotia Tax Rules
from the 15% template to the 14% one. NB, NL and PE stay at 15%.

Idempotent: existing 14% templates are left alone and only rules still pointing at
the 15% template are changed. Transactions (draft or submitted) are never modified.
"""
import frappe

NS_STATES = {"NS", "NOVA SCOTIA", "NOUVELLE-ÉCOSSE", "NOUVELLE-ECOSSE"}
OLD_BASE = "CA HST 15%"
NEW_BASE = "CA HST 14%"


def _is_ns(state):
    return (state or "").strip().upper() in NS_STATES


def _find(doctype, abbr):
    # Purchase templates created by older setup_taxes runs carry a doubled suffix.
    for name in (f"{OLD_BASE} - {abbr}", f"{OLD_BASE} - {abbr} - {abbr}"):
        if frappe.db.exists(doctype, name):
            return name
    return None


def _ensure_14(doctype, company, abbr):
    """Return the 14% template name for company, creating it from the 15% one if needed."""
    target = f"{NEW_BASE} - {abbr}"
    if frappe.db.exists(doctype, target):
        return target
    source = _find(doctype, abbr)
    if not source:
        return None
    src = frappe.get_doc(doctype, source)
    if src.company != company:
        return None
    new = frappe.copy_doc(src)
    new.title = NEW_BASE
    new.is_default = 0
    for row in new.taxes:
        if row.rate == 15:
            row.rate = 14
        row.description = (row.description or "").replace("15.0", "14.0").replace("15%", "14%")
    new.insert(ignore_permissions=True)
    if new.name != target:
        frappe.rename_doc(doctype, new.name, target, force=True)
    return target


def execute():
    for company, abbr in frappe.get_all("Company", fields=["name", "abbr"], as_list=True):
        for tax_type, doctype, field in (
            ("Sales", "Sales Taxes and Charges Template", "sales_tax_template"),
            ("Purchase", "Purchase Taxes and Charges Template", "purchase_tax_template"),
        ):
            old_names = {f"{OLD_BASE} - {abbr}", f"{OLD_BASE} - {abbr} - {abbr}"}
            rules = [
                r for r in frappe.get_all(
                    "Tax Rule",
                    filters={"company": company, "tax_type": tax_type, field: ["in", list(old_names)]},
                    fields=["name", "billing_state", "shipping_state"],
                )
                if _is_ns(r.billing_state) or _is_ns(r.shipping_state)
            ]
            new_name = _ensure_14(doctype, company, abbr)
            if not new_name:
                continue
            for r in rules:
                frappe.db.set_value("Tax Rule", r.name, field, new_name)
