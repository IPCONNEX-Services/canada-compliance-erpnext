# Changelog

## v0.3.2 — 2026-09-29
### Changed
- Purchase tax template now follows the **place of supply** (where the goods are delivered),
  not the supplier's province. Order: (a) drop-ship — PO shipping address / linked Sales Order
  address / customer address; (b) doc `shipping_address`; (c) company billing address on the doc,
  then the company's default address; (d) fallback to the supplier's province (old behaviour)
  only when no destination is known. A destination outside Canada sets no template.
- Only suppliers that resolve to a Canadian province get a template (unchanged for foreign
  suppliers); the destination only decides which Canadian template applies.
- Auto-set now also skips docs that already carry tax rows without a template (manual rows
  were previously replaced) and non-draft docs. Also hooked on Purchase Receipt.
- `Supplier.territory` is read only when the field exists (standard ERPNext has none).
- Purchase tax rows now carry `category` / `add_deduct_tax` / `cost_center` from the template;
  before, any Purchase Order/Invoice whose template was auto-set failed insert with a
  MandatoryError (masked until 0.3.1 because the purchase template names did not resolve).
### Added
- Read-only `ca_tax_basis` field on Purchase Order / Receipt / Invoice records the basis,
  e.g. "Destination QC (company address …)" or "Supplier fallback ON". Created by patch
  `v0_3_2.add_ca_tax_basis_field` and on install (the `custom_fields` dict in hooks.py is not
  synced by Frappe).

## v0.3.1 — 2026-09-29
### Fixed
- Nova Scotia HST is 14% (cut from 15% effective 2025-04-01). NS now maps to a new
  `CA HST 14%` sales/purchase template; NB, NL, PE stay on `CA HST 15%`. Fallback rate for NS is 14.
- Patch `v0_3_1.ns_hst_14` creates `CA HST 14% - <abbr>` from each company's `CA HST 15%`
  template (same account head) and repoints NS Tax Rules. Idempotent; never touches submitted documents.

## v0.2.0 — 2026-04-19
### Added
- Address fallback: billing address used for tax when no shipping address (services)
- B2B PST exemption: Customer flag skips PST in BC, SK, MB for registered resellers
- B2B QST exemption: Customer flag skips QST in QC for registered resellers
- Zero-rated supplies: Item Group and Item `zero_rated_gst` flag removes GST/HST when all items qualify
- Small supplier rule: CA Tax Settings toggle disables all tax injection (under $30k CAD)
- GST/HST registration number field in CA Tax Settings, printed on CA Tax Invoice
- QST registration number field in CA Tax Settings, printed on CA Tax Invoice
- CA Tax Invoice: print format for Sales Invoice with compliance footer
- Custom fields: Customer (PST/QST exemption), Item Group and Item (zero-rated flag)
- Items table triggers: tax recalculates when items are added/removed/changed
- 300ms debounce on all tax resolution triggers

### Changed
- Tax resolution moved to server-side `resolve_taxes()` — JS is now a thin trigger only
- `get_province_taxes()` kept as backward-compatible wrapper, now respects small supplier flag

## v0.1.0 — 2026-04-19
### Added
- Auto-populate GST, HST, PST, QST on Sales Orders, Quotations, and Sales Invoices based on shipping province
- Client-side province selector with live tax injection
- Support for all Canadian provinces and territories
