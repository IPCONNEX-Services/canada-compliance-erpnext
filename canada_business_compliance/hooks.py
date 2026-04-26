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
    "Address":       "canada_business_compliance/public/js/ca_address.js",
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
    "Sales Order Item": [
        {
            "fieldname": "zero_rated_gst",
            "fieldtype": "Check",
            "label": "Zero-rated",
            "fetch_from": "item_code.zero_rated_gst",
            "fetch_if_empty": 0,
            "read_only": 1,
            "insert_after": "item_code",
            "hidden": 1,
        },
    ],
    "Sales Invoice Item": [
        {
            "fieldname": "zero_rated_gst",
            "fieldtype": "Check",
            "label": "Zero-rated",
            "fetch_from": "item_code.zero_rated_gst",
            "fetch_if_empty": 0,
            "read_only": 1,
            "insert_after": "item_code",
            "hidden": 1,
        },
    ],
    "Quotation Item": [
        {
            "fieldname": "zero_rated_gst",
            "fieldtype": "Check",
            "label": "Zero-rated",
            "fetch_from": "item_code.zero_rated_gst",
            "fetch_if_empty": 0,
            "read_only": 1,
            "insert_after": "item_code",
            "hidden": 1,
        },
    ],
}

fixtures = [
    {"dt": "Print Format", "filters": [["name", "=", "CA Tax Invoice"]]},
    {"dt": "Territory", "filters": [["parent_territory", "=", "Canada"]]},
    # Sales Taxes and Charges Template requires company + account_head — create via setup script, not fixture
    {"dt": "Tax Rule", "filters": [["sales_tax_template", "like", "CA %"]]},
]
