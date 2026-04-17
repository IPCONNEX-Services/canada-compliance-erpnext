# Canada Business Compliance

A Frappe v16 app for Canadian business compliance. Starting with automatic sales tax — expanding to payroll and other Canadian compliance requirements.

## Features

### v0.1 — Canadian Sales Tax
- Auto-populates GST/HST/PST/QST on Sales Orders, Quotations, and Sales Invoices
- Triggers on shipping address change (client-side, zero friction)
- All 13 provinces and territories supported
- Configurable tax accounts via **CA Tax Settings**

### Planned
- `ca_payroll` — CPP, EI, provincial income tax withholding
- `ca_t4` — T4 slip generation
- `ca_hst_filing` — HST return calculation and export

---

## Province Tax Rates (2025)

| Province | GST | HST | PST / RST | QST | Total |
|----------|-----|-----|-----------|-----|-------|
| AB | 5% | — | — | — | 5% |
| BC | 5% | — | 7% | — | 12% |
| MB | 5% | — | 7% | — | 12% |
| NB | — | 15% | — | — | 15% |
| NL | — | 15% | — | — | 15% |
| NS | — | 15% | — | — | 15% |
| NT | 5% | — | — | — | 5% |
| NU | 5% | — | — | — | 5% |
| ON | — | 13% | — | — | 13% |
| PE | — | 15% | — | — | 15% |
| QC | 5% | — | — | 9.975% | 14.975% |
| SK | 5% | — | 6% | — | 11% |
| YT | 5% | — | — | — | 5% |

---

## Installation

```bash
cd /home/frappe/frappe-bench
bench get-app https://github.com/ipconnex/canada-business-compliance.git
bench --site your-site.com install-app canada_business_compliance
bench --site your-site.com migrate
bench restart
```

## Configuration

1. Go to **CA Tax Settings** in ERPNext
2. Set the Account for each tax type (GST, HST, PST, QST) — these should be liability accounts in your Chart of Accounts
3. Choose which document types to auto-apply tax on

## How It Works

When you set or change a shipping address on a Sales Order (or Quotation / Sales Invoice), the app reads the province from the address, looks up the applicable rates, and populates the **Taxes and Charges** table automatically.

If a tax account is not configured in CA Tax Settings, an orange warning is shown and taxes are not applied until the configuration is complete.

---

## License

MIT
