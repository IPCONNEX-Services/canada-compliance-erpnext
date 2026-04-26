// Canada Business Compliance — postal code → province auto-fill on Address form.
// No external API. Maps Canadian FSA first letter (and X0A/X0B/X0C for Nunavut) to province code.

(function () {
    "use strict";

    // FSA first letter → 2-letter province code
    var PREFIX_MAP = {
        A: "NL", B: "NS", C: "PE", E: "NB",
        G: "QC", H: "QC", J: "QC",
        K: "ON", L: "ON", M: "ON", N: "ON", P: "ON",
        R: "MB", S: "SK", T: "AB", V: "BC", Y: "YT",
        // X handled separately: X0A/X0B/X0C = Nunavut, all other X = Northwest Territories
    };

    var NU_FSAS = { X0A: true, X0B: true, X0C: true };

    // Canadian postal code: A1A 1A1 or A1A1A1 (space optional)
    var CA_POSTAL_RE = /^[ABCEGHJ-NPRSTVXY][0-9][ABCEGHJ-NPRSTV-Z] ?[0-9][ABCEGHJ-NPRSTV-Z][0-9]$/i;

    function postal_to_province(code) {
        var clean = (code || "").replace(/\s+/g, "").toUpperCase();
        if (!CA_POSTAL_RE.test(clean)) return null;
        var letter = clean[0];
        if (letter === "X") return NU_FSAS[clean.slice(0, 3)] ? "NU" : "NT";
        return PREFIX_MAP[letter] || null;
    }

    frappe.ui.form.on("Address", {
        pincode: function (frm) {
            var province = postal_to_province(frm.doc.pincode);
            if (!province) return;   // not a recognizable Canadian postal code — do nothing

            if (!frm.doc.country) {
                frm.set_value("country", "Canada");
            }

            var existing = (frm.doc.state || "").trim().toUpperCase();

            if (!existing) {
                frm.set_value("state", province);
            } else if (existing !== province) {
                frappe.show_alert({
                    message: __("Postal code suggests province {0} but province is set to {1}. Verify the address.", [province, frm.doc.state]),
                    indicator: "orange",
                }, 8);
            }
            // existing === province: already correct, no action needed
        },
    });

})();
