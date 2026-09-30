"""Purchase tax place of supply (v0.3.2): destination province picks the template, with
drop-ship → shipping_address → company address → supplier fallback, and ca_tax_basis recorded."""
from types import SimpleNamespace


ADDRESSES = {
    # name: (state, country)
    "IPX-MTL": ("Quebec", "Canada"),
    "IPX-BILL": ("QC", ""),
    "CUST-ON-SHIP": ("Ontario", "Canada"),
    "CUST-ON-BILL": ("ON", "Canada"),
    "CUST-US": ("FL", "United States"),
    "INGRAM-ON": ("ON", "Canada"),
    "NEXIT-ON": ("Ontario", "Canada"),
    "FOREIGN-SUP": (None, "Singapore"),
}


class FakeDoc(dict):
    """Minimal stand-in for a Frappe Document: dict access + attribute set + set/append."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def set(self, key, value):
        self[key] = value

    def append(self, key, row):
        self.setdefault(key, []).append(row)


def _setup(frappe, party_addresses=None, sales_orders=None, templates=None, small_supplier=0, abbr="IPX"):
    party_addresses = party_addresses or {}
    sales_orders = sales_orders or {}
    templates = templates if templates is not None else {
        "CA HST 13% - IPX", "CA GST + QST - IPX", "CA GST Only - IPX", "CA HST 15% - IPX", "CA HST 14% - IPX",
    }

    def get_value(doctype, name, fields, as_dict=False):
        if doctype == "Address":
            state, country = ADDRESSES.get(name, (None, None))
            if isinstance(fields, (list, tuple)):
                return {"state": state, "country": country} if name in ADDRESSES else None
            return state
        if doctype == "Sales Order":
            return sales_orders.get(name)
        if doctype == "Company" and fields == "abbr":
            return abbr
        return None

    def sql(query, values):
        link_doctype, link_name = values
        addr = party_addresses.get((link_doctype, link_name))
        return [(addr,)] if addr else []

    def get_doc(doctype, name):
        if doctype == "CA Company Tax Config":
            return SimpleNamespace(enabled=1, collects_canada_sales_tax=1, is_small_supplier=small_supplier)
        if doctype == "Purchase Taxes and Charges Template":
            return SimpleNamespace(taxes=[SimpleNamespace(
                charge_type="On Net Total", account_head="Tax - IPX", description=name, rate=1,
                get=lambda k, d=None: d,
            )])
        raise AssertionError(doctype)

    frappe.db.get_value.side_effect = get_value
    frappe.db.sql.side_effect = sql
    frappe.db.exists.side_effect = lambda dt, filters: filters["name"] in templates
    frappe.get_all.return_value = ["CFG"]
    frappe.get_doc.side_effect = get_doc
    frappe.get_meta.return_value.has_field.return_value = False  # standard Supplier: no territory


def _po(**kw):
    base = {"doctype": "Purchase Order", "company": "IPCONNEX Services Inc.", "docstatus": 0, "items": []}
    base.update(kw)
    return FakeDoc(base)


# ── get_purchase_destination ────────────────────────────────────────────────

def test_ontario_supplier_delivering_to_montreal_is_qc(frappe):
    from canada_business_compliance.utils.tax_resolver import get_purchase_destination
    _setup(frappe)
    doc = _po(supplier="Ingram Micro Canada", supplier_address="INGRAM-ON", shipping_address="IPX-MTL")
    assert get_purchase_destination(doc) == ("QC", "Destination QC (ship to IPX-MTL)")


def test_drop_ship_customer_shipping_address_wins(frappe):
    from canada_business_compliance.utils.tax_resolver import get_purchase_destination
    _setup(frappe)
    doc = _po(supplier="Nex-IT Canada", customer="Partash", shipping_address="CUST-ON-SHIP", billing_address="IPX-BILL")
    assert get_purchase_destination(doc) == ("ON", "Destination ON (drop-ship to CUST-ON-SHIP)")


def test_drop_ship_uses_linked_sales_order_address(frappe):
    from canada_business_compliance.utils.tax_resolver import get_purchase_destination
    _setup(frappe, sales_orders={"SO-1": {"shipping_address_name": "CUST-ON-SHIP", "customer_address": "CUST-ON-BILL"}})
    doc = _po(supplier="Nex-IT Canada", billing_address="IPX-BILL",
              items=[{"sales_order": "SO-1", "delivered_by_supplier": 1}])
    assert get_purchase_destination(doc) == ("ON", "Destination ON (drop-ship to CUST-ON-SHIP)")


def test_drop_ship_ignores_sales_order_without_delivered_by_supplier(frappe):
    from canada_business_compliance.utils.tax_resolver import get_purchase_destination
    _setup(frappe, sales_orders={"SO-1": {"shipping_address_name": "CUST-ON-SHIP"}})
    doc = _po(supplier="Nex-IT Canada", shipping_address="IPX-MTL",
              items=[{"sales_order": "SO-1", "delivered_by_supplier": 0}])
    assert get_purchase_destination(doc)[0] == "QC"


def test_drop_ship_falls_back_to_customer_default_address(frappe):
    from canada_business_compliance.utils.tax_resolver import get_purchase_destination
    _setup(frappe, party_addresses={("Customer", "Partash"): "CUST-ON-SHIP"})
    doc = _po(supplier="Nex-IT Canada", customer="Partash")
    assert get_purchase_destination(doc) == ("ON", "Destination ON (drop-ship to CUST-ON-SHIP)")


def test_drop_ship_outside_canada_gives_no_province(frappe):
    from canada_business_compliance.utils.tax_resolver import get_purchase_destination
    _setup(frappe)
    doc = _po(supplier="Nex-IT Canada", customer="US Co", shipping_address="CUST-US", billing_address="IPX-BILL")
    province, basis = get_purchase_destination(doc)
    assert province is None and basis.startswith("Destination outside Canada")


def test_company_billing_address_on_doc(frappe):
    from canada_business_compliance.utils.tax_resolver import get_purchase_destination
    _setup(frappe)
    doc = _po(supplier="Ingram Micro Canada", billing_address="IPX-BILL")
    assert get_purchase_destination(doc) == ("QC", "Destination QC (company address IPX-BILL)")


def test_company_default_address_when_doc_has_none(frappe):
    from canada_business_compliance.utils.tax_resolver import get_purchase_destination
    _setup(frappe, party_addresses={("Company", "IPCONNEX Services Inc."): "IPX-MTL"})
    doc = _po(supplier="Ingram Micro Canada")
    assert get_purchase_destination(doc) == ("QC", "Destination QC (company address IPX-MTL)")


def test_supplier_fallback_when_no_destination(frappe):
    from canada_business_compliance.utils.tax_resolver import get_purchase_destination
    _setup(frappe, party_addresses={("Supplier", "Ingram Micro Canada"): "INGRAM-ON"})
    doc = _po(supplier="Ingram Micro Canada", company="No Address Co")
    assert get_purchase_destination(doc) == ("ON", "Supplier fallback ON")


def test_supplier_origin_ignores_company_addresses(frappe):
    from canada_business_compliance.utils.tax_resolver import get_supplier_origin_province
    _setup(frappe)
    doc = _po(supplier="Foreign Carrier", supplier_address="FOREIGN-SUP", shipping_address="IPX-MTL", billing_address="IPX-BILL")
    assert get_supplier_origin_province(doc) is None


# ── auto_set_purchase_taxes ────────────────────────────────────────────────

def test_auto_set_ingram_to_montreal_gst_qst(frappe):
    from canada_business_compliance.utils.tax_resolver import auto_set_purchase_taxes
    _setup(frappe)
    doc = _po(supplier="Ingram Micro Canada", supplier_address="INGRAM-ON", shipping_address="IPX-MTL")
    auto_set_purchase_taxes(doc)
    assert doc.taxes_and_charges == "CA GST + QST - IPX"
    assert doc.ca_tax_basis == "Destination QC (ship to IPX-MTL)"
    assert len(doc.taxes) == 1
    # Purchase tax rows must carry the mandatory category / add_deduct_tax
    assert doc.taxes[0]["category"] == "Total" and doc.taxes[0]["add_deduct_tax"] == "Add"


def test_auto_set_nexit_drop_ship_ontario_hst(frappe):
    from canada_business_compliance.utils.tax_resolver import auto_set_purchase_taxes
    _setup(frappe)
    doc = _po(supplier="Nex-IT Canada", supplier_address="NEXIT-ON", customer="Partash", shipping_address="CUST-ON-SHIP")
    auto_set_purchase_taxes(doc)
    assert doc.taxes_and_charges == "CA HST 13% - IPX"
    assert doc.ca_tax_basis == "Destination ON (drop-ship to CUST-ON-SHIP)"


def test_auto_set_supplier_fallback(frappe):
    from canada_business_compliance.utils.tax_resolver import auto_set_purchase_taxes
    _setup(frappe)
    doc = _po(supplier="Ingram Micro Canada", supplier_address="INGRAM-ON")
    auto_set_purchase_taxes(doc)
    assert doc.taxes_and_charges == "CA HST 13% - IPX"
    assert doc.ca_tax_basis == "Supplier fallback ON"


def test_auto_set_respects_manual_template(frappe):
    from canada_business_compliance.utils.tax_resolver import auto_set_purchase_taxes
    _setup(frappe)
    doc = _po(supplier="Ingram Micro Canada", supplier_address="INGRAM-ON", shipping_address="IPX-MTL",
              taxes_and_charges="CA HST 13% - IPX")
    auto_set_purchase_taxes(doc)
    assert doc.taxes_and_charges == "CA HST 13% - IPX"
    assert "ca_tax_basis" not in doc


def test_auto_set_respects_manual_tax_rows(frappe):
    from canada_business_compliance.utils.tax_resolver import auto_set_purchase_taxes
    _setup(frappe)
    rows = [{"account_head": "Manual - IPX", "rate": 5}]
    doc = _po(supplier="Ingram Micro Canada", supplier_address="INGRAM-ON", shipping_address="IPX-MTL", taxes=rows)
    auto_set_purchase_taxes(doc)
    assert doc.taxes == rows and "taxes_and_charges" not in doc


def test_auto_set_skips_non_draft(frappe):
    from canada_business_compliance.utils.tax_resolver import auto_set_purchase_taxes
    _setup(frappe)
    doc = _po(supplier="Ingram Micro Canada", supplier_address="INGRAM-ON", shipping_address="IPX-MTL", docstatus=1)
    auto_set_purchase_taxes(doc)
    assert "taxes_and_charges" not in doc


def test_auto_set_foreign_supplier_untaxed(frappe):
    from canada_business_compliance.utils.tax_resolver import auto_set_purchase_taxes
    _setup(frappe)
    doc = _po(supplier="Foreign Carrier", supplier_address="FOREIGN-SUP", shipping_address="IPX-MTL")
    auto_set_purchase_taxes(doc)
    assert "taxes_and_charges" not in doc


def test_auto_set_export_drop_ship_untaxed(frappe):
    from canada_business_compliance.utils.tax_resolver import auto_set_purchase_taxes
    _setup(frappe)
    doc = _po(supplier="Nex-IT Canada", supplier_address="NEXIT-ON", customer="US Co", shipping_address="CUST-US",
              billing_address="IPX-BILL")
    auto_set_purchase_taxes(doc)
    assert "taxes_and_charges" not in doc


def test_auto_set_basis_truncated(frappe):
    from canada_business_compliance.utils.tax_resolver import auto_set_purchase_taxes, CA_TAX_BASIS_MAX
    long_name = "X" * 300
    ADDRESSES[long_name] = ("QC", "Canada")
    try:
        _setup(frappe)
        doc = _po(supplier="Ingram Micro Canada", supplier_address="INGRAM-ON", shipping_address=long_name)
        auto_set_purchase_taxes(doc)
        assert len(doc.ca_tax_basis) == CA_TAX_BASIS_MAX
    finally:
        del ADDRESSES[long_name]


def test_custom_field_definition():
    from canada_business_compliance.utils.custom_fields import get_custom_fields
    fields = get_custom_fields()
    assert set(fields) == {"Purchase Order", "Purchase Receipt", "Purchase Invoice"}
    f = fields["Purchase Order"][0]
    assert f["fieldname"] == "ca_tax_basis" and f["read_only"] == 1 and f["print_hide"] == 1 and f["length"] == 140
