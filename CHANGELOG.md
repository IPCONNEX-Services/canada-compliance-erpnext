# Changelog

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
