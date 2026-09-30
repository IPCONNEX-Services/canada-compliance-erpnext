"""Add the read-only `ca_tax_basis` field to Purchase Order / Receipt / Invoice. Idempotent."""
from canada_business_compliance.utils.custom_fields import ensure_custom_fields


def execute():
    ensure_custom_fields()
