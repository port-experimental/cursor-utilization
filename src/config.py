from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class AppConfig:
    cursor_api_key: str
    port_client_id: str
    port_client_secret: str
    port_base_url: str
    port_auth_url: str
    org_identifier: str
    timezone: str
    lookback_days: int
    dry_run: bool


def load_config() -> AppConfig:
    load_dotenv()

    return AppConfig(
        cursor_api_key=os.environ["X_CURSOR_API_KEY"],
        port_client_id=os.environ.get("PORT_CLIENT_ID", ""),
        port_client_secret=os.environ.get("PORT_CLIENT_SECRET", ""),
        port_base_url=os.environ.get("PORT_BASE_URL", "https://api.getport.io"),
        port_auth_url=os.environ.get("PORT_AUTH_URL", "https://api.getport.io/v1/auth/access_token"),
        org_identifier=os.environ["ORG_IDENTIFIER"],
        timezone=os.environ.get("TIMEZONE", "UTC"),
        lookback_days=int(os.environ.get("LOOKBACK_DAYS", "1")),
        dry_run=os.environ.get("DRY_RUN", "false").lower() == "true",
    )