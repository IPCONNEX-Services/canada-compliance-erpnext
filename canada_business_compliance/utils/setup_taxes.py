import frappe

PROVINCE_TO_TEMPLATE = {
    "AB": "CA GST Only",
    "NT": "CA GST Only",
    "NU": "CA GST Only",
    "YT": "CA GST Only",
    "ON": "CA HST 13%",
    "NB": "CA HST 15%",
    "NL": "CA HST 15%",
    "NS": "CA HST 15%",
    "PE": "CA HST 15%",
    "BC": "CA GST + PST 7%",
    "MB": "CA GST + PST 7%",
    "SK": "CA GST + PST 6%",
    "QC": "CA GST + QST",
}

PROVINCE_NAMES = {
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


def _template_rows(base_name, config):
    """Return tax row dicts for a given template name using company-specific accounts."""
    gst = config.gst_account
    hst = config.hst_account
    pst = config.pst_account
    qst = config.qst_account

    definitions = {
        "CA GST Only": [
            {"charge_type": "On Net Total", "account_head": gst, "description": "GST 5%", "rate": 5.0},
        ],
        "CA HST 13%": [
            {"charge_type": "On Net Total", "account_head": hst, "description": "HST 13%", "rate": 13.0},
        ],
        "CA HST 15%": [
            {"charge_type": "On Net Total", "account_head": hst, "description": "HST 15%", "rate": 15.0},
        ],
        "CA GST + PST 7%": [
            {"charge_type": "On Net Total", "account_head": gst, "description": "GST 5%", "rate": 5.0},
            {"charge_type": "On Net Total", "account_head": pst, "description": "PST 7%", "rate": 7.0},
        ],
        "CA GST + PST 6%": [
            {"charge_type": "On Net Total", "account_head": gst, "description": "GST 5%", "rate": 5.0},
            {"charge_type": "On Net Total", "account_head": pst, "description": "PST 6%", "rate": 6.0},
        ],
        "CA GST + QST": [
            {"charge_type": "On Net Total", "account_head": gst, "description": "GST 5%", "rate": 5.0},
            {"charge_type": "On Net Total", "account_head": qst, "description": "QST 9.975%", "rate": 9.975},
        ],
    }
    return definitions.get(base_name, [])


def _get_config(company):
    names = frappe.get_all("CA Company Tax Config", filters={"company": company}, pluck="name", limit=1)
    if not names:
        frappe.throw(f"No CA Company Tax Config found for company '{company}'. Create one first.")
    return frappe.get_doc("CA Company Tax Config", names[0])


@frappe.whitelist()
def setup_company_taxes(company):
    """
    Create or update Sales Tax Templates and Tax Rules for one company.
    Called from the Generate Tax Templates button on CA Company Tax Config.
    """
    config = _get_config(company)

    if not config.enabled:
        frappe.throw(f"CA Company Tax Config for '{company}' is disabled.")
    if not config.collects_canada_sales_tax:
        frappe.throw(f"'{company}' is marked as not collecting Canadian sales tax.")
    if config.is_small_supplier:
        frappe.throw(f"'{company}' is a small supplier — no tax templates needed.")

    missing = []
    if not config.gst_account:
        missing.append("GST Account")
    if not config.hst_account:
        missing.append("HST Account")
    if missing:
        frappe.throw(f"Set the following accounts before generating templates: {', '.join(missing)}")

    abbr = frappe.db.get_value("Company", company, "abbr")
    if not abbr:
        frappe.throw(f"Company abbreviation not found for '{company}'.")

    tpl_created = tpl_updated = rule_created = rule_updated = 0

    # --- Sales Tax Templates ---
    for base_name in set(PROVINCE_TO_TEMPLATE.values()):
        rows = _template_rows(base_name, config)
        # Skip templates whose required account is missing (e.g. PST when company is in ON)
        if any(not r["account_head"] for r in rows):
            continue

        tpl_name = f"{base_name} - {abbr}"
        if frappe.db.exists("Sales Taxes and Charges Template", tpl_name):
            doc = frappe.get_doc("Sales Taxes and Charges Template", tpl_name)
            doc.taxes = []
            for row in rows:
                doc.append("taxes", row)
            doc.company = company
            doc.save(ignore_permissions=True)
            tpl_updated += 1
        else:
            doc = frappe.new_doc("Sales Taxes and Charges Template")
            doc.title = tpl_name
            doc.company = company
            for row in rows:
                doc.append("taxes", row)
            doc.insert(ignore_permissions=True)
            tpl_created += 1

    # --- Tax Rules (one per province, billing_state = province code) ---
    for province, base_name in PROVINCE_TO_TEMPLATE.items():
        tpl_name = f"{base_name} - {abbr}"
        if not frappe.db.exists("Sales Taxes and Charges Template", tpl_name):
            continue

        existing = frappe.get_all(
            "Tax Rule",
            filters={
                "tax_type": "Sales",
                "company": company,
                "billing_state": province,
                "billing_country": "Canada",
            },
            pluck="name",
            limit=1,
        )
        if existing:
            frappe.db.set_value("Tax Rule", existing[0], "sales_tax_template", tpl_name)
            rule_updated += 1
        else:
            rule = frappe.new_doc("Tax Rule")
            rule.tax_type = "Sales"
            rule.company = company
            rule.billing_state = province
            rule.billing_country = "Canada"
            rule.sales_tax_template = tpl_name
            rule.priority = 10
            rule.insert(ignore_permissions=True)
            rule_created += 1

    frappe.db.commit()

    return {
        "templates_created": tpl_created,
        "templates_updated": tpl_updated,
        "rules_created": rule_created,
        "rules_updated": rule_updated,
    }
