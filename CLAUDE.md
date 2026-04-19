# Canada Business Compliance

## Purpose
Auto-populates Canadian sales tax (GST, HST, PST, QST) on ERPNext Sales Orders,
Quotations, and Sales Invoices based on the customer's shipping province.
Published on the Frappe Cloud marketplace. Version: 0.1.0.

## Paid Tier
FREE — all features included at no cost.

## Tech Stack
- Frappe v15+ / ERPNext v15+
- Python 3.10+
- No external APIs (static tax rate table)

## Key Files
- `canada_business_compliance/hooks.py` — registers client JS on Sales Order, Quotation, Sales Invoice
- `canada_business_compliance/public/js/ca_sales_tax.js` — client-side province selector and tax injection
- `canada_business_compliance/ca_sales_tax/` — DocType definitions for tax configuration
- `canada_business_compliance/utils/` — shared helpers

## Common Tasks

### Add or update a tax rate
1. Update the rate table in the appropriate DocType or fixture JSON
2. Write a patch if existing data needs migration (see Frappe skill: Patch Patterns)
3. Register patch in `canada_business_compliance/patches.txt`
4. Bump version in `pyproject.toml`

### Add a new province or territory
1. Add the province code and rates to the tax configuration DocType
2. Update `ca_sales_tax.js` if the province selector needs a new option
3. Write + register a patch if DocType data ships as fixtures

### Add a new document type (e.g., Purchase Order)
1. Add entry to `doctype_js` in `hooks.py`:
   `"Purchase Order": "canada_business_compliance/public/js/ca_sales_tax.js"`
2. Ensure the JS handles the new doctype's field names

### Cut a release
See Frappe/ERPNext skill → Release Procedure.

## Gotchas
- Tax rates change federally and provincially — when rates change, a data patch is required; do not hardcode rates in JS
- `pyproject.toml` uses `flit_core` build backend (not setuptools) — version is set under `[project]` → `dynamic = ["version"]` resolved from `hooks.py`
- Frappe dependency declared as `frappe >= 16.0.0` in pyproject.toml but app targets v15+; update this if v15 compatibility is confirmed required
- Client JS runs on form load — test on each supported doctype after any JS change

## Secrets
No external API keys required. No secrets needed.
