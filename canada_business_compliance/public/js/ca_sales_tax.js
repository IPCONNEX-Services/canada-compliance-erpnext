// Canada Business Compliance — resolve and apply Canadian sales tax
// Server-side resolve_taxes() handles: address fallback, exemptions, zero-rated items

(function () {
    "use strict";

    function debounce(fn, delay) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function resolve_and_apply(frm) {
        if (!frm.doc.customer) return;

        frappe.call({
            method: "canada_business_compliance.utils.tax_resolver.resolve_taxes",
            args: {
                doctype: frm.doctype,
                shipping_address: frm.doc.shipping_address_name || "",
                customer_address: frm.doc.customer_address || "",
                customer: frm.doc.customer || "",
                items: JSON.stringify(
                    (frm.doc.items || []).map(r => r.item_code).filter(Boolean)
                ),
            },
            callback(r) {
                const rows = r.message || [];

                if (!rows.length) {
                    frm.clear_table("taxes");
                    frm.refresh_field("taxes");
                    return;
                }

                const unconfigured = rows.filter(row => !row.account_head);
                if (unconfigured.length) {
                    frappe.msgprint({
                        title: __("CA Tax Settings"),
                        message: __(
                            "Tax accounts not configured for: {0}. Go to CA Tax Settings.",
                            [unconfigured.map(r => r.description).join(", ")]
                        ),
                        indicator: "orange",
                    });
                    return;
                }

                frm.clear_table("taxes");
                rows.forEach(row => frm.add_child("taxes", row));
                frm.refresh_field("taxes");
                frappe.show_alert({ message: __("Canadian tax applied"), indicator: "green" }, 3);
            },
        });
    }

    const resolve_debounced = debounce(resolve_and_apply, 300);

    const ADDRESS_TRIGGERS = {
        "Sales Order": ["shipping_address_name", "customer_address"],
        "Quotation": ["customer_address"],
        "Sales Invoice": ["shipping_address_name", "customer_address"],
    };

    Object.entries(ADDRESS_TRIGGERS).forEach(([doctype, addressFields]) => {
        const handlers = {
            customer: resolve_debounced,
            // items table: re-resolve when items are added, removed, or item_code changes
            items_add: resolve_debounced,
            items_remove: resolve_debounced,
            items_item_code: resolve_debounced,
        };
        addressFields.forEach(field => {
            handlers[field] = resolve_debounced;
        });
        frappe.ui.form.on(doctype, handlers);
    });
})();
