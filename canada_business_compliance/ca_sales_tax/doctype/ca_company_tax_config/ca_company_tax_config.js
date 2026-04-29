frappe.ui.form.on("CA Company Tax Config", {
    refresh: function (frm) {
        if (frm.doc.__islocal) return;
        if (!frm.doc.enabled || !frm.doc.collects_canada_sales_tax || frm.doc.is_small_supplier) return;

        frm.add_custom_button(__("Generate Tax Templates & Rules"), function () {
            var missing = [];
            if (!frm.doc.gst_account) missing.push(__("GST Account"));
            if (!frm.doc.hst_account) missing.push(__("HST Account"));
            if (missing.length) {
                frappe.msgprint({
                    title: __("Missing Accounts"),
                    indicator: "orange",
                    message: __("Set these accounts before generating: {0}", [missing.join(", ")]),
                });
                return;
            }

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
