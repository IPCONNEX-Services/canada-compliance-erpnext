import frappe

# Simple mode: one PST account for all PST provinces
_TAX_ACCOUNTS_SIMPLE = {
    "gst": ("GST Payable", "Tax"),
    "hst": ("HST Payable", "Tax"),
    "pst": ("PST Payable", "Tax"),
    "qst": ("QST Payable", "Tax"),
}

# Advanced mode: separate PST account per province
_TAX_ACCOUNTS_ADVANCED = {
    "gst":    ("GST Payable",     "Tax"),
    "hst":    ("HST Payable",     "Tax"),
    "pst_bc": ("BC PST Payable",  "Tax"),
    "pst_sk": ("SK PST Payable",  "Tax"),
    "rst_mb": ("MB RST Payable",  "Tax"),
    "qst":    ("QST Payable",     "Tax"),
}

# Simple mode province → template name
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

# Advanced mode: PST provinces get province-specific templates
PROVINCE_TO_TEMPLATE_ADVANCED = {
    **PROVINCE_TO_TEMPLATE,
    "BC": "CA GST + BC PST 7%",
    "MB": "CA GST + MB RST 7%",
    "SK": "CA GST + SK PST 6%",
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


def _province_code(province_str):
    """Extract 2-letter code from 'AB - Alberta' or return 'AB' as-is."""
    if not province_str:
        return None
    return province_str.split(" - ")[0].strip().upper()


def _accounts_for_province(province_code, advanced_mode=False):
    """
    Return the set of account keys to create for a given province.
    GST + HST are always included (needed for pan-Canadian selling).
    Simple mode: PST for BC/SK/MB; QST for QC.
    Advanced mode: all three per-province PST accounts + QST for QC.
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
    """Return tax row dicts for a given template name using company-specific accounts."""
    gst = config.gst_account
    hst = config.hst_account
    pst = config.pst_account
    qst = config.qst_account
    pst_bc = getattr(config, "pst_bc_account", None)
    pst_sk = getattr(config, "pst_sk_account", None)
    rst_mb = getattr(config, "rst_mb_account", None)

    definitions = {
        # --- Simple mode templates ---
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
        # --- Advanced mode per-province PST templates ---
        "CA GST + BC PST 7%": [
            {"charge_type": "On Net Total", "account_head": gst,    "description": "GST 5%",     "rate": 5.0},
            {"charge_type": "On Net Total", "account_head": pst_bc, "description": "BC PST 7%",  "rate": 7.0},
        ],
        "CA GST + MB RST 7%": [
            {"charge_type": "On Net Total", "account_head": gst,    "description": "GST 5%",     "rate": 5.0},
            {"charge_type": "On Net Total", "account_head": rst_mb, "description": "MB RST 7%",  "rate": 7.0},
        ],
        "CA GST + SK PST 6%": [
            {"charge_type": "On Net Total", "account_head": gst,    "description": "GST 5%",     "rate": 5.0},
            {"charge_type": "On Net Total", "account_head": pst_sk, "description": "SK PST 6%",  "rate": 6.0},
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

    advanced = bool(config.use_advanced_pst)
    province_map = PROVINCE_TO_TEMPLATE_ADVANCED if advanced else PROVINCE_TO_TEMPLATE
    tpl_created = tpl_updated = rule_created = rule_updated = 0

    # --- Sales Tax Templates ---
    for base_name in set(province_map.values()):
        rows = _template_rows(base_name, config)
        # Skip templates whose required account is missing
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

    # --- Tax Rules (one per province) ---
    for province, base_name in province_map.items():
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

    return {
        "templates_created": tpl_created,
        "templates_updated": tpl_updated,
        "rules_created": rule_created,
        "rules_updated": rule_updated,
        "advanced_mode": advanced,
    }


def _find_tax_parent(company, abbr):
    """Return the parent account to use for new tax accounts."""
    for candidate in [
        f"Duties and Taxes - {abbr}",
        f"Tax Payable - {abbr}",
    ]:
        if frappe.db.exists("Account", candidate):
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
    Advanced mode: GST + HST + all three per-province PST accounts; QST for QC.
    Saves account links back to CA Company Tax Config.
    """
    frappe.has_permission("CA Company Tax Config", "write", throw=True)

    abbr = frappe.db.get_value("Company", company, "abbr")
    if not abbr:
        frappe.throw(f"Company abbreviation not found for '{company}'.")

    configs = frappe.get_all("CA Company Tax Config", filters={"company": company}, pluck="name", limit=1)
    province = None
    advanced = False
    if configs:
        config_vals = frappe.db.get_value(
            "CA Company Tax Config", configs[0], ["company_province", "use_advanced_pst"], as_dict=True
        )
        province = _province_code(config_vals.get("company_province"))
        advanced = bool(config_vals.get("use_advanced_pst"))

    tax_accounts = _TAX_ACCOUNTS_ADVANCED if advanced else _TAX_ACCOUNTS_SIMPLE
    accounts_to_create = _accounts_for_province(province, advanced) if province else set(tax_accounts.keys())

    parent = _find_tax_parent(company, abbr)
    result = {}
    created = []
    warnings = []

    for key, (account_name, account_type) in tax_accounts.items():
        if key not in accounts_to_create:
            continue

        full_name = f"{account_name} - {abbr}"
        if frappe.db.exists("Account", full_name):
            result[key] = full_name
            continue

        # Warn if a differently-named account with the same tax type already exists
        first_word = account_name.split()[0]
        similar = frappe.get_all(
            "Account",
            filters={"company": company, "account_type": "Tax", "account_name": ["like", f"%{first_word}%"]},
            pluck="name",
            limit=3,
        )
        if similar:
            warnings.append(
                f"Creating <b>{full_name}</b> but found similar existing account(s): "
                f"{', '.join(similar)}. Verify you do not have duplicates."
            )

        doc = frappe.new_doc("Account")
        doc.account_name = account_name
        doc.parent_account = parent
        doc.account_type = account_type
        doc.company = company
        doc.insert(ignore_permissions=True)
        result[key] = doc.name
        created.append(account_name)

    # Persist account links back onto the config record
    if configs:
        config = frappe.get_doc("CA Company Tax Config", configs[0])
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
