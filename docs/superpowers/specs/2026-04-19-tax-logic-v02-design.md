# Canada Business Compliance — Tax Logic v0.2 Design

**Date:** 2026-04-19
**App:** canada-business-compliance
**Status:** Approved

---

## Goal

Upgrade the tax application engine from a simple province-rate lookup to a full compliance-aware resolver that handles: service address fallback, B2B PST/QST exemptions, zero-rated supplies, small supplier rule, and GST/QST registration numbers on invoices.

## Architecture

A single server-side `resolve_taxes()` function owns all tax logic. The JS layer becomes a thin trigger that collects form data and calls the resolver. All rules execute in a fixed order server-side. Custom fields on Customer, Item, and Item Group carry exemption and zero-rating flags. CA Tax Settings gains registration numbers and the small supplier toggle.

**Tech Stack:** Python 3.10+, Frappe v15+, ERPNext v15+, Vanilla JS

---

## Section 1: Data Model

### CA Tax Settings (existing Single DocType — add fields)

| Field | Type | Description |
|-------|------|-------------|
| `is_small_supplier` | Check | When on, disables all tax injection. Annual taxable supplies < $30k CAD. |
| `gst_registration_number` | Data | Company GST/HST number (format: 123456789 RT0001). Printed on invoices. |
| `qst_registration_number` | Data | Company QST number (format: 1234567890 TQ0001). Printed on QC invoices. |

Existing fields kept unchanged: `gst_account`, `hst_account`, `pst_account`, `qst_account`, `apply_to_*`.

### Customer (custom fields via hooks.py `custom_fields`)

| Field | Type | Description |
|-------|------|-------------|
| `pst_exempt` | Check | PST/RST exempt (BC, SK, MB resellers with exemption certificate) |
| `pst_exemption_number` | Data | PST exemption certificate number |
| `qst_exempt` | Check | QST exempt (Quebec resellers buying for resale) |
| `qst_exemption_number` | Data | Customer's QST registration number |

**When PST exemption applies:** BC (PST 7%), Saskatchewan (PST 6%), Manitoba (RST 7%) — resellers with a valid provincial exemption certificate do not pay PST. GST is always charged.

**When QST exemption applies:** Quebec only — businesses registered for QST buying goods/services for resale.

**GST/HST exemption does NOT exist** for resellers — they pay GST/HST and reclaim via Input Tax Credits.

### Item Group (custom field via hooks.py `custom_fields`)

| Field | Type | Description |
|-------|------|-------------|
| `zero_rated_gst` | Check | All items in this group are zero-rated for GST/HST (e.g., basic groceries, prescription drugs, exports) |

### Item (custom field via hooks.py `custom_fields`)

| Field | Type | Description |
|-------|------|-------------|
| `zero_rated_gst` | Check | Override Item Group setting. If checked, this item is zero-rated for GST/HST. |

**Zero-rated resolution:** Item-level wins. If Item.zero_rated_gst is unchecked but Item Group.zero_rated_gst is checked, the item is zero-rated. Zero-rating applies to GST/HST only — PST/QST zero-rating follows separate provincial rules not covered in this version.

**Zero-rated invoice rule:** GST/HST row is removed only if ALL items on the document are zero-rated. If even one item is taxable, GST/HST applies to the full invoice (ERPNext tax rows apply to net total, not per-item). If the items list is empty (document has no items yet), zero-rating check is skipped and GST/HST applies normally.

---

## Section 2: Tax Resolver

### New file: `canada_business_compliance/utils/tax_resolver.py`

```python
@frappe.whitelist()
def resolve_taxes(doctype, shipping_address, customer_address, customer, items):
    ...
```

**Resolution order (strict):**

```
1. SMALL SUPPLIER
   CA Tax Settings.is_small_supplier == True → return []

2. ADDRESS FALLBACK
   province = province_from_address(shipping_address)
              or province_from_address(customer_address)
   if no province → return []

3. PROVINCE LOOKUP
   tax_rows = get_tax_rows(province)  # existing PROVINCE_TAXES dict

4. PST/QST EXEMPTION
   if Customer.pst_exempt and province in {BC, SK, MB}:
       remove PST row
   if Customer.qst_exempt and province == QC:
       remove QST row

5. ZERO-RATED ITEMS
   if all items are zero_rated_gst (Item override > Item Group):
       remove GST/HST row

6. ACCOUNT HEAD INJECTION
   fetch CA Tax Settings accounts
   attach account_head to each row
   flag rows with missing account as needs_configuration=True

7. RETURN tax rows
```

### Backward compatibility

`get_province_taxes(province_code)` in `tax_calculator.py` is kept as a thin wrapper calling `resolve_taxes` with no customer/items context. No existing integrations break.

