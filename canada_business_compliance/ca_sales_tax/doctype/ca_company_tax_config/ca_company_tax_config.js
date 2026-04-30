frappe.ui.form.on("CA Company Tax Config", {
    setup: function (frm) {
        ["gst_account", "hst_account", "pst_account", "qst_account"].forEach(function (field) {
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
        ["gst_account", "hst_account", "pst_account", "qst_account"].forEach(function (f) {
            frm.set_value(f, "");
        });

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

            frappe.confirm(
                __(
                    "Create missing tax accounts (GST, HST, PST, QST) under <b>{0}</b>'s Chart of Accounts?",
                    [frm.doc.company]
                ),
                function () {
                    frappe.show_progress(__("Creating accounts…"), 40, 100, __("Checking Chart of Accounts…"));
                    frappe.call({
                        method: "canada_business_compliance.utils.setup_taxes.ensure_company_tax_accounts",
                        args: { company: frm.doc.company },
                        callback: function (r) {
                            frappe.hide_progress();
                            if (r.exc || !r.message) return;

                            var accts = r.message.accounts;
                            var created = r.message.created;

                            frm.set_value("gst_account", accts.gst || "");
                            frm.set_value("hst_account", accts.hst || "");
                            frm.set_value("pst_account", accts.pst || "");
                            frm.set_value("qst_account", accts.qst || "");

                            var detail = created.length
                                ? __("Created: <b>{0}</b>", [created.join(", ")])
                                : __("All accounts already existed — nothing new was created.");

                            frappe.msgprint({
                                title: __("Tax Accounts Ready"),
                                indicator: "green",
                                message: detail + "<br><br>"
                                    + __("Account fields have been saved. Click <b>Generate Tax Templates & Rules</b> to finish setup."),
                            });

                            frm.reload_doc();
                        },
                    });
                }
            );
        }, __("Setup"));

        frm.add_custom_button(__("Generate Tax Templates & Rules"), function () {
            frappe.confirm(
                __("Create or update Sales Tax Templates and Tax Rules for <b>{0}</b>?", [frm.doc.company]),
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
                                        "Tax Templates: {0} created, {1} updated<br>Tax Rules: {2} created, {3} updated",
                                        [m.templates_created, m.templates_updated, m.rules_created, m.rules_updated]
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
