"""Fetch named Pomona businesses with opening_hours from OpenStreetMap as NDJSON.

Usage: python3 snowflake/scripts/osm_fetch.py --out snowflake/build/osm_pomona.ndjson
Normally run by `scripts/lq.py load`. Uses the public Overpass API; keep runs
infrequent. Data is © OpenStreetMap contributors under ODbL-1.0 and must be
attributed wherever it is shown.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from lq_snowflake.osm_categories import categories  # noqa: E402

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
ATTEMPTS_PER_URL = 2
USER_AGENT = "local-quest-hackathon-ingest/0.1"
# Pomona, CA (south, west, north, east), including Cal Poly Pomona.
POMONA_BBOX = (34.01, -117.83, 34.10, -117.71)
QUERY = """[out:json][timeout:180];
(
  nwr["opening_hours"]["name"]["amenity"]({bbox});
  nwr["opening_hours"]["name"]["shop"]({bbox});
  nwr["opening_hours"]["name"]["tourism"]({bbox});
  nwr["opening_hours"]["name"]["leisure"]({bbox});
  nwr["opening_hours"]["name"]["craft"]({bbox});
);
out center tags;"""


def parse_bbox(text):
    south, west, north, east = (float(x) for x in text.split(","))
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise argparse.ArgumentTypeError("bbox must be south,west,north,east")
    return south, west, north, east


def to_records(payload):
    snapshot = payload.get("osm3s", {}).get("timestamp_osm_base", "")[:10]
    if not snapshot:
        raise ValueError("Overpass response has no osm3s.timestamp_osm_base")
    seen = set()
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        labels = categories(tags)
        if labels is None:
            continue
        lat = element.get("lat", element.get("center", {}).get("lat"))
        lon = element.get("lon", element.get("center", {}).get("lon"))
        if lat is None or lon is None:
            continue
        osm_ref = f"{element['type']}/{element['id']}"
        if osm_ref in seen:
            continue
        seen.add(osm_ref)
        yield {
            "osm_ref": osm_ref,
            "name": tags.get("name"),
            "latitude": lat,
            "longitude": lon,
            "categories": labels,
            "address": address(tags),
            "website": tags.get("website") or tags.get("contact:website"),
            "opening_hours": tags.get("opening_hours"),
            "snapshot_date": snapshot,
        }


def address(tags):
    street = " ".join(p for p in (tags.get("addr:housenumber"), tags.get("addr:street")) if p)
    parts = [p for p in (street, tags.get("addr:city"), tags.get("addr:postcode")) if p]
    return ", ".join(parts) or None


def fetch(query):
    """POST the query, retrying transient failures on each mirror a bounded number of times."""
    data = urllib.parse.urlencode({"data": query}).encode()
    errors = []
    for url in OVERPASS_URLS:
        for attempt in range(ATTEMPTS_PER_URL):
            request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=240) as response:
                    return json.load(response)
            except (urllib.error.URLError, TimeoutError) as exc:
                errors.append(f"{url}: {exc}")
                time.sleep(5 * (attempt + 1))
    raise SystemExit("Overpass request failed:\n  " + "\n  ".join(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bbox", type=parse_bbox, default=POMONA_BBOX,
                        help="south,west,north,east (default: Pomona)")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    south, west, north, east = args.bbox
    query = QUERY.format(bbox=f"{south},{west},{north},{east}")
    payload = fetch(query)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with args.out.open("w", encoding="utf-8") as handle:
        for record in to_records(payload):
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    print(f"wrote {count} places to {args.out}")


if __name__ == "__main__":
    main()
