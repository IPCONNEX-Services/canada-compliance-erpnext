# Territories & Tax Rules — Design Spec

**Date:** 2026-04-21
**Status:** Approved
**Scope:** Replace custom tax injection with ERPNext native Territory → Tax Rule pipeline

---

## Problem

The app currently uses a custom `resolve_taxes()` function that injects tax rows by reading a static `PROVINCE_TAXES` dict. This bypasses ERPNext's native tax framework, making territory-based reporting, Tax Rule management, and standard ERPNext tax tooling unavailable.

---

## Goals

- All 13 Canadian provinces and territories exist as ERPNext Territory records (installed as fixtures)
- Each territory has a matching Tax Rule pointing to the correct Sales Tax Template
- Customer territory is auto-set from their primary address province
- Transaction territory is overridden per-invoice if the shipping address is in a different province
- A global toggle in CA Tax Settings enables/disables all Tax Rules at once
- Customers with PST or QST exemptions bypass Tax Rules entirely — user fills taxes manually

---

## Fixtures

Three sets of records shipped as fixtures, installed on `bench migrate`.

### Territories (13)

All parented under "Canada" territory.

| Territory Name | Province Code |
|---|---|
| Alberta | AB |
| British Columbia | BC |
| Manitoba | MB |
| New Brunswick | NB |
| Newfoundland and Labrador | NL |
| Northwest Territories | NT |
| Nova Scotia | NS |
| Nunavut | NU |
| Ontario | ON |
| Prince Edward Island | PE |
| Quebec | QC |
| Saskatchewan | SK |
| Yukon | YT |

### Sales Tax Templates (6)

One per unique rate combination. Template rows use the account fields from CA Tax Settings at install time; users configure accounts separately.

| Template Name | Tax Rows |
|---|---|
| CA GST Only | GST 5% |
| CA HST 13% | HST 13% |
| CA HST 15% | HST 15% |
| CA GST + PST 7% | GST 5%, PST 7% |
| CA GST + PST 6% | GST 5%, PST 6% |
| CA GST + QST | GST 5%, QST 9.975% |

### Tax Rules (13)

One per territory. All set `tax_type = "Sales"` and `priority = 1`.

| Territory | Template |
|---|---|
| Alberta | CA GST Only |
| Northwest Territories | CA GST Only |
| Nunavut | CA GST Only |
| Yukon | CA GST Only |
| Ontario | CA HST 13% |
| New Brunswick | CA HST 15% |
| Newfoundland and Labrador | CA HST 15% |
| Nova Scotia | CA HST 15% |
| Prince Edward Island | CA HST 15% |
| British Columbia | CA GST + PST 7% |
| Manitoba | CA GST + PST 7% |
| Saskatchewan | CA GST + PST 6% |
| Quebec | CA GST + QST |

---

## Territory Assignment

### Province → Territory Map

New module `canada_business_compliance/utils/territory.py`:

```python
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

def province_to_territory(province_code: str) -> str | None:
    """Map a province code (e.g. 'ON') to an ERPNext Territory name."""
    return PROVINCE_TERRITORY.get((province_code or "").strip().upper())
```

### Customer Level (persistent default)

A `doc_events` hook on Customer fires on `after_insert` and `on_update`. It reads the customer's primary address `state` field, maps it to a Territory name via `province_to_territory()`, and saves `Customer.territory` if it changed. Runs silently.

```python
# hooks.py
doc_events = {
    "Customer": {
        "after_insert": "canada_business_compliance.utils.territory.set_customer_territory",
        "on_update": "canada_business_compliance.utils.territory.set_customer_territory",
    }
}
```

### Transaction Level (per-invoice override)

In `ca_sales_tax.js`, when `shipping_address_name` changes:

1. Fetch the address `state` from the server
2. Map to territory name
3. If territory differs from `frm.doc.territory` → `frm.set_value("territory", territory_name)`
4. ERPNext's native Tax Rule system applies the matching template automatically

Before doing any of this, check exemptions:

```javascript
// If customer is exempt, clear taxes and skip
if (frm.doc.pst_exempt || frm.doc.qst_exempt) {
    frm.clear_table("taxes");
    frm.refresh_field("taxes");
    return;
}
```

---

## Toggle

Add `use_tax_rules` Check field (default: 1) to `CA Tax Settings`.

On `CA Tax Settings.on_update`: if `use_tax_rules` changed, loop all Tax Rules with name starting "CA " and set `disabled = 0` or `disabled = 1` accordingly.

```python
def on_update(self):
    disabled = 0 if self.use_tax_rules else 1
    for rule in frappe.get_all("Tax Rule", filters={"tax_type": "Sales", "disabled": ("!=", disabled)}):
        frappe.db.set_value("Tax Rule", rule.name, "disabled", disabled)
```

The toggle does not delete rules — it only enables/disables them. Re-enabling restores the full pipeline.

---

## Migration from Old System

| Component | Action |
|---|---|
| `utils/tax_resolver.py` | Delete |
| `utils/tax_calculator.py` | Delete |
| `utils/territory.py` | New — map + `set_customer_territory()` |
| `ca_sales_tax.js` | Update — replace `resolve_taxes()` call with territory override |
| `CA Tax Settings` DocType | Add `use_tax_rules` Check field |
| `CA Tax Settings` Python class | Add `on_update` hook for toggle |
| `hooks.py` | Add `doc_events` for Customer; update fixtures list |
| Custom fields (Customer, Item, Item Group) | Keep unchanged |
| `tests/test_tax_resolver.py` | Delete (tests deleted module) |
| `tests/test_territory.py` | New — test province_to_territory, set_customer_territory |

### Fixtures update

`hooks.py` fixtures list gains three new entries:

```python
fixtures = [
    {"dt": "Print Format", "filters": [["name", "=", "CA Tax Invoice"]]},
    {"dt": "Territory", "filters": [["parent_territory", "=", "Canada"]]},
    {"dt": "Sales Taxes and Charges Template", "filters": [["name", "like", "CA %"]]},
    {"dt": "Tax Rule", "filters": [["name", "like", "CA %"]]},
]
```

---

## Error Handling

- Province code not in `PROVINCE_TERRITORY` → `province_to_territory()` returns `None` → customer territory unchanged, transaction territory unchanged → no Tax Rule applied → user fills taxes manually
- Address has no `state` → same fallback
- Tax Rule toggle fails → log error, surface in Frappe error log

---

## Testing

- `test_territory.py` — unit tests for `province_to_territory()` (all 13 codes, unknown code, empty string, lowercase input) and `set_customer_territory()` (customer with address, customer without address)
- Fixture JSON files validated by their structure (no runtime test needed)
- JS exemption bypass — manual verification (no automated JS tests)
- Old tests in `test_tax_resolver.py` — deleted alongside the deleted module

---

## Out of Scope

- Zero-rated item logic (remains as-is on the existing custom fields — not wired into Tax Rules)
- Address auto-correct / postal code validation (separate feature)
- ITC reporting
- French/bilingual invoice
- Per-territory toggle (global toggle only)
