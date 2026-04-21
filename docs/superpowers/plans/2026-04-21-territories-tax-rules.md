# Territories & Tax Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the custom `resolve_taxes()` injection with ERPNext's native Territory → Tax Rule pipeline: install 13 Canadian province/territory records, 6 sales tax templates, and 13 tax rules as fixtures; auto-assign customer territory from their primary address; override per-invoice from shipping address; and add a global toggle to CA Tax Settings.

**Architecture:** A new `utils/territory.py` module exposes `province_to_territory()` (pure dict lookup) and `set_customer_territory()` (doc_events hook). Three fixture JSON files ship the Territory, Sales Taxes and Charges Template, and Tax Rule records. The JS is simplified to a single trigger on `shipping_address_name` change that sets `frm.territory`; ERPNext's native Tax Rule engine applies the correct template automatically. The old `tax_resolver.py` / `tax_calculator.py` are deleted.

**Tech Stack:** Python 3, Frappe/ERPNext fixtures system, ERPNext Territory + Tax Rule + Sales Taxes and Charges Template DocTypes, Frappe JavaScript form client, pytest with frappe module mock

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `canada_business_compliance/utils/territory.py` | Create | Province → territory map + customer hook |
| `tests/test_territory.py` | Create | Unit tests for territory.py |
| `canada_business_compliance/ca_sales_tax/doctype/ca_tax_settings/ca_tax_settings.json` | Modify | Add `use_tax_rules` Check field |
| `canada_business_compliance/ca_sales_tax/doctype/ca_tax_settings/ca_tax_settings.py` | Modify | Add `on_update` toggle logic |
| `canada_business_compliance/fixtures/territory.json` | Create | 13 Territory records |
| `canada_business_compliance/fixtures/sales_taxes_and_charges_template.json` | Create | 6 Sales Tax Template records |
| `canada_business_compliance/fixtures/tax_rule.json` | Create | 13 Tax Rule records |
| `canada_business_compliance/hooks.py` | Modify | Add `doc_events` for Customer + expand fixtures list |
| `canada_business_compliance/public/js/ca_sales_tax.js` | Modify | Replace `resolve_taxes()` with territory override |
| `canada_business_compliance/utils/tax_resolver.py` | Delete | Replaced by native Tax Rule system |
| `canada_business_compliance/utils/tax_calculator.py` | Delete | Replaced by native Tax Rule system |
| `tests/test_tax_resolver.py` | Delete | Tests for deleted module |

---

### Task 1: utils/territory.py + tests

**Files:**
- Create: `canada_business_compliance/utils/territory.py`
- Create: `tests/test_territory.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_territory.py` with the following content:

```python
import pytest


# ── province_to_territory ─────────────────────────────────────────────────────

def test_all_13_province_codes(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    expected = {
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
    for code, name in expected.items():
        assert province_to_territory(code) == name, f"Failed for {code}"


def test_unknown_code_returns_none(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory("XX") is None


def test_empty_string_returns_none(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory("") is None


def test_none_returns_none(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory(None) is None


def test_lowercase_input_normalised(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory("on") == "Ontario"
    assert province_to_territory("qc") == "Quebec"


def test_whitespace_stripped(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory("  ON  ") == "Ontario"


# ── set_customer_territory ────────────────────────────────────────────────────

def test_set_customer_territory_sets_territory_from_primary_address(frappe):
    from canada_business_compliance.utils.territory import set_customer_territory
    from unittest.mock import MagicMock

    frappe.get_all.return_value = ["Addr-001"]  # pluck="parent" returns list of strings

    def get_value_side_effect(doctype, filters_or_name, field):
        if doctype == "Address" and isinstance(filters_or_name, dict) and field == "name":
            return "Addr-001"
        if doctype == "Address" and filters_or_name == "Addr-001" and field == "state":
            return "ON"
        return None

    frappe.db.get_value.side_effect = get_value_side_effect

    doc = MagicMock()
    doc.name = "CUST-001"
    doc.territory = ""

    set_customer_territory(doc)

    frappe.db.set_value.assert_called_once_with("Customer", "CUST-001", "territory", "Ontario")


def test_set_customer_territory_skips_when_already_correct(frappe):
    from canada_business_compliance.utils.territory import set_customer_territory
    from unittest.mock import MagicMock

    frappe.get_all.return_value = ["Addr-001"]

    def get_value_side_effect(doctype, filters_or_name, field):
        if doctype == "Address" and isinstance(filters_or_name, dict) and field == "name":
            return "Addr-001"
        if doctype == "Address" and filters_or_name == "Addr-001" and field == "state":
            return "ON"
        return None

    frappe.db.get_value.side_effect = get_value_side_effect

    doc = MagicMock()
    doc.name = "CUST-001"
    doc.territory = "Ontario"  # already set correctly

    set_customer_territory(doc)

    frappe.db.set_value.assert_not_called()


def test_set_customer_territory_no_address(frappe):
    from canada_business_compliance.utils.territory import set_customer_territory
    from unittest.mock import MagicMock

    frappe.get_all.return_value = []  # no addresses linked

    doc = MagicMock()
    doc.name = "CUST-002"

    set_customer_territory(doc)

    frappe.db.set_value.assert_not_called()


def test_set_customer_territory_unknown_province(frappe):
    from canada_business_compliance.utils.territory import set_customer_territory
    from unittest.mock import MagicMock

    frappe.get_all.return_value = ["Addr-001"]

    def get_value_side_effect(doctype, filters_or_name, field):
        if doctype == "Address" and isinstance(filters_or_name, dict) and field == "name":
            return "Addr-001"
        if doctype == "Address" and filters_or_name == "Addr-001" and field == "state":
            return "ZZ"  # unmapped province
        return None

    frappe.db.get_value.side_effect = get_value_side_effect

    doc = MagicMock()
    doc.name = "CUST-003"
    doc.territory = "All Territories"

    set_customer_territory(doc)

    frappe.db.set_value.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/omarelmohri/Claude/canada-business-compliance
python -m pytest tests/test_territory.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` for `canada_business_compliance.utils.territory`

