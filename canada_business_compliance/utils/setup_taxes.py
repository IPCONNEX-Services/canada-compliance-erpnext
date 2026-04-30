import frappe

from canada_business_compliance.utils.tax_resolver import (
    PROVINCE_TO_TEMPLATE_BASE as PROVINCE_TO_TEMPLATE,
    _province_code,
)

# Advanced mode overrides the three PST provinces with per-province templates
PROVINCE_TO_TEMPLATE_ADVANCED = {
    **PROVINCE_TO_TEMPLATE,
    "BC": "CA GST + BC PST 7%",
    "MB": "CA GST + MB RST 7%",
    "SK": "CA GST + SK PST 6%",
}

# GST, HST, QST accounts are the same in both modes
_TAX_ACCOUNTS_COMMON = {
    "gst": ("GST Payable", "Tax"),
    "hst": ("HST Payable", "Tax"),
    "qst": ("QST Payable", "Tax"),
}

_TAX_ACCOUNTS_SIMPLE = {
    **_TAX_ACCOUNTS_COMMON,
    "pst": ("PST Payable", "Tax"),
}

_TAX_ACCOUNTS_ADVANCED = {
    **_TAX_ACCOUNTS_COMMON,
    "pst_bc": ("BC PST Payable", "Tax"),
    "pst_sk": ("SK PST Payable", "Tax"),
    "rst_mb": ("MB RST Payable", "Tax"),
}


def _accounts_for_province(province_code, advanced_mode=False):
    """
    Return account keys to create for a province.
    GST + HST always included. PST/QST depend on province and mode.
    """
    needed = {"gst", "hst"}
    if advanced_mode:
        needed.update({"pst_bc", "pst_sk", "rst_mb"})
    elif province_code in ("BC", "SK", "MB"):
        needed.add("pst")
    if province_code == "QC":
        needed.add("qst")
    return needed


