# Canada Business Compliance

A Frappe v16 / ERPNext app for Canadian business compliance — automatic sales tax, multi-company support, and full coverage of all 13 provinces and territories.

---

## Features

- Auto-applies GST / HST / PST / QST on Sales Orders, Quotations, and Sales Invoices
- Per-company configuration — each ERPNext company gets its own tax config, accounts, and registration numbers
- All 13 provinces and territories supported
- B2B PST/QST exemptions (resellers)
- Zero-rated GST/HST items and item groups
- Small supplier mode (under $30,000 CAD annual revenue)
- CA Tax Invoice print format with registration numbers in the footer
- Auto-creates missing tax accounts in your Chart of Accounts

---

## Province Tax Rates (2025)

| Province / Territory | GST | HST | PST / RST | QST | Total |
|---|---|---|---|---|---|
| AB — Alberta | 5% | — | — | — | 5% |
| BC — British Columbia | 5% | — | 7% | — | 12% |
| MB — Manitoba | 5% | — | 7% RST | — | 12% |
| NB — New Brunswick | — | 15% | — | — | 15% |
| NL — Newfoundland | — | 15% | — | — | 15% |
| NS — Nova Scotia | — | 15% | — | — | 15% |
| NT — Northwest Territories | 5% | — | — | — | 5% |
| NU — Nunavut | 5% | — | — | — | 5% |
| ON — Ontario | — | 13% | — | — | 13% |
| PE — Prince Edward Island | — | 15% | — | — | 15% |
| QC — Quebec | 5% | — | — | 9.975% | 14.975% |
| SK — Saskatchewan | 5% | — | 6% | — | 11% |
| YT — Yukon | 5% | — | — | — | 5% |

---

## Installation

```bash
cd /home/frappe/frappe-bench
bench get-app https://github.com/IPCONNEX-Services/canada-compliance-erpnext.git
bench --site your-site.com install-app canada_business_compliance
bench --site your-site.com migrate
bench restart
```

---

## Setup

### 1 — Create a CA Company Tax Config

Go to **CA Company Tax Config → New** and select your company.

- Pick the **Company Province / Territory** (where the company is registered)
- Set **Collects Canadian Sales Tax** ✓
- Save

### 2 — Create Tax Accounts

Click **Setup → Create Tax Accounts**.

The app will create any missing tax payable accounts (`GST Payable`, `HST Payable`, `PST Payable`, `QST Payable`) under your company's Chart of Accounts (`Duties and Taxes`) and populate the account fields automatically.

> If your Chart of Accounts doesn't have a `Duties and Taxes` parent account, create it first or the button will tell you exactly what's missing.

### 3 — Generate Tax Templates & Rules

Click **Setup → Generate Tax Templates & Rules**.

This creates one **Sales Taxes and Charges Template** and one **Tax Rule** per province, scoped to your company. ERPNext will automatically apply the correct template based on the customer's billing province.

### 4 — Add Registration Numbers

In the **Registration Numbers** section, fill in:

| Field | Required when |
|---|---|
| GST/HST Registration No. | Always (if registered for GST/HST) |
| QST Registration No. | Operating in Quebec |
| BC PST Registration No. | Collecting BC PST |
| SK PST Business ID | Collecting Saskatchewan PST |
| MB RST Number | Collecting Manitoba RST |

These print automatically in the footer of the **CA Tax Invoice** print format.

---

## Multi-Company

Each company needs its own **CA Company Tax Config** record. Repeat the three setup steps above for each company. Tax Templates and Tax Rules are namespaced by company abbreviation (`CA GST Only - ABC`), so companies never share templates.

---

## Advanced: Per-Province PST Accounts

> **This is off by default.** Most businesses do not need this.

If your company has **physical branches in multiple PST provinces** (BC, SK, and/or MB) and files **separate PST returns** to each provincial government, you may want a dedicated GL account per province so the balance sheet directly shows what is owed to each government without filtering reports.

To enable:

1. Open **CA Company Tax Config** for the company
2. Expand the **Advanced: Per-Province PST Accounts** section at the bottom of Tax Accounts
3. Check **Use separate PST account per province**
4. Three new account fields appear: `BC PST Account`, `SK PST Account`, `MB RST Account`
5. Click **Setup → Create Tax Accounts** — creates `BC PST Payable`, `SK PST Payable`, `MB RST Payable` and links them
6. Click **Setup → Generate Tax Templates & Rules** — creates province-specific templates (`CA GST + BC PST 7%`, `CA GST + SK PST 6%`, `CA GST + MB RST 7%`) each pointing to its own account

> **When is this needed?** Only when a single ERPNext company entity has nexus in multiple PST provinces simultaneously and your accountant wants the balance sheet to separate what's owed to BC Ministry of Finance vs Saskatchewan Finance vs Manitoba Finance. If each provincial branch is its own ERPNext company, use separate CA Company Tax Config records instead — the standard setup handles it cleanly.

---

## How Automatic Tax Application Works

On save of a Sales Order, Quotation, or Sales Invoice:

1. The app reads the customer's billing address state (province code)
2. Looks up the matching Tax Rule for that province and company
3. Applies the Sales Taxes and Charges Template to the document

Address takes priority over the customer's Territory field. If neither is set, no tax is applied.

---

## B2B Exemptions

On the **Customer** record, set:

- **PST/RST Exempt** — strips PST rows from BC, SK, MB invoices (for resellers with a PST exemption certificate)
- **QST Exempt** — strips QST rows for Quebec resellers

GST/HST is always preserved (exemptions are handled separately via zero-rating).

---

## Zero-Rated Items

Set **Zero-rated (GST/HST)** on an **Item** or **Item Group**. If all items on a document are zero-rated, all GST/HST rows are cleared. A warning is shown for mixed documents (some zero-rated, some taxable).

---

## License

MIT
