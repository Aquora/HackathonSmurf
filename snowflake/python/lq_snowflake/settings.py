"""Ranking and matching settings. Change RANKING_VERSION when any value changes."""

RANKING_VERSION = "osm_hybrid_v6"

# Score = W_SIM * preference match + W_DIST * closeness (1 at the start, 0 at the radius edge).
W_SIM = 0.7
W_DIST = 0.3

# Straight-line search radius per travel method: speed (m/s) x half the time, capped (m).
# Unknown methods use walk.
TRAVEL = {
    "walk": (1.3, 2000),
    "bike": (4.0, 6000),
    "transit": (6.0, 8000),
    "drive": (11.0, 15000),
}
DEFAULT_TRAVEL = "walk"

# The API needs exactly RESULT_LIMIT places. If too few open places fall inside the
# radius, fill from farther open places within this distance (covers all of Pomona).
FILL_RADIUS_M = 25000

# A place must stay open this long, continuously, inside the user's time window.
MIN_OPEN_SECONDS = 1200

# API request (FIND_QUEST_LOCATIONS): times are "now" in Pomona.
TIMEZONE = "America/Los_Angeles"
RESULT_LIMIT = 10
MAX_DESIRED_MINUTES = 1440
MAX_INTERESTS = 5
MAX_INTEREST_LENGTH = 64
CURRENCY = "USD"
MAX_ADDRESS_LENGTH = 300

# Semantic fallback (interests with no keyword match nearby): a tag counts when it
# is among the interest's SEMANTIC_TOP_K closest category labels (Cortex AI_EMBED
# cosine >= SEMANTIC_FLOOR), scored SEMANTIC_CAP * (1 - 0.05 * (rank - 1)).
# Keyword matches score up to 1.0.
EMBED_MODEL = "snowflake-arctic-embed-m-v1.5"
# Top-1 only: on the Pomona labels (2026-10-23) the closest category was right for
# every probe (dessert->ice cream, art->museum, cozy study spot->cafe), but ranks 2-5
# were noise (dessert->breakfast/restaurant, art->american).
SEMANTIC_TOP_K = 1
SEMANTIC_FLOOR = 0.8
SEMANTIC_CAP = 0.85

# Matches scoring below this produce no "related"/"closest" reason text.
REASON_THRESHOLD = 0.7

# OSM tags juice bars and boba shops as amenity=fast_food, so "fast food" alone would make them
# matches for "food". A place whose tags include a drink-only cuisine and no food cuisine keeps
# DRINK_ONLY_FOOD_FACTOR of its match for these interests (below REASON_THRESHOLD: no "food" reason).
FOOD_INTERESTS = frozenset({"food", "restaurant", "meal", "lunch", "dinner", "eat"})
DRINK_ONLY_TAGS = frozenset({"juice", "bubble tea", "tea", "coffee shop", "smoothie", "coffee"})
GENERIC_FOOD_TAGS = frozenset({"fast food", "food court", "cafe", "restaurant"})
DRINK_ONLY_FOOD_FACTOR = 0.4

ATTRIBUTION = "© OpenStreetMap contributors (ODbL-1.0)"
