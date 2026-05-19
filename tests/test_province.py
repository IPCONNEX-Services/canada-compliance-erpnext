"""Bulletproof province normalization — exhaustive input variations."""
import pytest


# ── 2-letter codes ────────────────────────────────────────────────────────────

def test_all_13_codes_uppercase(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    for code in ["AB","BC","MB","NB","NL","NS","NT","NU","ON","PE","QC","SK","YT"]:
        assert normalize_province(code) == code


def test_codes_lowercase(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    for code in ["ab","bc","mb","nb","nl","ns","nt","nu","on","pe","qc","sk","yt"]:
        assert normalize_province(code) == code.upper()


def test_codes_with_whitespace(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    assert normalize_province("  ON  ") == "ON"
    assert normalize_province("\tQC\n") == "QC"


# ── Full English names ────────────────────────────────────────────────────────

def test_full_english_names(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    expected = {
        "Alberta": "AB",
        "British Columbia": "BC",
        "Manitoba": "MB",
        "New Brunswick": "NB",
        "Newfoundland and Labrador": "NL",
        "Nova Scotia": "NS",
        "Northwest Territories": "NT",
        "Nunavut": "NU",
        "Ontario": "ON",
        "Prince Edward Island": "PE",
        "Quebec": "QC",
        "Saskatchewan": "SK",
        "Yukon": "YT",
    }
    for name, code in expected.items():
        assert normalize_province(name) == code, f"failed for {name!r}"


def test_full_names_case_insensitive(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    assert normalize_province("ontario") == "ON"
    assert normalize_province("ONTARIO") == "ON"
    assert normalize_province("OnTaRiO") == "ON"


# ── French names + accents ────────────────────────────────────────────────────

def test_quebec_with_accent(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    assert normalize_province("Québec") == "QC"
    assert normalize_province("québec") == "QC"
    assert normalize_province("QUÉBEC") == "QC"


def test_french_province_names(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    assert normalize_province("Colombie-Britannique") == "BC"
    assert normalize_province("Colombie Britannique") == "BC"
    assert normalize_province("Nouveau-Brunswick") == "NB"
    assert normalize_province("Nouvelle-Écosse") == "NS"
    assert normalize_province("Île-du-Prince-Édouard") == "PE"


# ── Common abbreviations ──────────────────────────────────────────────────────

def test_common_abbreviations(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    assert normalize_province("Ont") == "ON"
    assert normalize_province("Que") == "QC"
    assert normalize_province("Sask") == "SK"
    assert normalize_province("Man") == "MB"
    assert normalize_province("Alta") == "AB"
    assert normalize_province("Nfld") == "NL"
    assert normalize_province("PEI") == "PE"


# ── Combined "CODE - Name" forms ──────────────────────────────────────────────

def test_combined_code_name_format(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    assert normalize_province("AB - Alberta") == "AB"
    assert normalize_province("ON-Ontario") == "ON"
    assert normalize_province("QC Quebec") == "QC"


# ── Trailing junk (postal code, country, comma) ───────────────────────────────

def test_input_with_trailing_junk(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    assert normalize_province("Ontario, Canada") == "ON"
    assert normalize_province("QC H2Y 1A1") == "QC"
    assert normalize_province("British Columbia, Canada") == "BC"


# ── Negative / edge cases ─────────────────────────────────────────────────────

def test_none_and_empty(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    assert normalize_province(None) is None
    assert normalize_province("") is None
    assert normalize_province("   ") is None


def test_unknown_input_returns_none(mock_frappe_module):
    from canada_business_compliance.utils.province import normalize_province
    assert normalize_province("XX") is None
    assert normalize_province("California") is None
    assert normalize_province("Canada") is None  # country, not province
    assert normalize_province("Montreal") is None  # city, not province


def test_does_not_match_substring_anywhere(mock_frappe_module):
    """Prefix match must be word-bounded — "Sontario" must not match "ON"."""
    from canada_business_compliance.utils.province import normalize_province
    assert normalize_province("Sontario") is None


# ── code_to_name ──────────────────────────────────────────────────────────────

def test_code_to_name(mock_frappe_module):
    from canada_business_compliance.utils.province import code_to_name
    assert code_to_name("ON") == "Ontario"
    assert code_to_name("qc") == "Quebec"
    assert code_to_name("  AB  ") == "Alberta"
    assert code_to_name("XX") is None
    assert code_to_name(None) is None


# ── territory.province_to_territory still works on all input forms ────────────

def test_province_to_territory_accepts_full_names(mock_frappe_module):
    from canada_business_compliance.utils.territory import province_to_territory
    assert province_to_territory("Ontario") == "Ontario"
    assert province_to_territory("Québec") == "Quebec"
    assert province_to_territory("Quebec") == "Quebec"
    assert province_to_territory("ON") == "Ontario"
    assert province_to_territory("qc") == "Quebec"
    assert province_to_territory("Sask") == "Saskatchewan"
