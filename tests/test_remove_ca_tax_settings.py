"""CA Tax Settings removal (v0.3.3): migration reads raw Singles, delete patch is safe."""
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "canada_business_compliance"


def test_doctype_folder_removed():
    assert not (APP / "ca_sales_tax" / "doctype" / "ca_tax_settings").exists()


def test_no_runtime_reference_to_old_doctype():
    allowed = {
        APP / "patches" / "v0_3_0" / "migrate_settings_to_company_config.py",
        APP / "patches" / "v0_3_3" / "remove_ca_tax_settings.py",
    }
    offenders = [
        p for p in APP.rglob("*")
        if p.suffix in {".py", ".js", ".json", ".html"}
        and p not in allowed
        and "CA Tax Settings" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert offenders == []


def test_patch_order_post_model_sync():
    lines = [l.strip() for l in (APP / "patches.txt").read_text().splitlines() if l.strip()]
    post = lines[lines.index("[post_model_sync]") + 1:]
    migrate = "canada_business_compliance.patches.v0_3_0.migrate_settings_to_company_config"
    remove = "canada_business_compliance.patches.v0_3_3.remove_ca_tax_settings"
    assert migrate in post and remove in post
    assert post.index(migrate) < post.index(remove)
    assert lines.count(migrate) == 1


def _setup_migrate(frappe, singles_rows):
    frappe.db.exists.return_value = True
    frappe.db.get_single_value.return_value = "Test Co"
    frappe.get_all.return_value = []
    frappe.db.sql.return_value = singles_rows
    frappe.utils.cint.side_effect = lambda v: int(float(v or 0))
    config = frappe.new_doc.return_value
    values = {}
    config.set.side_effect = lambda k, v: values.__setitem__(k, v)
    return config, values


def test_migrate_copies_raw_singles(frappe):
    from canada_business_compliance.patches.v0_3_0 import migrate_settings_to_company_config as m
    config, values = _setup_migrate(frappe, (
        ("is_small_supplier", "1"),
        ("apply_to_quotation", "0"),
        ("gst_account", "GST Payable - T"),
        ("qst_registration_number", "1234567890TQ0001"),
    ))
    m.execute()
    assert config.company == "Test Co"
    assert config.is_small_supplier == 1
    assert values["apply_to_quotation"] == 0
    assert values["apply_to_sales_order"] == 1
    assert values["use_tax_rules"] == 1
    assert values["gst_account"] == "GST Payable - T"
    assert "hst_account" not in values
    config.insert.assert_called_once()


def test_migrate_defaults_when_old_doctype_gone(frappe):
    from canada_business_compliance.patches.v0_3_0 import migrate_settings_to_company_config as m
    config, values = _setup_migrate(frappe, ())
    m.execute()
    assert config.is_small_supplier == 0
    assert all(values[f] == 1 for f in m._CHECK_FIELDS_DEFAULT_ON)
    config.insert.assert_called_once()


def test_migrate_skips_existing_config(frappe):
    from canada_business_compliance.patches.v0_3_0 import migrate_settings_to_company_config as m
    _setup_migrate(frappe, ())
    frappe.get_all.return_value = [{"name": "Test Co"}]
    m.execute()
    frappe.new_doc.assert_not_called()


def test_remove_patch_deletes_doctype_and_references(frappe):
    from canada_business_compliance.patches.v0_3_3 import remove_ca_tax_settings as r
    frappe.db.exists.return_value = True
    frappe.db.table_exists.return_value = True
    frappe.db.get_value.return_value = ""
    r.execute()
    frappe.delete_doc.assert_called_once_with(
        "DocType", "CA Tax Settings", force=1, ignore_missing=True, ignore_permissions=True
    )
    deleted = {c.args[0] for c in frappe.db.delete.call_args_list}
    assert {"Singles", "Custom Field", "Property Setter", "Workspace Link"} <= deleted
    frappe.clear_cache.assert_called_once()


def test_remove_patch_idempotent_when_gone(frappe):
    from canada_business_compliance.patches.v0_3_3 import remove_ca_tax_settings as r
    frappe.db.exists.return_value = False
    frappe.db.table_exists.return_value = True
    r.execute()
    frappe.delete_doc.assert_not_called()
    assert frappe.db.delete.call_count == len(r._REFERENCES)


def test_shipped_print_format_does_not_use_old_doctype():
    import json
    pf = APP / "ca_sales_tax" / "print_format" / "ca_tax_invoice" / "ca_tax_invoice.json"
    html = json.loads(pf.read_text())["html"]
    assert "CA Tax Settings" not in html
    assert "CA Company Tax Config" in html


def test_remove_patch_refreshes_stale_print_format(frappe):
    from canada_business_compliance.patches.v0_3_3 import remove_ca_tax_settings as r
    frappe.db.exists.return_value = True
    frappe.db.table_exists.return_value = True
    frappe.db.get_value.return_value = "{% set ca = frappe.get_single('CA Tax Settings') %}"
    frappe.get_app_path.return_value = str(APP)
    r.execute()
    args = frappe.db.set_value.call_args.args
    assert args[:3] == ("Print Format", "CA Tax Invoice", "html")
    assert "CA Company Tax Config" in args[3]


def test_remove_patch_leaves_current_print_format(frappe):
    from canada_business_compliance.patches.v0_3_3 import remove_ca_tax_settings as r
    frappe.db.exists.return_value = True
    frappe.db.table_exists.return_value = True
    frappe.db.get_value.return_value = "{{ frappe.get_all('CA Company Tax Config') }}"
    r.execute()
    frappe.db.set_value.assert_not_called()
