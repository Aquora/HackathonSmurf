"""Zip snowflake/python/lq_snowflake into snowflake/build/lq_snowflake.zip.

Usage (from the local-quest folder): python3 snowflake/scripts/build_package.py
Upload the zip to @APP.CODE, then run app/functions.sql (see README).
"""

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "python" / "lq_snowflake"
OUTPUT = ROOT / "build" / "lq_snowflake.zip"


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in SOURCE.rglob("*.py") if "__pycache__" not in p.parts)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(str(path.relative_to(SOURCE.parent)), date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    print(f"wrote {OUTPUT} ({len(files)} modules)")


if __name__ == "__main__":
    main()
