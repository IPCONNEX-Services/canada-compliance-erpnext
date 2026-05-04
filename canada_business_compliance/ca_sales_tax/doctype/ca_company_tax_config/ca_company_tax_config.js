var _CA_ACCOUNT_FIELDS = ["gst_account", "hst_account", "pst_account", "qst_account",
                          "pst_bc_account", "pst_sk_account", "rst_mb_account",
                          "gst_itc_account", "hst_itc_account", "qst_itc_account"];

frappe.ui.form.on("CA Company Tax Config", {
    setup: function (frm) {
        _CA_ACCOUNT_FIELDS.forEach(function (field) {
            frm.set_query(field, function () {
                return {
                    filters: [
                        ["account_type", "in", ["Tax", "Payable"]],
                        ["company", "=", frm.doc.company],
                    ],
                };
            });
        });
    },

    company: function (frm) {
        frm.set_value("company_province", "");
        _CA_ACCOUNT_FIELDS.forEach(function (f) { frm.set_value(f, ""); });

        if (!frm.doc.company) return;

        frappe.db.get_value("Company", frm.doc.company, "country", function (r) {
            if (r && r.country && r.country !== "Canada") {
                frappe.msgprint({
                    title: __("Non-Canadian Company"),
                    indicator: "orange",
                    message: __(
                        "The selected company is registered under <b>{0}</b>. "
                        + "CA Company Tax Config is designed for Canadian companies.",
                        [r.country]
                    ),
                });
            }
        });
    },

    refresh: function (frm) {
        if (frm.doc.__islocal) return;
        if (!frm.doc.enabled || !frm.doc.collects_canada_sales_tax || frm.doc.is_small_supplier) return;

        frm.add_custom_button(__("Create Tax Accounts"), function () {
            if (!frm.doc.company) {
                frappe.msgprint(__("Select a company first."));
                return;
            }

            var mode_hint = frm.doc.use_advanced_pst
                ? __(" in <b>advanced mode</b> (BC PST, SK PST, MB RST separately)")
                : "";
            var province_hint = frm.doc.company_province
                ? __(" for province <b>{0}</b>", [frm.doc.company_province])
                : __(" (no province set — all accounts will be created)");

            frappe.confirm(
                __("Create missing tax accounts{0}{1} under <b>{2}</b>'s Chart of Accounts?",
                    [province_hint, mode_hint, frm.doc.company]),
                function () {
                    frappe.show_progress(__("Creating accounts…"), 40, 100, __("Checking Chart of Accounts…"));
                    frappe.call({
                        method: "canada_business_compliance.utils.setup_taxes.ensure_company_tax_accounts",
                        args: { company: frm.doc.company },
                        callback: function (r) {
                            frappe.hide_progress();
                            if (r.exc || !r.message) return;

                            var created = r.message.created;
                            var warnings = r.message.warnings || [];

                            var detail = created.length
                                ? __("Created: <b>{0}</b>", [created.join(", ")])
                                : __("All accounts already existed — nothing new was created.");

                            var msg = detail + "<br><br>"
                                + __("Click <b>Generate Tax Templates & Rules</b> to finish setup.");

                            if (warnings.length) {
                                msg += "<br><br><b>" + __("Warnings") + ":</b><br>" + warnings.join("<br>");
                            }

                            frappe.msgprint({
                                title: __("Tax Accounts Ready"),
                                indicator: warnings.length ? "orange" : "green",
                                message: msg,
                            });

                            frm.reload_doc();
                        },
                    });
                }
            );
        }, __("Setup"));

        frm.add_custom_button(__("Generate Tax Templates & Rules"), function () {
            var mode_label = frm.doc.use_advanced_pst
                ? __(" (advanced per-province PST mode)") : "";
            frappe.confirm(
                __("Create or update Sales Tax Templates and Tax Rules for <b>{0}</b>{1}?",
                    [frm.doc.company, mode_label]),
                function () {
                    frappe.show_progress(__("Generating…"), 30, 100, __("Creating templates and tax rules…"));
                    frappe.call({
                        method: "canada_business_compliance.utils.setup_taxes.setup_company_taxes",
                        args: { company: frm.doc.company },
                        callback: function (r) {
                            frappe.hide_progress();
                            if (!r.exc && r.message) {
                                var m = r.message;
                                frappe.msgprint({
                                    title: __("Done"),
                                    indicator: "green",
                                    message: __(
                                        "<b>Sales</b> — Templates: {0} created, {1} updated | Rules: {2} created, {3} updated<br>"
                                        + "<b>Purchase</b> — Templates: {4} created, {5} updated | Rules: {6} created, {7} updated",
                                        [m.templates_created, m.templates_updated,
                                         m.rules_created, m.rules_updated,
                                         m.purchase_templates_created, m.purchase_templates_updated,
                                         m.purchase_rules_created, m.purchase_rules_updated]
                                    ),
                                });
                            }
                        },
                    });
                }
            );
        }, __("Setup"));
    },
});