### Helper: `province_from_address(address_name)`

```python
def province_from_address(address_name):
    if not address_name:
        return None
    state = frappe.db.get_value("Address", address_name, "state")
    return state.upper().strip() if state else None
```

### Helper: `is_item_zero_rated(item_code)`

```python
def is_item_zero_rated(item_code):
    # Item-level wins over Item Group
    item = frappe.get_cached_doc("Item", item_code)
    if item.get("zero_rated_gst") is not None:
        return bool(item.zero_rated_gst)
    item_group = frappe.get_cached_doc("Item Group", item.item_group)
    return bool(item_group.get("zero_rated_gst"))
```

---

## Section 3: JavaScript

### Updated: `canada_business_compliance/public/js/ca_sales_tax.js`

**Trigger events per doctype:**

| Doctype | Triggers |
|---------|---------|
| Sales Order | `shipping_address_name`, `customer_address`, `items` (on_change) |
| Quotation | `customer_address`, `items` (on_change) |
| Sales Invoice | `shipping_address_name`, `customer_address`, `items` (on_change) |

**Single helper function:**

```javascript
function resolve_and_apply(frm) {
    // Debounced 300ms — prevents firing on rapid changes
    frappe.call({
        method: "canada_business_compliance.utils.tax_resolver.resolve_taxes",
        args: {
            doctype: frm.doctype,
            shipping_address: frm.doc.shipping_address_name || "",
            customer_address: frm.doc.customer_address || "",
            customer: frm.doc.customer || "",
            items: (frm.doc.items || []).map(r => r.item_code).filter(Boolean),
        },
        callback(r) {
            const rows = r.message || [];
            if (!rows.length) {
                frm.clear_table("taxes");
                frm.refresh_field("taxes");
                return;
            }
            const missing = rows.filter(row => row.needs_configuration);
            if (missing.length) {
                frappe.msgprint({
                    title: "CA Tax Settings",
                    message: `Tax accounts not configured for: ${missing.map(r => r.description).join(", ")}`,
                    indicator: "orange",
                });
                return;
            }
            frm.clear_table("taxes");
            rows.forEach(row => frm.add_child("taxes", row));
            frm.refresh_field("taxes");
            frappe.show_alert({ message: "Canadian tax applied", indicator: "green" }, 3);
        },
    });
}
```

All triggers call `resolve_and_apply(frm)`. Debounce wrapper applied at registration time.

---

## Section 4: Print Format

**Name:** `CA Tax Invoice`
**DocType:** Sales Invoice
**Delivery:** JSON fixture shipped with the app, applied on `bench migrate`

**Footer addition (Jinja):**

```html
{%- set ca = frappe.get_single("CA Tax Settings") -%}
{%- if ca.gst_registration_number or ca.qst_registration_number %}
<div class="ca-tax-registration">
  {%- if ca.gst_registration_number %}
  <span>GST/HST Registration No.: {{ ca.gst_registration_number }}</span>
  {%- endif %}
  {%- if ca.qst_registration_number %}
  <span>QST Registration No.: {{ ca.qst_registration_number }}</span>
  {%- endif %}
</div>
{%- endif %}
```

Numbers only print if configured. No output if both fields are empty.

**Scope:** Sales Invoice only. Sales Orders and Quotations do not require registration numbers legally.

---

## Files Changed

| Action | File |
|--------|------|
| Modify | `canada_business_compliance/utils/tax_calculator.py` — keep `get_province_taxes()`, add `province_from_address()`, `is_item_zero_rated()` |
| Create | `canada_business_compliance/utils/tax_resolver.py` — `resolve_taxes()` |
| Modify | `canada_business_compliance/public/js/ca_sales_tax.js` — `resolve_and_apply()`, new triggers |
| Modify | `canada_business_compliance/ca_sales_tax/doctype/ca_tax_settings/ca_tax_settings.json` — add 3 fields |
| Modify | `canada_business_compliance/hooks.py` — add `custom_fields` for Customer, Item, Item Group |
| Create | `canada_business_compliance/ca_sales_tax/print_format/ca_tax_invoice/ca_tax_invoice.json` — print format fixture |
| Modify | `canada_business_compliance/hooks.py` — register `fixtures` for print format |
| Bump | `canada_business_compliance/__init__.py` + `hooks.py` → version `0.2.0` |

---

## Out of Scope (This Version)

- Per-item PST/QST zero-rating (PST exempt categories vary by province — future)
- Address auto-correct/suggest (Group B)
- ITC report (Group C)
- French/bilingual print format (Group D)
- Payroll, T4, HST filing (future modules)
