"""Run the API: `python -m app`. Reads settings from the environment and `.env`."""

import json
import logging
import sys

import uvicorn

from .config import ConfigError, load_settings
from .container import build_app


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {"time": self.formatTime(record), "level": record.levelname.lower(), "logger": record.name, "msg": record.getMessage()}
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def main() -> None:
    try:
        settings = load_settings()
    except ConfigError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    handler = logging.StreamHandler()
    if settings.APP_ENV == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=settings.LOG_LEVEL.upper(), handlers=[handler], force=True)
    # Quiet the connector's verbose INFO logs.
    logging.getLogger("snowflake.connector").setLevel(logging.WARNING)

    if settings.uses_mock:
        logging.getLogger("app").warning(
            "running with MOCK adapters (ai=%s, data=%s); responses are labeled mock: true",
            settings.AI_PROVIDER,
            settings.DATA_PROVIDER,
        )

    try:
        app = build_app(settings)
    except ConfigError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_config=None,
        access_log=False,  # the app logs requests itself, without bodies
        proxy_headers=settings.TRUST_PROXY,
        forwarded_allow_ips="*" if settings.TRUST_PROXY else None,
        timeout_graceful_shutdown=10,
        server_header=False,
    )


if __name__ == "__main__":
    main()
