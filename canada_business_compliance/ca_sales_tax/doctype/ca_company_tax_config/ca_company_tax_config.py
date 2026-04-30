import frappe
from frappe.model.document import Document


class CACompanyTaxConfig(Document):
    def validate(self):
        if self.is_new():
            if frappe.db.exists("CA Company Tax Config", self.company):
                frappe.throw(
                    f"A CA Company Tax Config already exists for {self.company}. "
                    "Find it in the CA Company Tax Config list.",
                    title="Already Configured",
                )
            # Only check country on first save to avoid noise on every edit
            country = frappe.db.get_value("Company", self.company, "country")
            if country and country != "Canada":
                frappe.msgprint(
                    f"Company '{self.company}' is registered under <b>{country}</b>, not Canada. "
                    "CA Company Tax Config is designed for Canadian companies.",
                    title="Non-Canadian Company",
                    indicator="orange",
                )

    def on_update(self):
        if not self.has_value_changed("use_tax_rules"):
            return
        disabled = 0 if self.use_tax_rules else 1
        rules = frappe.get_all(
            "Tax Rule",
            filters={
                "tax_type": "Sales",
                "company": self.company,
                "billing_country": "Canada",
            },
            pluck="name",
        )
        for name in rules:
            frappe.db.set_value("Tax Rule", name, "disabled", disabled)
