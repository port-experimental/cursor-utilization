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
    # Relation target configurations
    user_blueprint: str
    service_blueprint: str
    github_pull_request_blueprint: str
    # Rate limiting configuration
    rate_limit_requests_per_minute: int
    rate_limit_delay_between_pages: float


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
        # Relation target configurations with defaults
        user_blueprint=os.environ.get("USER_BLUEPRINT", "_user"),
        service_blueprint=os.environ.get("SERVICE_BLUEPRINT", "service"),
        github_pull_request_blueprint=os.environ.get("GITHUB_PULL_REQUEST_BLUEPRINT", "githubPullRequest"),
        # Rate limiting configuration
        rate_limit_requests_per_minute=int(os.environ.get("RATE_LIMIT_REQUESTS_PER_MINUTE", "55")),
        rate_limit_delay_between_pages=float(os.environ.get("RATE_LIMIT_DELAY_BETWEEN_PAGES", "1.5")),
    )