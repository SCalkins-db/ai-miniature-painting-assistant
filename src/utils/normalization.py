"""
normalization.py

Shared text normalization utilities used throughout the project.

Used by:

- registry_loader.py
- paint_database.py
- inventory.py
- audit.py
- audit_missing_color_data_json.py
- audit_equivalency_enrichment_opportunities.py
- import_equivalencies.py
- recommendation_engine.py (future)
"""

import re


# ------------------------------------------------------------------
# Common replacements
# ------------------------------------------------------------------

ALIASES = {

    # --------------------------
    # Product Lines
    # --------------------------
    "warpaints fanatic": "fanatic",
    "warpaint fanatic": "fanatic",
    "war paints fanatic": "fanatic",

    "3rd gen acrylic": "3rd gen",
    "3rd gen": "3rd gen",
    "third gen acrylic": "3rd gen",

    "pro acryl standard": "standard",
    "pro acryl signature": "signature",

    "contrast": "contrast",
    "base": "base",
    "layer": "layer",
    "air": "air",
    "spray": "spray",
    "xpress color": "xpress",
    "game color": "game color",
    "model color": "model color",
    "model air": "model air",
    "game air": "game air",

    "speed paint": "speedpaint",
    "speed_paint": "speedpaint",
    "speed-paint": "speedpaint",
    "speedpaint2": "speedpaint",
    "speedpaint 2": "speedpaint",
    "speedpaint 2.0": "speedpaint",
    "speed paint 2.0": "speedpaint",
    "speedpaint2.0": "speedpaint",
    "speedpaint 20": "speedpaint",
    "speed paint 20": "speedpaint",
    "speedpaint20": "speedpaint",
    "speed paints": "speedpaint",
    "speed paints 20": "speedpaint",

    "war paints": "warpaints",
    "war-paints": "warpaints",
    "war_paints": "warpaints",

    "war paints fanatic": "warpaints fanatic",
    "war-paints fanatic": "warpaints fanatic",

    "3rd generation": "3rd gen",
    "3rd generation acrylic": "3rd gen acrylic",

    "game colour": "game color",
    "model colour": "model color",

    # --------------------------
    # Paint Types
    # --------------------------

    "acrylic paint": "acrylic",
    "acrylic paints": "acrylic",

    # --------------------------
    # Company Names
    # --------------------------

    "games workshop": "games workshop",
    "gw": "games workshop",

    "army painter": "army painter",
    "the army painter": "army painter",

    "ak": "ak interactive",
    "akinteractive": "ak interactive",

    "proacryl": "pro acryl",

    "citadel": "games workshop",
    "games workshop citadel": "games workshop",
    "gw citadel": "games workshop",

    "vallejo": "vallejo",
    "vallejo acrylics": "vallejo",

    "monument": "pro acryl",
    "monument hobbies": "pro acryl",
    "monument pro acryl": "pro acryl",

    "ak interactive": "ak interactive",
    "akinteractive": "ak interactive",
    "ak interactive 3rd gen acrylic": "ak interactive",
}


# ------------------------------------------------------------------
# Canonical normalization
# ------------------------------------------------------------------

def canonicalize(text):
    if text is None:
        return ""

    text = str(text).lower().strip()

    text = text.replace("_", " ")
    text = text.replace("-", " ")

    text = re.sub(r"\s+", " ", text).strip()

    # Apply aliases BEFORE stripping punctuation
    if text in ALIASES:
        text = ALIASES[text]

    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Apply aliases AGAIN after punctuation removal
    if text in ALIASES:
        text = ALIASES[text]

    return text

    text = str(text)

    text = text.lower()

    text = text.strip()

    text = text.replace("_", " ")

    text = text.replace("-", " ")

    text = re.sub(r"\s+", " ", text)

    text = re.sub(r"[^\w\s]", "", text)

    text = text.strip()

    if text in ALIASES:
        return ALIASES[text]

    return text


# ------------------------------------------------------------------
# Key Builder
# ------------------------------------------------------------------

def build_key(*values):
    """
    Builds a normalized lookup key.

    Example

    build_key(company, product_line, paint_name)

    returns

    army painter|speedpaint|grim black
    """

    return "|".join(
        canonicalize(value)
        for value in values
    )


# ------------------------------------------------------------------
# Flexible Match
# ------------------------------------------------------------------

def text_matches(left, right):
    """
    Compare two values using canonical normalization.
    """

    return canonicalize(left) == canonicalize(right)