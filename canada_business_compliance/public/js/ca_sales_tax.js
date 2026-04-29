// Canada Business Compliance — Canadian tax injection for Sales Order, Quotation, Sales Invoice.
// Per-company config loaded from CA Company Tax Config; falls back silently if no config exists.

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

    const PST_PROVINCES = new Set(["BC", "SK", "MB"]);

    // Cache is keyed per company — reset on refresh or company change
    let _settings_promise = null;
    let _settings_company = null;

    function get_settings(frm) {
        var company = frm.doc.company;
        if (company !== _settings_company) {
            _settings_promise = null;
            _settings_company = company;
        }
        if (!_settings_promise) {
            _settings_promise = frappe.call({
                method: "canada_business_compliance.utils.tax_resolver.get_company_tax_config",
                args: { company: company },
            }).then(function (r) {
                return r.message || null;
            });
        }
        return _settings_promise;
    }

    function territory_to_province(territory) {
        for (var code in PROVINCE_TERRITORY) {
            if (PROVINCE_TERRITORY[code] === territory) return code;
        }
        return null;
    }

    function strip_tax_rows(frm, predicate) {
        var keep = (frm.doc.taxes || []).filter(function (row) { return !predicate(row); });
        var removed = frm.doc.taxes.length - keep.length;
        if (!removed) return;
        frm.clear_table("taxes");
        keep.forEach(function (row) { frm.add_child("taxes", row); });
        frm.refresh_field("taxes");
    }

    // ── Main rule engine ────────────────────────────────────────────────────────

    function apply_canadian_rules(frm) {
        if (!frm.doc.customer) return;

        get_settings(frm).then(function (s) {
            if (!s) return;  // no CA config for this company — skip silently

            // Rule 1 — apply_to_* kill switch
            var apply_flag = {
                "Sales Order":   "apply_to_sales_order",
                "Quotation":     "apply_to_quotation",
                "Sales Invoice": "apply_to_sales_invoice",
            }[frm.doctype];

            if (apply_flag && s[apply_flag] === 0) {
                frm.clear_table("taxes");
                frm.refresh_field("taxes");
                return;
            }

            // Rule 2 — Small supplier: no GST/HST at all
            if (s.is_small_supplier) {
                if ((frm.doc.taxes || []).length) {
                    frm.clear_table("taxes");
                    frm.refresh_field("taxes");
                }
                frm.dashboard.set_headline_alert(
                    __("Small Supplier mode — no GST/HST applied"),
                    "yellow"
                );
                return;
            }

            // Rule 3 — Zero-rated items
            var items = (frm.doc.items || []).filter(function (r) { return r.item_code; });
            if (items.length) {
                var all_zero  = items.every(function (r) { return r.zero_rated_gst; });
                var some_zero = items.some(function (r) { return r.zero_rated_gst; });

                if (all_zero) {
                    frm.clear_table("taxes");
                    frm.refresh_field("taxes");
                    frappe.show_alert({ message: __("All items are zero-rated — no GST/HST applied"), indicator: "blue" }, 5);
                    return;
                }

                if (some_zero && !frm.__ca_zero_rated_alerted) {
                    frm.__ca_zero_rated_alerted = true;
                    frappe.show_alert({
                        message: __("Mixed zero-rated items detected. Split the invoice for accurate GST/HST treatment."),
                        indicator: "orange",
                    }, 8);
                }
            }

            // Rule 4 — Selective PST/QST exemption strip
            frappe.db.get_value("Customer", frm.doc.customer, ["pst_exempt", "qst_exempt"])
                .then(function (r) {
                    var vals = (r && r.message) || {};
                    if (!vals.pst_exempt && !vals.qst_exempt) return;

                    var province = territory_to_province(frm.doc.territory);
                    var pst_account = (s.pst_account || "").toLowerCase();
                    var qst_account = (s.qst_account || "").toLowerCase();

                    function is_pst_row(row) {
                        if (pst_account && (row.account_head || "").toLowerCase() === pst_account) return true;
                        return /\b(PST|RST)\b/i.test(row.description || "");
                    }

                    function is_qst_row(row) {
                        if (qst_account && (row.account_head || "").toLowerCase() === qst_account) return true;
                        return /\bQST\b/i.test(row.description || "");
                    }

                    strip_tax_rows(frm, function (row) {
                        if (vals.pst_exempt && province && PST_PROVINCES.has(province) && is_pst_row(row)) return true;
                        if (vals.qst_exempt && province === "QC" && is_qst_row(row)) return true;
                        return false;
                    });
                });
        });
    }

    // ── Address → territory resolver ────────────────────────────────────────────

    function resolve_address_to_territory(frm) {
        if (!frm.doc.customer) return;
        var address_name = frm.doc.shipping_address_name || frm.doc.customer_address;
        if (!address_name) return;

        frappe.db.get_value("Address", address_name, "state").then(function (r) {
            var state = ((r && r.message && r.message.state) || "").trim().toUpperCase();
            var territory = PROVINCE_TERRITORY[state];
            if (territory && territory !== frm.doc.territory) {
                frm.set_value("territory", territory);
            }
        });
    }

    // ── Event registration ───────────────────────────────────────────────────────

    ["Sales Order", "Quotation", "Sales Invoice"].forEach(function (doctype) {
        frappe.ui.form.on(doctype, {
            refresh: function (frm) {
                _settings_promise = null;
                _settings_company = null;
                frm.__ca_zero_rated_alerted = false;
                apply_canadian_rules(frm);
            },
            company: function (frm) {
                // Reset settings cache when company changes on the document
                _settings_promise = null;
                _settings_company = null;
            },
            shipping_address_name: resolve_address_to_territory,
            customer_address:      resolve_address_to_territory,
            taxes_and_charges:     apply_canadian_rules,
            items_add:             apply_canadian_rules,
            items_remove:          apply_canadian_rules,
        });
    });

    ["Sales Order Item", "Sales Invoice Item", "Quotation Item"].forEach(function (child) {
        frappe.ui.form.on(child, {
            item_code: function (frm) { apply_canadian_rules(frm); },
        });
    });

})();
