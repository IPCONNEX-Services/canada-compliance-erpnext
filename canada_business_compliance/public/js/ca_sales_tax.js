// Canada Business Compliance — territory override for Canadian tax
// When shipping address changes, set invoice territory to match the shipping province.
// ERPNext's native Tax Rule engine applies the correct Sales Tax Template automatically.

(function () {
    "use strict";

    const PROVINCE_TERRITORY = {
        AB: "Alberta",
        BC: "British Columbia",
        MB: "Manitoba",
        NB: "New Brunswick",
        NL: "Newfoundland and Labrador",
        NS: "Nova Scotia",
        NT: "Northwest Territories",
        NU: "Nunavut",
        ON: "Ontario",
        PE: "Prince Edward Island",
        QC: "Quebec",
        SK: "Saskatchewan",
        YT: "Yukon",
    };

    function override_territory_from_shipping(frm) {
        if (!frm.doc.shipping_address_name || !frm.doc.customer) return;

        frappe.db.get_value("Customer", frm.doc.customer, ["pst_exempt", "qst_exempt"])
            .then(function (r) {
                const values = (r && r.message) || {};
                if (values.pst_exempt || values.qst_exempt) {
                    frm.clear_table("taxes");
                    frm.refresh_field("taxes");
                    return;
                }

                frappe.db.get_value("Address", frm.doc.shipping_address_name, "state")
                    .then(function (r2) {
                        const state = ((r2 && r2.message && r2.message.state) || "").trim().toUpperCase();
                        const territory = PROVINCE_TERRITORY[state];
                        if (territory && territory !== frm.doc.territory) {
                            frm.set_value("territory", territory);
                        }
                    });
            });
    }

    frappe.ui.form.on("Sales Order", {
        shipping_address_name: override_territory_from_shipping,
    });

    frappe.ui.form.on("Sales Invoice", {
        shipping_address_name: override_territory_from_shipping,
    });
})();
