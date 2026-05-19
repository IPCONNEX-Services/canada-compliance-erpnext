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

    // Minimal province normalizer — mirrors canada_business_compliance.utils.province.
    var VALID_CODES = { AB:1,BC:1,MB:1,NB:1,NL:1,NS:1,NT:1,NU:1,ON:1,PE:1,QC:1,SK:1,YT:1 };
    var ALIASES = {
        "ab":"AB","alberta":"AB","alta":"AB","alb":"AB",
        "bc":"BC","british columbia":"BC","colombie britannique":"BC",
        "mb":"MB","manitoba":"MB","man":"MB",
        "nb":"NB","new brunswick":"NB","nouveau brunswick":"NB",
        "nl":"NL","nf":"NL","nfld":"NL","newfoundland":"NL",
        "newfoundland and labrador":"NL","newfoundland labrador":"NL","labrador":"NL",
        "terre neuve":"NL","terre neuve et labrador":"NL",
        "ns":"NS","nova scotia":"NS","nouvelle ecosse":"NS",
        "nt":"NT","nwt":"NT","northwest territories":"NT","territoires du nord ouest":"NT",
        "nu":"NU","nunavut":"NU",
        "on":"ON","ont":"ON","ontario":"ON",
        "pe":"PE","pei":"PE","p e i":"PE","prince edward island":"PE","ile du prince edouard":"PE",
        "qc":"QC","pq":"QC","que":"QC","qbc":"QC","quebec":"QC",
        "sk":"SK","sask":"SK","saskatchewan":"SK",
        "yt":"YT","yk":"YT","yukon":"YT","yukon territory":"YT",
    };
    var ALIAS_KEYS_DESC = Object.keys(ALIASES).sort(function (a, b) { return b.length - a.length; });

    function normalize_province(raw) {
        if (!raw) return null;
        var s = String(raw).trim();
        if (!s) return null;
        var seps = [" - ", "-", " "];
        for (var i = 0; i < seps.length; i++) {
            var head = s.split(seps[i])[0].trim();
            if (head.length === 2 && VALID_CODES[head.toUpperCase()]) return head.toUpperCase();
        }
        var stripped = s.normalize ? s.normalize("NFKD").replace(/[̀-ͯ]/g, "") : s;
        var key = stripped.toLowerCase().replace(/[.,\/\\_\-'"()]/g, " ").replace(/\s+/g, " ").trim();
        if (!key) return null;
        if (ALIASES[key]) return ALIASES[key];
        if (key.length === 2 && VALID_CODES[key.toUpperCase()]) return key.toUpperCase();
        for (var j = 0; j < ALIAS_KEYS_DESC.length; j++) {
            var alias = ALIAS_KEYS_DESC[j];
            if (key === alias || key.indexOf(alias + " ") === 0) return ALIASES[alias];
        }
        return null;
    }

    frappe.ui.form.on("Address", {
        pincode: function (frm) {
            var province = postal_to_province(frm.doc.pincode);
            if (!province) return;   // not a recognizable Canadian postal code — do nothing

            if (!frm.doc.country) {
                frm.set_value("country", "Canada");
            }

            var existing_raw = (frm.doc.state || "").trim();
            var existing_code = normalize_province(existing_raw);

            if (!existing_raw) {
                frm.set_value("state", province);
            } else if (existing_code !== province) {
                frappe.show_alert({
                    message: __("Postal code suggests province {0} but province is set to {1}. Verify the address.", [province, frm.doc.state]),
                    indicator: "orange",
                }, 8);
            }
            // matches (including aliases like "Ontario" vs "ON"): no action
        },
    });

})();
