"""Handler for APP.FIND_QUEST_LOCATIONS(request VARIANT, address STRING).

The address is geocoded against APP.ADDRESS (OpenStreetMap addresses in Pomona;
this trial account cannot call outside geocoders). Request values reach SQL only
as bind parameters; the one interpolated value is the constant settings.EMBED_MODEL.

Preference match per place = the best (tag, interest) score of:
* keyword: 1.0 exact tag, INTEREST_SYNONYM weight, or 0.8 whole-word match;
* semantic (fallback for interests with no keyword match nearby): the tag is
  among the interest's top-k closest category labels by Cortex AI_EMBED cosine
  (above a floor), scored by rank. Without the fallback rule, top-k always fills
  and e.g. 'coffee' pulled in restaurants. Raw cosine is not used
  because short labels score in a compressed band (related ~0.86-0.93,
  unrelated ~0.75-0.85), so a threshold alone is noisy.
"""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from . import settings
from .ranking import build_locations
from .request import parse_request

NEARBY_SQL = """
WITH origin AS (SELECT ST_MAKEPOINT(?::FLOAT, ?::FLOAT) AS pt),
near AS (
    SELECT p.place_id, p.osm_ref, p.name, p.tags, p.latitude, p.longitude,
           p.address, p.website, p.snapshot_date, ST_DISTANCE(p.point, s.pt) AS dist_m
    FROM APP.PLACE p CROSS JOIN origin s
    WHERE ST_DWITHIN(p.point, s.pt, ?::FLOAT)
      AND EXISTS (SELECT 1 FROM APP.PLACE_HOURS h WHERE h.place_id = p.place_id)
),
interests AS (
    SELECT f.value::STRING AS interest FROM TABLE(FLATTEN(input => PARSE_JSON(?))) f
),
place_tags AS (
    SELECT n.place_id, t.value::STRING AS label
    FROM near n, LATERAL FLATTEN(input => n.tags) t
),
keyword_match AS (
    SELECT pt.place_id, pt.label, it.interest, 'keyword' AS kind,
           CASE WHEN pt.label = it.interest THEN 1.0
                WHEN s.weight IS NOT NULL THEN s.weight
                WHEN ARRAY_CONTAINS(it.interest::VARIANT, SPLIT(pt.label, ' ')) THEN 0.8
                ELSE 0 END AS sim
    FROM place_tags pt
    CROSS JOIN interests it
    LEFT JOIN APP.INTEREST_SYNONYM s ON s.interest = it.interest AND s.label = pt.label
),
interest_vecs AS (
    SELECT interest, AI_EMBED('{model}', interest) AS vec FROM interests
),
sem_rank AS (
    SELECT interest, label, rk
    FROM (
        SELECT iv.interest, ce.label,
               VECTOR_COSINE_SIMILARITY(ce.embedding, iv.vec) AS cos,
               ROW_NUMBER() OVER (PARTITION BY iv.interest
                   ORDER BY VECTOR_COSINE_SIMILARITY(ce.embedding, iv.vec) DESC, ce.label) AS rk
        FROM interest_vecs iv
        JOIN APP.CATEGORY_EMBEDDING ce ON ce.model = '{model}'
    )
    WHERE rk <= ?::INT AND cos >= ?::FLOAT
),
semantic_match AS (
    SELECT pt.place_id, pt.label, sr.interest, 'semantic' AS kind,
           ?::FLOAT * (1 - 0.05 * (sr.rk - 1)) AS sim
    FROM place_tags pt
    JOIN sem_rank sr ON sr.label = pt.label
    -- Fallback only: skip interests that already have a keyword match nearby.
    WHERE sr.interest NOT IN (SELECT interest FROM keyword_match WHERE sim > 0)
),
cost AS (
    SELECT pt.place_id, MAX(c.usd) AS usd, MAX_BY(c.label, c.usd) AS cost_label
    FROM place_tags pt
    JOIN APP.CATEGORY_COST c ON c.label = pt.label
    GROUP BY pt.place_id
),
best AS (
    SELECT place_id, label, interest, kind, sim
    FROM (SELECT * FROM keyword_match UNION ALL SELECT * FROM semantic_match)
    WHERE sim > 0
    QUALIFY ROW_NUMBER() OVER (PARTITION BY place_id ORDER BY sim DESC, kind, label, interest) = 1
)
SELECT n.*, b.sim, b.label AS sim_label, b.interest AS sim_interest, b.kind AS sim_kind,
       c.usd AS cost_usd, c.cost_label
FROM near n
LEFT JOIN best b ON b.place_id = n.place_id
LEFT JOIN cost c ON c.place_id = n.place_id""".replace("{model}", settings.EMBED_MODEL)

HOURS_SQL = """
SELECT place_id, day_of_week, open_minute, close_minute
FROM APP.PLACE_HOURS
WHERE ARRAY_CONTAINS(place_id::VARIANT, PARSE_JSON(?))"""


# Several OSM features can share an address (e.g. every building on a campus);
# use their median point.
ADDRESS_SQL = """
SELECT MEDIAN(latitude) AS lat, MEDIAN(longitude) AS lon, COUNT(*) AS n,
       MODE(housenumber || ' ' || street || COALESCE(', ' || postcode, '')) AS matched
FROM APP.ADDRESS
WHERE housenumber = ? AND street_core = ? AND (?::STRING IS NULL OR postcode = ?)"""


def find_quest_locations(session, request, address):
    payload = json.loads(request) if isinstance(request, str) else request

    def locate(housenumber, core, postcode):
        row = _rows(session.sql(ADDRESS_SQL, params=[housenumber, core, postcode, postcode]))[0]
        if not row["n"]:
            return None
        return float(row["lat"]), float(row["lon"]), row["matched"]

    req = parse_request(payload, address, datetime.now(ZoneInfo(settings.TIMEZONE)), locate)

    rows = _rows(session.sql(NEARBY_SQL, params=[
        req.longitude, req.latitude, settings.FILL_RADIUS_M,
        json.dumps(list(req.interests)),
        settings.SEMANTIC_TOP_K, settings.SEMANTIC_FLOOR, settings.SEMANTIC_CAP,
    ]))
    for row in rows:
        row["tags"] = json.loads(row["tags"]) if isinstance(row.get("tags"), str) else row.get("tags")

    weekly = {}
    ids = json.dumps([row["place_id"] for row in rows])
    for row in _rows(session.sql(HOURS_SQL, params=[ids])):
        weekly.setdefault(row["place_id"], []).append({
            "day_of_week": int(row["day_of_week"]),
            "open_minute": int(row["open_minute"]),
            "close_minute": int(row["close_minute"]),
        })

    return build_locations(req, rows, weekly, datetime.now(timezone.utc))


def _rows(dataframe):
    return [{k.lower(): v for k, v in row.as_dict().items()} for row in dataframe.collect()]
