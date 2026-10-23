"""Normalize US street addresses so a user's text can match OSM address tags.

The same functions run at load time (scripts/osm_fetch.py) and at request time
(procedure.py), so "3801 W Temple Ave" and OSM's "3801 West Temple Avenue" both
become ("3801", "temple ave"). Leading directions are dropped because OSM tags
the same building both with and without them.
"""

import re

_WORDS = {
    "avenue": "ave", "av": "ave", "street": "st", "boulevard": "blvd", "drive": "dr",
    "road": "rd", "lane": "ln", "court": "ct", "place": "pl", "parkway": "pkwy",
    "circle": "cir", "highway": "hwy", "terrace": "ter", "square": "sq", "trail": "trl",
    "north": "n", "south": "s", "east": "e", "west": "w",
}
_DIRECTIONS = {"n", "s", "e", "w", "ne", "nw", "se", "sw"}
_POSTCODE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
_HOUSE_STREET = re.compile(r"^\s*(\d+[a-z]?)\s+(.+)$", re.IGNORECASE)


def street_core(street):
    """'West Temple Avenue' -> 'temple ave'; returns '' when nothing is left."""
    words = [_WORDS.get(w, w) for w in re.sub(r"[^a-z0-9 ]", " ", street.lower()).split()]
    if len(words) > 1 and words[0] in _DIRECTIONS:
        words = words[1:]
    return " ".join(words)


def parse_address(text):
    """Return (housenumber, street_core, postcode or None), or None if unusable."""
    first = text.split(",")[0]
    match = _HOUSE_STREET.match(first)
    if not match:
        return None
    core = street_core(match.group(2))
    if not core:
        return None
    postcodes = _POSTCODE.findall(text[len(first):]) if "," in text else []
    return match.group(1).lower(), core, (postcodes[-1] if postcodes else None)
