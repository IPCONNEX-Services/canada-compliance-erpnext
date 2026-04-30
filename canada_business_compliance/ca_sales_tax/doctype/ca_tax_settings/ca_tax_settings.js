frappe.ui.form.on("CA Tax Settings", {
    refresh: function (frm) {
        frm.set_intro(
            __("⚠️ <b>Deprecated.</b> CA Tax Settings has been replaced by "
                + "<b>CA Company Tax Config</b> (one record per company). "
                + "Your data was migrated automatically. This form is kept only for reference."),
            "orange"
        );
        frm.add_custom_button(__("Open CA Company Tax Config"), function () {
            frappe.set_route("List", "CA Company Tax Config");
        });
    },
});