- [ ] **Step 3: Create utils/territory.py**

```python
import frappe

PROVINCE_TERRITORY = {
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


def province_to_territory(province_code: str):
    """Map a province code (e.g. 'ON') to an ERPNext Territory name."""
    return PROVINCE_TERRITORY.get((province_code or "").strip().upper())


def set_customer_territory(doc, method=None):
    links = frappe.get_all(
        "Dynamic Link",
        filters={"link_doctype": "Customer", "link_name": doc.name, "parenttype": "Address"},
        pluck="parent",
    )
    if not links:
        return
    address_name = (
        frappe.db.get_value("Address", {"name": ["in", links], "is_primary_address": 1}, "name")
        or links[0]
    )
    state = frappe.db.get_value("Address", address_name, "state") or ""
    territory = province_to_territory(state)
    if territory and doc.territory != territory:
        frappe.db.set_value("Customer", doc.name, "territory", territory)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_territory.py -v
```

Expected: all 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add canada_business_compliance/utils/territory.py tests/test_territory.py
git commit -m "feat: add utils/territory.py — province_to_territory() + set_customer_territory()"
```

---

### Task 2: CA Tax Settings — use_tax_rules toggle

**Files:**
- Modify: `canada_business_compliance/ca_sales_tax/doctype/ca_tax_settings/ca_tax_settings.json`
- Modify: `canada_business_compliance/ca_sales_tax/doctype/ca_tax_settings/ca_tax_settings.py`

- [ ] **Step 1: Add use_tax_rules field to the JSON**

Open `canada_business_compliance/ca_sales_tax/doctype/ca_tax_settings/ca_tax_settings.json`.

In `field_order`, insert `"tax_rules_section"` and `"use_tax_rules"` after `"apply_to_sales_invoice"`:

```json
"field_order": [
  "is_small_supplier",
  "small_supplier_note",
  "tax_accounts_section",
  "gst_account",
  "hst_account",
  "col_break_1",
  "pst_account",
  "qst_account",
  "registration_section",
  "gst_registration_number",
  "qst_registration_number",
  "apply_to_section",
  "apply_to_sales_order",
  "apply_to_quotation",
  "apply_to_sales_invoice",
  "tax_rules_section",
  "use_tax_rules"
],
```

In `fields`, append these two entries before the closing `]`:

```json
  {
   "fieldname": "tax_rules_section",
   "fieldtype": "Section Break",
   "label": "Tax Rules"
  },
  {
   "default": "1",
   "fieldname": "use_tax_rules",
   "fieldtype": "Check",
   "label": "Use Tax Rules",
   "description": "Enable ERPNext Tax Rules for automatic Canadian tax. Uncheck to disable all CA Tax Rules and fill taxes manually."
  }