def _template_rows(base_name, config):
    """Return tax row dicts for a template name using company-specific accounts."""
    gst = config.gst_account
    hst = config.hst_account
    pst = config.pst_account
    qst = config.qst_account
    pst_bc = getattr(config, "pst_bc_account", None)
    pst_sk = getattr(config, "pst_sk_account", None)
    rst_mb = getattr(config, "rst_mb_account", None)

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
        "CA GST + BC PST 7%": [
            {"charge_type": "On Net Total", "account_head": gst,    "description": "GST 5%",    "rate": 5.0},
            {"charge_type": "On Net Total", "account_head": pst_bc, "description": "BC PST 7%", "rate": 7.0},
        ],
        "CA GST + MB RST 7%": [
            {"charge_type": "On Net Total", "account_head": gst,    "description": "GST 5%",    "rate": 5.0},
            {"charge_type": "On Net Total", "account_head": rst_mb, "description": "MB RST 7%", "rate": 7.0},
        ],
        "CA GST + SK PST 6%": [
            {"charge_type": "On Net Total", "account_head": gst,    "description": "GST 5%",    "rate": 5.0},
            {"charge_type": "On Net Total", "account_head": pst_sk, "description": "SK PST 6%", "rate": 6.0},
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
    In advanced PST mode, generates province-specific PST templates (BC/SK/MB).
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

    advanced = bool(config.use_advanced_pst)
    province_map = PROVINCE_TO_TEMPLATE_ADVANCED if advanced else PROVINCE_TO_TEMPLATE
    tpl_created = tpl_updated = rule_created = rule_updated = 0

    # Batch-fetch which templates already exist to avoid N existence checks in the loop
    all_tpl_names = [f"{base} - {abbr}" for base in set(province_map.values())]
    existing_tpl = set(frappe.get_all(
        "Sales Taxes and Charges Template",
        filters={"name": ["in", all_tpl_names], "company": company},
        pluck="name",
    ))

    # Batch-fetch existing Tax Rules for this company to avoid N queries in the loop
    existing_rules = {
        r.billing_state: r.name
        for r in frappe.get_all(
            "Tax Rule",
            filters={"tax_type": "Sales", "company": company, "billing_country": "Canada"},
            fields=["name", "billing_state"],
        )
    }

    # --- Sales Tax Templates ---
    for base_name in set(province_map.values()):
        rows = _template_rows(base_name, config)
        if any(not r["account_head"] for r in rows):
            continue

        tpl_name = f"{base_name} - {abbr}"
        if tpl_name in existing_tpl:
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

    # --- Tax Rules (one per province) ---
    for province, base_name in province_map.items():
        tpl_name = f"{base_name} - {abbr}"
        if not frappe.db.exists("Sales Taxes and Charges Template", tpl_name):
            continue

        if province in existing_rules:
            frappe.db.set_value("Tax Rule", existing_rules[province], "sales_tax_template", tpl_name)
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

    return {
        "templates_created": tpl_created,
        "templates_updated": tpl_updated,
        "rules_created": rule_created,
        "rules_updated": rule_updated,
        "advanced_mode": advanced,
    }


def _find_tax_parent(company, abbr):
    """Return the parent account to use for new tax accounts."""
    candidates = [f"Duties and Taxes - {abbr}", f"Tax Payable - {abbr}"]
    found = set(frappe.get_all("Account", filters={"name": ["in", candidates]}, pluck="name"))
    for candidate in candidates:
        if candidate in found:
            return candidate

    existing = frappe.get_all(
        "Account",
        filters={"company": company, "account_type": "Tax", "is_group": 0},
        fields=["parent_account"],
        limit=1,
    )
    if existing and existing[0].parent_account:
        return existing[0].parent_account

    frappe.throw(
        f"Cannot find a parent account for tax accounts in <b>{company}</b>. "
        f"Please create <b>Duties and Taxes - {abbr}</b> in the Chart of Accounts first.",
        title="Chart of Accounts Incomplete",
    )


@frappe.whitelist()
def ensure_company_tax_accounts(company):
    """
    Create tax payable accounts for the company based on its registered province and mode.
    Simple mode: GST + HST always; PST for BC/SK/MB; QST for QC.
    Advanced mode: GST + HST + per-province PST accounts; QST for QC.
    Saves account links back to CA Company Tax Config.
    """
    frappe.has_permission("CA Company Tax Config", "write", throw=True)

    abbr = frappe.db.get_value("Company", company, "abbr")
    if not abbr:
        frappe.throw(f"Company abbreviation not found for '{company}'.")

    # Fetch config doc once — reused for both reading settings and saving account links
    configs = frappe.get_all("CA Company Tax Config", filters={"company": company}, pluck="name", limit=1)
    config = None
    province = None
    advanced = False
    if configs:
        config = frappe.get_doc("CA Company Tax Config", configs[0])
        province = _province_code(config.company_province)
        advanced = bool(config.use_advanced_pst)

    tax_accounts = _TAX_ACCOUNTS_ADVANCED if advanced else _TAX_ACCOUNTS_SIMPLE
    accounts_to_create = _accounts_for_province(province, advanced) if province else set(tax_accounts.keys())

    parent = _find_tax_parent(company, abbr)

    # Batch-fetch all existing Tax accounts for the company to avoid per-account DB calls
    all_tax_accounts = frappe.get_all(
        "Account",
        filters={"company": company, "account_type": "Tax"},
        fields=["name", "account_name"],
    )
    existing_names = {a.name for a in all_tax_accounts}
    existing_account_names = [a.account_name for a in all_tax_accounts]

    result = {}
    created = []
    warnings = []

    for key, (account_name, account_type) in tax_accounts.items():
        if key not in accounts_to_create:
            continue

        full_name = f"{account_name} - {abbr}"
        if full_name in existing_names:
            result[key] = full_name
            continue

        # Warn if a differently-named account with the same tax type already exists
        first_word = account_name.split()[0].lower()
        similar = [n for n, an in zip(
            [a.name for a in all_tax_accounts],
            existing_account_names,
        ) if first_word in an.lower()]
        if similar:
            warnings.append(
                f"Creating <b>{full_name}</b> but found similar existing account(s): "
                f"{', '.join(similar[:3])}. Verify you do not have duplicates."
            )

        doc = frappe.new_doc("Account")
        doc.account_name = account_name
        doc.parent_account = parent
        doc.account_type = account_type
        doc.company = company
        doc.insert(ignore_permissions=True)
        result[key] = doc.name
        created.append(account_name)
        # Keep in-memory list current so later iterations in this loop see it
        all_tax_accounts.append(frappe._dict(name=doc.name, account_name=account_name))
        existing_account_names.append(account_name)

    if config:
        config.gst_account = result.get("gst") or config.gst_account
        config.hst_account = result.get("hst") or config.hst_account
        config.qst_account = result.get("qst") or config.qst_account
        if advanced:
            config.pst_bc_account = result.get("pst_bc") or config.pst_bc_account
            config.pst_sk_account = result.get("pst_sk") or config.pst_sk_account
            config.rst_mb_account = result.get("rst_mb") or config.rst_mb_account
        else:
            config.pst_account = result.get("pst") or config.pst_account
        config.save(ignore_permissions=True)

    return {"accounts": result, "created": created, "warnings": warnings, "advanced_mode": advanced}
