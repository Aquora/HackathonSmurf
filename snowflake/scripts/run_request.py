"""Run a request JSON through the handler (synthetic fixtures) and emit the result JSON.

    python3 snowflake/scripts/run_request.py [REQUEST.json] [-o OUT.json]

With -o NAME.expected.json next to NAME.request.json in tests/cases/, the output
becomes that case's expected file. Review it before committing: it records what the
code does now, not what is correct. Places come from tests/support.py (fictional).
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "python"))

from lq_snowflake import procedure  # noqa: E402
from lq_snowflake.request import InvalidInput  # noqa: E402
from test_procedure import FakeSession  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("request", nargs="?", default=str(ROOT / "tests" / "cases" / "demo.request.json"),
                        help="request JSON (default: tests/cases/demo.request.json)")
    parser.add_argument("-o", "--output", help="write JSON here instead of stdout")
    args = parser.parse_args()

    payload = json.loads(Path(args.request).read_text())
    try:
        result = procedure.get_candidates(FakeSession(), payload)
        result.pop("retrieved_at", None)
    except InvalidInput as exc:
        print(f"rejected: {exc}", file=sys.stderr)
        result = {"error": "InvalidInput"}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text)
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
