"""Bulletproof Canadian province normalization.

Maps any reasonable user input — 2-letter codes, full English/French names,
common abbreviations, "AB - Alberta" combined format, with or without
accents/punctuation — to the canonical 2-letter province code.
"""
import unicodedata

PROVINCE_NAME = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}

# Aliases — keys are normalised (lowercased, accents stripped, punctuation → space).
# Covers English + French canonical names, common abbreviations, and legacy codes.
_ALIASES = {
    # Alberta
    "ab": "AB", "alberta": "AB", "alta": "AB", "alb": "AB",
    # British Columbia
    "bc": "BC", "british columbia": "BC",
    "colombie britannique": "BC", "colombie b": "BC",
    # Manitoba
    "mb": "MB", "manitoba": "MB", "man": "MB",
    # New Brunswick
    "nb": "NB", "new brunswick": "NB",
    "nouveau brunswick": "NB",
    # Newfoundland and Labrador
    "nl": "NL", "nf": "NL", "nfld": "NL", "newfoundland": "NL",
    "newfoundland and labrador": "NL",
    "newfoundland labrador": "NL",
    "labrador": "NL",
    "terre neuve": "NL", "terre neuve et labrador": "NL",
    # Nova Scotia
    "ns": "NS", "nova scotia": "NS",
    "nouvelle ecosse": "NS",
    # Northwest Territories
    "nt": "NT", "nwt": "NT", "northwest territories": "NT",
    "territoires du nord ouest": "NT",
    # Nunavut
    "nu": "NU", "nunavut": "NU",
    # Ontario
    "on": "ON", "ont": "ON", "ontario": "ON",
    # Prince Edward Island
    "pe": "PE", "pei": "PE", "p e i": "PE", "prince edward island": "PE",
    "ile du prince edouard": "PE",
    # Quebec
    "qc": "QC", "pq": "QC", "que": "QC", "qbc": "QC", "quebec": "QC",
    # Saskatchewan
    "sk": "SK", "sask": "SK", "saskatchewan": "SK",
    # Yukon
    "yt": "YT", "yk": "YT", "yukon": "YT", "yukon territory": "YT",
}

# Sorted longest-first for prefix matching (so "newfoundland and labrador" beats "newfoundland")
_ALIASES_BY_LENGTH = sorted(_ALIASES.keys(), key=len, reverse=True)


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _normalise_key(s: str) -> str:
    s = _strip_accents(s).lower().strip()
    for ch in (".", ",", "/", "\\", "_", "-", "'", '"', "(", ")"):
        s = s.replace(ch, " ")
    return " ".join(s.split())


def normalize_province(raw):
    """Return the 2-letter Canadian province code for any reasonable input.

    Accepts:
      - 2-letter codes in any case ("on", "ON", " ON ")
      - Full English or French names, with or without accents
        ("Ontario", "Québec", "Quebec", "Colombie-Britannique")
      - Common abbreviations ("Ont", "Sask", "Nfld", "PEI", "Alta")
      - Combined "CODE - Name" or "CODE-Name" forms ("AB - Alberta")
      - Input with trailing junk ("Ontario, Canada", "QC H2Y 1A1")

    Returns the canonical 2-letter code (e.g. "ON") or None if no match.
    """
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None

    # Combined "CODE - Name" / "CODE-Name" — trust the leading 2-letter code if valid
    for sep in (" - ", "-", " "):
        head = s.split(sep, 1)[0].strip()
        if len(head) == 2 and head.upper() in PROVINCE_NAME:
            return head.upper()

    key = _normalise_key(s)
    if not key:
        return None

    # Exact alias hit
    if key in _ALIASES:
        return _ALIASES[key]

    # 2-letter bare code after normalisation
    if len(key) == 2 and key.upper() in PROVINCE_NAME:
        return key.upper()

    # Prefix match: "ontario canada", "qc h2y 1a1", etc.
    for alias in _ALIASES_BY_LENGTH:
        if key == alias or key.startswith(alias + " "):
            return _ALIASES[alias]

    return None


def code_to_name(code):
    """Return the canonical English province name for a 2-letter code."""
    if not code:
        return None
    return PROVINCE_NAME.get(str(code).strip().upper())


def name_to_code(name):
    """Reverse lookup: territory name (English) → 2-letter code. Alias of normalize_province."""
    return normalize_province(name)