```

- [ ] **Step 2: Add on_update to ca_tax_settings.py**

Replace the entire content of `canada_business_compliance/ca_sales_tax/doctype/ca_tax_settings/ca_tax_settings.py` with:

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add canada_business_compliance/ca_sales_tax/doctype/ca_tax_settings/ca_tax_settings.json \
        canada_business_compliance/ca_sales_tax/doctype/ca_tax_settings/ca_tax_settings.py
git commit -m "feat: add use_tax_rules toggle to CA Tax Settings"
```

---

### Task 3: Territory fixtures (13 records)

**Files:**
- Create: `canada_business_compliance/fixtures/territory.json`

(No runtime test needed — structural correctness verified by reading the file.)

- [ ] **Step 1: Create the fixtures directory (if it doesn't exist) and write territory.json**

Create `canada_business_compliance/fixtures/territory.json`:

```json
[
  {
    "doctype": "Territory",
    "name": "Alberta",
    "territory_name": "Alberta",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "British Columbia",
    "territory_name": "British Columbia",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "Manitoba",
    "territory_name": "Manitoba",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "New Brunswick",
    "territory_name": "New Brunswick",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "Newfoundland and Labrador",
    "territory_name": "Newfoundland and Labrador",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "Northwest Territories",
    "territory_name": "Northwest Territories",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "Nova Scotia",
    "territory_name": "Nova Scotia",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "Nunavut",
    "territory_name": "Nunavut",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "Ontario",
    "territory_name": "Ontario",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "Prince Edward Island",
    "territory_name": "Prince Edward Island",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "Quebec",
    "territory_name": "Quebec",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "Saskatchewan",
    "territory_name": "Saskatchewan",
    "parent_territory": "Canada",
    "is_group": 0
  },
  {
    "doctype": "Territory",
    "name": "Yukon",
    "territory_name": "Yukon",
    "parent_territory": "Canada",
    "is_group": 0
  }
]
```

- [ ] **Step 2: Verify the file is valid JSON**

```bash
python -c "import json; data = json.load(open('canada_business_compliance/fixtures/territory.json')); print(f'OK — {len(data)} territories')"
```

Expected: `OK — 13 territories`

- [ ] **Step 3: Commit**

```bash
git add canada_business_compliance/fixtures/territory.json
git commit -m "feat: add Territory fixtures for all 13 Canadian provinces and territories"
```

---

### Task 4: Sales Tax Template fixtures (6 records)

**Files:**
- Create: `canada_business_compliance/fixtures/sales_taxes_and_charges_template.json`

Account heads are intentionally left empty — users configure them in CA Tax Settings.

- [ ] **Step 1: Create sales_taxes_and_charges_template.json**

```json
[
  {
    "doctype": "Sales Taxes and Charges Template",
    "name": "CA GST Only",
    "title": "CA GST Only",
    "is_default": 0,
    "taxes": [
      {
        "doctype": "Sales Taxes and Charges",
        "charge_type": "On Net Total",
        "account_head": "",
        "description": "GST 5%",
        "rate": 5.0
      }
    ]
  },
  {
    "doctype": "Sales Taxes and Charges Template",
    "name": "CA HST 13%",
    "title": "CA HST 13%",
    "is_default": 0,
    "taxes": [
      {
        "doctype": "Sales Taxes and Charges",
        "charge_type": "On Net Total",
        "account_head": "",
        "description": "HST 13%",
        "rate": 13.0
      }
    ]
  },
  {
    "doctype": "Sales Taxes and Charges Template",
    "name": "CA HST 15%",
    "title": "CA HST 15%",
    "is_default": 0,
    "taxes": [
      {
        "doctype": "Sales Taxes and Charges",
        "charge_type": "On Net Total",
        "account_head": "",
        "description": "HST 15%",
        "rate": 15.0
      }
    ]
  },
  {
    "doctype": "Sales Taxes and Charges Template",
    "name": "CA GST + PST 7%",
    "title": "CA GST + PST 7%",
    "is_default": 0,
    "taxes": [
      {
        "doctype": "Sales Taxes and Charges",
        "charge_type": "On Net Total",
        "account_head": "",
        "description": "GST 5%",
        "rate": 5.0
      },
      {
        "doctype": "Sales Taxes and Charges",
        "charge_type": "On Net Total",
        "account_head": "",
        "description": "PST 7%",
        "rate": 7.0
      }
    ]
  },
  {
    "doctype": "Sales Taxes and Charges Template",
    "name": "CA GST + PST 6%",
    "title": "CA GST + PST 6%",
    "is_default": 0,
    "taxes": [
      {
        "doctype": "Sales Taxes and Charges",
        "charge_type": "On Net Total",
        "account_head": "",
        "description": "GST 5%",
        "rate": 5.0
      },
      {
        "doctype": "Sales Taxes and Charges",
        "charge_type": "On Net Total",
        "account_head": "",
        "description": "PST 6%",
        "rate": 6.0
      }
    ]
  },
  {
    "doctype": "Sales Taxes and Charges Template",
    "name": "CA GST + QST",
    "title": "CA GST + QST",
    "is_default": 0,
    "taxes": [
      {
        "doctype": "Sales Taxes and Charges",
        "charge_type": "On Net Total",
        "account_head": "",
        "description": "GST 5%",
        "rate": 5.0
      },
      {
        "doctype": "Sales Taxes and Charges",
        "charge_type": "On Net Total",
        "account_head": "",
        "description": "QST 9.975%",
        "rate": 9.975
      }
    ]
  }
]
```

- [ ] **Step 2: Verify the file is valid JSON**

```bash
python -c "import json; data = json.load(open('canada_business_compliance/fixtures/sales_taxes_and_charges_template.json')); print(f'OK — {len(data)} templates')"
```

Expected: `OK — 6 templates`

- [ ] **Step 3: Commit**

```bash
git add canada_business_compliance/fixtures/sales_taxes_and_charges_template.json
git commit -m "feat: add Sales Tax Template fixtures for all 6 Canadian rate combinations"
```

---

### Task 5: Tax Rule fixtures (13 records)

**Files:**
- Create: `canada_business_compliance/fixtures/tax_rule.json`

Rules are named `CA <Territory>` so the toggle filter `["name", "like", "CA %"]` matches all of them.

- [ ] **Step 1: Create tax_rule.json**

```json
[
  {
    "doctype": "Tax Rule",
    "name": "CA Alberta",
    "title": "CA Alberta",
    "tax_type": "Sales",
    "sales_tax_template": "CA GST Only",
    "territory": "Alberta",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA Northwest Territories",
    "title": "CA Northwest Territories",
    "tax_type": "Sales",
    "sales_tax_template": "CA GST Only",
    "territory": "Northwest Territories",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA Nunavut",
    "title": "CA Nunavut",
    "tax_type": "Sales",
    "sales_tax_template": "CA GST Only",
    "territory": "Nunavut",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA Yukon",
    "title": "CA Yukon",
    "tax_type": "Sales",
    "sales_tax_template": "CA GST Only",
    "territory": "Yukon",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA Ontario",
    "title": "CA Ontario",
    "tax_type": "Sales",
    "sales_tax_template": "CA HST 13%",
    "territory": "Ontario",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA New Brunswick",
    "title": "CA New Brunswick",
    "tax_type": "Sales",
    "sales_tax_template": "CA HST 15%",
    "territory": "New Brunswick",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA Newfoundland and Labrador",
    "title": "CA Newfoundland and Labrador",
    "tax_type": "Sales",
    "sales_tax_template": "CA HST 15%",
    "territory": "Newfoundland and Labrador",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA Nova Scotia",
    "title": "CA Nova Scotia",
    "tax_type": "Sales",
    "sales_tax_template": "CA HST 15%",
    "territory": "Nova Scotia",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA Prince Edward Island",
    "title": "CA Prince Edward Island",
    "tax_type": "Sales",
    "sales_tax_template": "CA HST 15%",
    "territory": "Prince Edward Island",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA British Columbia",
    "title": "CA British Columbia",
    "tax_type": "Sales",
    "sales_tax_template": "CA GST + PST 7%",
    "territory": "British Columbia",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA Manitoba",
    "title": "CA Manitoba",
    "tax_type": "Sales",
    "sales_tax_template": "CA GST + PST 7%",
    "territory": "Manitoba",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA Saskatchewan",
    "title": "CA Saskatchewan",
    "tax_type": "Sales",
    "sales_tax_template": "CA GST + PST 6%",
    "territory": "Saskatchewan",
    "priority": 1,
    "disabled": 0
  },
  {
    "doctype": "Tax Rule",
    "name": "CA Quebec",
    "title": "CA Quebec",
    "tax_type": "Sales",
    "sales_tax_template": "CA GST + QST",
    "territory": "Quebec",
    "priority": 1,
    "disabled": 0
  }
]
```

- [ ] **Step 2: Verify the file is valid JSON**

```bash
python -c "import json; data = json.load(open('canada_business_compliance/fixtures/tax_rule.json')); print(f'OK — {len(data)} tax rules')"
```

Expected: `OK — 13 tax rules`

- [ ] **Step 3: Commit**

```bash
git add canada_business_compliance/fixtures/tax_rule.json
git commit -m "feat: add Tax Rule fixtures — one per Canadian province/territory"
```

---

### Task 6: Update hooks.py

**Files:**
- Modify: `canada_business_compliance/hooks.py`

- [ ] **Step 1: Add doc_events and expand fixtures list**

Replace the entire content of `canada_business_compliance/hooks.py` with:

```python
app_name = "canada_business_compliance"
app_title = "Canada Business Compliance"
app_publisher = "IPCONNEX"
app_description = "Canadian business compliance for Frappe/ERPNext — sales tax, payroll, and more"
app_email = "dev@ipconnex.com"
app_license = "MIT"
app_version = "0.2.0"

doctype_js = {
    "Sales Order":   "canada_business_compliance/public/js/ca_sales_tax.js",
    "Quotation":     "canada_business_compliance/public/js/ca_sales_tax.js",
    "Sales Invoice": "canada_business_compliance/public/js/ca_sales_tax.js",
}

doc_events = {
    "Customer": {
        "after_insert": "canada_business_compliance.utils.territory.set_customer_territory",
        "on_update": "canada_business_compliance.utils.territory.set_customer_territory",
    }
}

custom_fields = {
    "Customer": [
        {
            "fieldname": "ca_tax_section",
            "fieldtype": "Section Break",
            "label": "Canadian Tax",
            "insert_after": "customer_type",
            "collapsible": 1,
        },
        {
            "fieldname": "pst_exempt",
            "fieldtype": "Check",
            "label": "PST/RST Exempt",
            "description": "Reseller exempt from PST: BC (7%), Saskatchewan (6%), Manitoba RST (7%)",
            "insert_after": "ca_tax_section",
        },
        {
            "fieldname": "pst_exemption_number",
            "fieldtype": "Data",
            "label": "PST Exemption Certificate No.",
            "depends_on": "eval:doc.pst_exempt",
            "insert_after": "pst_exempt",
        },
        {
            "fieldname": "qst_exempt",
            "fieldtype": "Check",
            "label": "QST Exempt (Quebec Reseller)",
            "description": "Businesses with a QST number buying goods/services for resale in Quebec",
            "insert_after": "pst_exemption_number",
        },
        {
            "fieldname": "qst_exemption_number",
            "fieldtype": "Data",
            "label": "QST Registration No. (Resale)",
            "depends_on": "eval:doc.qst_exempt",
            "insert_after": "qst_exempt",
        },
    ],
    "Item Group": [
        {
            "fieldname": "zero_rated_gst",
            "fieldtype": "Check",
            "label": "Zero-rated (GST/HST)",
            "description": "All items in this group are zero-rated for GST/HST (e.g., basic groceries, prescription drugs, exports)",
            "insert_after": "is_group",
        },
    ],
    "Item": [
        {
            "fieldname": "zero_rated_gst",
            "fieldtype": "Check",
            "label": "Zero-rated (GST/HST)",
            "description": "Overrides Item Group setting. Leave unchecked to inherit from Item Group.",
            "insert_after": "item_group",
        },
    ],
}

fixtures = [
    {"dt": "Print Format", "filters": [["name", "=", "CA Tax Invoice"]]},
    {"dt": "Territory", "filters": [["parent_territory", "=", "Canada"]]},
    {"dt": "Sales Taxes and Charges Template", "filters": [["name", "like", "CA %"]]},
    {"dt": "Tax Rule", "filters": [["name", "like", "CA %"]]},
]
```

- [ ] **Step 2: Run existing tests to confirm nothing broken**

```bash
python -m pytest tests/ -v --ignore=tests/test_tax_resolver.py
```

Expected: all existing tests PASS (test_territory.py tests from Task 1 also pass)

- [ ] **Step 3: Commit**

```bash
git add canada_business_compliance/hooks.py
git commit -m "feat: add Customer doc_events and expand fixtures list in hooks.py"
```

---

### Task 7: Rewrite ca_sales_tax.js

**Files:**
- Modify: `canada_business_compliance/public/js/ca_sales_tax.js`

The old JS called `resolve_taxes()` on every trigger (customer change, address change, item changes). The new JS only acts on `shipping_address_name` change: it checks customer exemptions, then sets `frm.territory` from the shipping address province. ERPNext's native Tax Rule engine handles the rest automatically.

- [ ] **Step 1: Replace the entire content of ca_sales_tax.js**

```javascript
// Canada Business Compliance — territory override for Canadian tax
// When shipping address changes, set invoice territory to match the shipping province.
// ERPNext's native Tax Rule engine applies the correct Sales Tax Template automatically.

(function () {
    "use strict";

    const PROVINCE_TERRITORY = {
        AB: "Alberta",
        BC: "British Columbia",
        MB: "Manitoba",
        NB: "New Brunswick",
        NL: "Newfoundland and Labrador",
        NS: "Nova Scotia",
        NT: "Northwest Territories",
        NU: "Nunavut",
        ON: "Ontario",
        PE: "Prince Edward Island",
        QC: "Quebec",
        SK: "Saskatchewan",
        YT: "Yukon",
    };

    function override_territory_from_shipping(frm) {
        if (!frm.doc.shipping_address_name || !frm.doc.customer) return;

        frappe.db.get_value("Customer", frm.doc.customer, ["pst_exempt", "qst_exempt"])
            .then(function (r) {
                const values = (r && r.message) || {};
                if (values.pst_exempt || values.qst_exempt) {
                    frm.clear_table("taxes");
                    frm.refresh_field("taxes");
                    return;
                }

                frappe.db.get_value("Address", frm.doc.shipping_address_name, "state")
                    .then(function (r2) {
                        const state = ((r2 && r2.message && r2.message.state) || "").trim().toUpperCase();
                        const territory = PROVINCE_TERRITORY[state];
                        if (territory && territory !== frm.doc.territory) {
                            frm.set_value("territory", territory);
                        }
                    });
            });
    }

    frappe.ui.form.on("Sales Order", {
        shipping_address_name: override_territory_from_shipping,
    });

    frappe.ui.form.on("Sales Invoice", {
        shipping_address_name: override_territory_from_shipping,
    });
})();
```

- [ ] **Step 2: Commit**

```bash
git add canada_business_compliance/public/js/ca_sales_tax.js
git commit -m "feat: rewrite ca_sales_tax.js — territory override replaces resolve_taxes() call"
```

---

### Task 8: Delete old files

**Files:**
- Delete: `canada_business_compliance/utils/tax_resolver.py`
- Delete: `canada_business_compliance/utils/tax_calculator.py`
- Delete: `tests/test_tax_resolver.py`

- [ ] **Step 1: Delete the three files**

```bash
git rm canada_business_compliance/utils/tax_resolver.py \
       canada_business_compliance/utils/tax_calculator.py \
       tests/test_tax_resolver.py
```

- [ ] **Step 2: Run the full test suite to confirm clean state**

```bash
python -m pytest tests/ -v
```

Expected: all tests PASS, no import errors, no references to deleted modules

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: delete tax_resolver.py, tax_calculator.py, test_tax_resolver.py — replaced by native Tax Rule system"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ 13 Territory records as fixtures (Task 3)
- ✅ 6 Sales Tax Templates as fixtures (Task 4)
- ✅ 13 Tax Rules as fixtures (Task 5) — each matching territory → template per spec table
- ✅ `province_to_territory()` with PROVINCE_TERRITORY map (Task 1)
- ✅ `set_customer_territory()` customer doc_events hook (Task 1)
- ✅ Customer hook registered in hooks.py `doc_events` (Task 6)
- ✅ fixtures list updated with Territory, Sales Taxes and Charges Template, Tax Rule (Task 6)
- ✅ `use_tax_rules` Check field added to CA Tax Settings (Task 2)
- ✅ Toggle on_update disables/enables all `CA %` Tax Rules (Task 2)
- ✅ JS shipping_address_name trigger overrides territory (Task 7)
- ✅ JS exemption bypass: clears taxes if pst_exempt or qst_exempt (Task 7)
- ✅ Quotation excluded from territory override (no shipping_address_name field on Quotation)
- ✅ tax_resolver.py deleted (Task 8)
- ✅ tax_calculator.py deleted (Task 8)
- ✅ test_tax_resolver.py deleted (Task 8)

**Out-of-scope items confirmed not included:**
- Zero-rated item logic (existing custom fields untouched — hooks.py custom_fields preserved)
- Per-territory toggle (global only via use_tax_rules)
- ITC reporting, French/bilingual invoice, address autocorrect
