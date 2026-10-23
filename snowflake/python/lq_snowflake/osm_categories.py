"""Derive normalized category labels from OpenStreetMap tags (used by ingest)."""

CATEGORY_KEYS = ("amenity", "shop", "tourism", "leisure", "craft", "cuisine")

# Tagged features that are not visitable local businesses for a quest.
EXCLUDED = {
    ("amenity", v) for v in (
        "atm", "bench", "bicycle_parking", "charging_station", "clinic", "dentist",
        "doctors", "drinking_water", "fuel", "hospital", "kindergarten", "parking",
        "parking_entrance", "place_of_worship", "police", "post_box", "recycling",
        "school", "shelter", "social_facility", "telephone", "toilets",
        "vending_machine", "waste_basket",
    )
}


def normalize(label):
    return " ".join(label.strip().lower().replace("_", " ").split())


def categories(tags):
    """Return ordered unique labels, or None when the feature should be skipped."""
    labels = []
    found_business_key = False
    for key in CATEGORY_KEYS:
        raw = tags.get(key)
        if not raw:
            continue
        for value in raw.split(";"):
            value = value.strip()
            if not value or value in ("yes", "no"):
                continue
            if (key, value) in EXCLUDED:
                return None
            if key != "cuisine":
                found_business_key = True
            label = normalize(value)
            if key == "shop" and not label.endswith("shop"):
                label = f"{label} shop"
            if label not in labels:
                labels.append(label)
    return labels if found_business_key else None
