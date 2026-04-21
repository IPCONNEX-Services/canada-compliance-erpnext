import frappe
from frappe.model.document import Document


class CATaxSettings(Document):
    def on_update(self):
        disabled = 0 if self.use_tax_rules else 1
        rules = frappe.get_all(
            "Tax Rule",
            filters={"tax_type": "Sales", "name": ["like", "CA %"]},
        )
        for rule in rules:
            frappe.db.set_value("Tax Rule", rule.name, "disabled", disabled)
