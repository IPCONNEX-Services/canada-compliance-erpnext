app_name = "canada_business_compliance"
app_title = "Canada Business Compliance"
app_publisher = "IPCONNEX"
app_description = "Canadian business compliance for Frappe/ERPNext — sales tax, payroll, and more"
app_email = "dev@ipconnex.com"
app_license = "MIT"
app_version = "0.1.0"

doctype_js = {
    "Sales Order":   "canada_business_compliance/public/js/ca_sales_tax.js",
    "Quotation":     "canada_business_compliance/public/js/ca_sales_tax.js",
    "Sales Invoice": "canada_business_compliance/public/js/ca_sales_tax.js",
}
