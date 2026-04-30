# Handoff — canada-business-compliance

**Date:** 2026-04-30
**Branch:** main (all changes pushed)

---

## What was done this session

### 1. CA Company Tax Config — creation was broken (root cause found + fixed)

Three separate fixes landed before the actual root cause was identified:

| Commit | What it did |
|---|---|
| `47bb33d` | Moved `get_query` from JSON to `frm.set_query()` in JS; fixed print format; added validate duplicate error |
| `0287362` | Added patch calling `frappe.reload_doc(..., force=True)` — didn't fix it |
| `c369e1b` | Added patch writing directly to `tabDocPerm` — didn't fix it |
| **`b328209`** | **The real fix: `"in_create": 0` in `ca_company_tax_config.json`** |

**Root cause:** `in_create: 1` in the DocType JSON causes Frappe to put the doctype into `boot.user.in_create` instead of `boot.user.can_create` at boot time. The list-view New button checks `can_create` — so it never rendered even though server-side permissions were correct. Ref: `frappe/utils/user.py` ~L133.

The two permission patches (`fix_company_config_permissions`, `set_company_config_perms_direct`) are harmless but were chasing the wrong problem. They can be removed in a future cleanup.

### 2. Print format fixed

`ca_tax_invoice.json` was reading registration numbers from the old `CA Tax Settings` single doctype. Now reads from `CA Company Tax Config` filtered by `doc.company`, with a null guard.

### 3. App icon added

- Generated in Canva: red maple leaf + white checkmark, IPCONNEX logo at bottom
- Saved to `canada_business_compliance/public/logo.png` (512×512 PNG)
- This is the standard path Frappe Cloud looks for marketplace icons

---

## Current state

- **CA Tax Settings** (Single DocType) — still exists, now legacy/unused. All active tax logic reads from CA Company Tax Config. Can be deprecated or hidden in a future release.
- **CA Company Tax Config** — fully working. Migration patch auto-creates a record for the default company from CA Tax Settings data on `bench migrate`. Additional companies are added manually via the list view.
- **Tax resolver** (`utils/tax_resolver.py`) — reads from CA Company Tax Config only
- **Setup taxes** (`utils/setup_taxes.py`) — reads from CA Company Tax Config only; triggered via "Generate Tax Templates & Rules" button on the config form

---

## Next steps / known gaps

- **Deprecate CA Tax Settings** — it's no longer read by any active code. Consider hiding it from the module or marking it deprecated in a v0.4 release.
- **Remove redundant patches** — `fix_company_config_permissions` and `set_company_config_perms_direct` can be cleaned up; they're in patches.txt and will run harmlessly but are noise.
- **Test multi-company flow end-to-end** — create a second company, add a CA Company Tax Config for it, generate tax templates, create a Sales Invoice and verify correct tax is applied.
- **Frappe Cloud marketplace listing** — icon is ready at `public/logo.png`. Still needs a marketplace description/README update if submitting to the marketplace.

---

## Key files

| File | Purpose |
|---|---|
| `ca_sales_tax/doctype/ca_company_tax_config/` | Per-company tax config — the main settings doc |
| `ca_sales_tax/doctype/ca_tax_settings/` | Legacy single-company settings (unused by active code) |
| `utils/tax_resolver.py` | Auto-sets taxes on Sales Invoice/Order/Quotation before insert |
| `utils/setup_taxes.py` | Generates Sales Tax Templates + Tax Rules per company |
| `utils/territory.py` | Sets customer territory from address province |
| `public/js/ca_sales_tax.js` | Client-side tax injection for Sales Order/Quotation/Invoice |
| `ca_sales_tax/print_format/ca_tax_invoice/` | CA Tax Invoice print format |
| `patches/v0_3_0/migrate_settings_to_company_config.py` | Migrates CA Tax Settings → CA Company Tax Config on first v0.3 install |
| `public/logo.png` | Marketplace icon (512×512) |
