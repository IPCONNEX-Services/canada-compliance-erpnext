import frappe
from frappe.model.document import Document


class CATaxSettings(Document):
    def validate(self):
        frappe.throw(
            "CA Tax Settings is deprecated — use <b>CA Company Tax Config</b> instead "
            "(Setup &rarr; CA Company Tax Config &rarr; New, one record per company).",
            title="Deprecated",
        )
