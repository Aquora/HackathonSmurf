"""Ranking and matching settings. Change RANKING_VERSION when any value changes."""

RANKING_VERSION = "osm_hybrid_v1"

# Score = W_SIM * preference match + W_DIST * closeness (1 at the start, 0 at the radius edge).
W_SIM = 0.7
W_DIST = 0.3

# Straight-line search radius: half the time budget at walking speed, capped.
MAX_RADIUS_M = 2000
WALKING_SPEED_MPS = 1.3

# A place must stay open this long, continuously, inside the user's time window.
MIN_OPEN_SECONDS = 1200

LIMIT_CAP = 10
MAX_INTERESTS = 5
MAX_INTEREST_LENGTH = 64
SUPPORTED_CURRENCIES = ("USD",)

# Semantic matching: a tag counts when it is among the interest's SEMANTIC_TOP_K
# closest category labels (Cortex AI_EMBED cosine >= SEMANTIC_FLOOR), scored
# SEMANTIC_CAP * (1 - 0.05 * (rank - 1)). Keyword matches score up to 1.0.
EMBED_MODEL = "snowflake-arctic-embed-m-v1.5"
SEMANTIC_TOP_K = 5
SEMANTIC_FLOOR = 0.8
SEMANTIC_CAP = 0.85

# Matches scoring below this produce no "related"/"closest" reason text.
REASON_THRESHOLD = 0.7

ATTRIBUTION = "© OpenStreetMap contributors (ODbL-1.0)"
