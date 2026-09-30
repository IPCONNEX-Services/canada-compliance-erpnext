"""Custom fields owned by this app, created via create_custom_fields.

NB: Frappe has no `custom_fields` hook — the dict of that name in hooks.py is never
synced by bench. Fields that must exist are created here, from the after_install hook
(fresh installs mark all patches done without running them) and from a patch (existing sites).
"""
import frappe

PURCHASE_TAX_BASIS_DOCTYPES = ("Purchase Order", "Purchase Receipt", "Purchase Invoice")


def get_custom_fields():
    field = {
        "fieldname": "ca_tax_basis",
        "label": "CA Tax Basis",
        "fieldtype": "Data",
        "length": 140,
        "insert_after": "taxes_and_charges",
        "read_only": 1,
        "print_hide": 1,
        "no_copy": 0,  # carried PO -> PR/PI by the mapper together with taxes_and_charges
        "translatable": 0,
        "description": "Why the purchase tax template was chosen (place of supply = delivery destination). Set automatically.",
    }
    return {dt: [dict(field)] for dt in PURCHASE_TAX_BASIS_DOCTYPES}


def ensure_custom_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields(get_custom_fields(), update=True)
    frappe.clear_cache()
