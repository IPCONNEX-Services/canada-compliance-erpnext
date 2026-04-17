// Canada Business Compliance — Auto-apply Canadian sales tax on address change

(function () {
    const ADDRESS_FIELDS = {
        "Sales Order":   ["shipping_address_name", "customer_address"],
        "Quotation":     ["customer_address"],
        "Sales Invoice": ["shipping_address_name", "customer_address"],
    };

    function apply_ca_tax(frm, address_name) {
        if (!address_name) return;

        frappe.db.get_value("Address", address_name, "state").then(({ message }) => {
            const province = message && message.state;
            if (!province) return;

            frappe.call({
                method: "canada_business_compliance.utils.tax_calculator.get_province_taxes",
                args: { province_code: province },
                callback(r) {
                    if (!r.message || !r.message.length) return;

                    // Warn if any tax account is unconfigured
                    const missing = r.message.filter(row => !row.account_head);
                    if (missing.length) {
                        frappe.msgprint({
                            title: "CA Tax Settings",
                            message: `Tax accounts not configured for: ${missing.map(r => r.description).join(", ")}. Go to CA Tax Settings to set them up.`,
                            indicator: "orange",
                        });
                        return;
                    }

                    frm.clear_table("taxes");
                    r.message.forEach(row => frm.add_child("taxes", row));
                    frm.refresh_field("taxes");
                    frappe.show_alert({
                        message: `Canadian tax applied for ${province}`,
                        indicator: "green",
                    }, 3);
                },
            });
        });
    }

    Object.entries(ADDRESS_FIELDS).forEach(([doctype, fields]) => {
        const handlers = {};
        fields.forEach(field => {
            handlers[field] = function (frm) {
                apply_ca_tax(frm, frm.doc[field]);
            };
        });
        frappe.ui.form.on(doctype, handlers);
    });
})();
