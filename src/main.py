from __future__ import annotations

import argparse
from typing import Dict, List, Optional
import pendulum as pdt

from .config import load_config
from .cursor_adapter import CursorAdapter
from .models import DailyUserSummary, UsageEvent
from .aggregate import aggregate_daily, aggregate_teams
from .port_exporter import PortExporter


def slice_days_utc(days: int, start_utc: Optional[str] = None, end_utc: Optional[str] = None) -> List[int]:
    # Return epoch ms for each day start in UTC for last `days` days
    if start_utc and end_utc:
        start = pdt.parse(start_utc).start_of("day").in_timezone("UTC")
        end = pdt.parse(end_utc).start_of("day").in_timezone("UTC")
        total_days = (end - start).in_days() + 1
        return [int(start.add(days=i).int_timestamp * 1000) for i in range(total_days)]
    now = pdt.now("UTC").start_of("day")
    return [int(now.subtract(days=i).int_timestamp * 1000) for i in range(days)][::-1]


def run(mode: str, days: int, start_utc: Optional[str], end_utc: Optional[str], email_to_team_path: Optional[str], anonymize: bool) -> None:
    cfg = load_config()
    cursor = CursorAdapter(api_key=cfg.cursor_api_key)
    exporter = PortExporter(
        base_url=cfg.port_base_url,
        auth_url=cfg.port_auth_url,
        bulk_upsert_url=cfg.port_bulk_upsert_url,
        client_id=cfg.port_client_id,
        client_secret=cfg.port_client_secret,
        dry_run=cfg.dry_run,
    )

    # Determine day windows in UTC
    day_starts = slice_days_utc(days, start_utc, end_utc)

    # Optional team mapping
    email_to_team: Dict[str, str] = {}
    if email_to_team_path:
        import json, yaml, os
        if os.path.exists(email_to_team_path):
            with open(email_to_team_path, "r", encoding="utf-8") as f:
                content = f.read()
                try:
                    email_to_team = json.loads(content)
                except Exception:
                    email_to_team = yaml.safe_load(content)

    for day_start in day_starts:
        day_end = day_start + 24 * 60 * 60 * 1000 - 1

        daily_data = cursor.get_daily_usage(day_start, day_end)
        summaries = [DailyUserSummary(**d) for d in daily_data]

        # Optional: events for cost/tokens
        # Page through until exhausted
        events: List[UsageEvent] = []
        page = 1
        while True:
            ev = cursor.get_filtered_usage_events(start_epoch_ms=day_start, end_epoch_ms=day_end, page=page, page_size=200)
            usage_events = ev.get("usageEvents", [])
            if not usage_events:
                break
            events.extend(UsageEvent(**e) for e in usage_events)
            pagination = ev.get("pagination", {})
            if not pagination.get("hasNextPage"):
                break
            page += 1

        org_record, user_records = aggregate_daily(cfg.org_identifier, day_start, summaries, events)

        if anonymize:
            # Hash emails in user records and breakdowns
            import hashlib
            for ur in user_records:
                original = ur.totals.email
                hashed = hashlib.sha256(original.encode("utf-8")).hexdigest()
                ur.totals.email = hashed
            if "users" in org_record.breakdown:
                for u in org_record.breakdown["users"]:
                    if "email" in u:
                        u["email"] = hashlib.sha256(str(u["email"]).encode("utf-8")).hexdigest()

        team_records = []
        if email_to_team:
            team_records = aggregate_teams(cfg.org_identifier, day_start, user_records, email_to_team)

        exporter.export_org_users_teams(org_record, user_records, team_records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cursor → Port utilization sync")
    parser.add_argument("--mode", choices=["daily", "backfill"], default="daily")
    parser.add_argument("--days", type=int, default=1, help="Number of days to process (UTC)")
    parser.add_argument("--start", type=str, default=None, help="Start date (YYYY-MM-DD) UTC")
    parser.add_argument("--end", type=str, default=None, help="End date (YYYY-MM-DD) UTC")
    parser.add_argument("--team-map", type=str, default=None, help="Path to JSON/YAML mapping { email: team }")
    parser.add_argument("--anonymize-emails", action="store_true", help="Hash emails before export")
    args = parser.parse_args()

    run(mode=args.mode, days=args.days, start_utc=args.start, end_utc=args.end, email_to_team_path=args.team_map, anonymize=args.anonymize_emails)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import asyncio
from typing import List, Dict, Any

import pendulum as pdt

from .config import load_settings
from .cursor_adapter import CursorAdapter
from .models import DailyUserSummary
from .aggregate import org_aggregate
from .port_exporter import PortExporter


def slice_dates_utc(start: pdt.DateTime, end: pdt.DateTime) -> List[pdt.DateTime]:
    days = []
    cur = start.start_of("day")
    while cur <= end.start_of("day"):
        days.append(cur)
        cur = cur.add(days=1)
    return days


async def run_once(mode: str, num_days: int) -> None:
    cfg = load_settings()
    adapter = CursorAdapter(cfg.cursor_api_key)
    exporter = PortExporter(
        base_url=cfg.port_base_url,
        auth_url=cfg.port_auth_url,
        bulk_upsert_url=cfg.port_bulk_upsert_url,
        client_id=cfg.port_client_id,
        client_secret=cfg.port_client_secret,
    )

    end = pdt.now("UTC").start_of("day") if mode == "daily" else pdt.now("UTC").start_of("day")
    start = end.subtract(days=(num_days - 1))

    for day in slice_dates_utc(start, end):
        start_ms = int(day.start_of("day").timestamp() * 1000)
        end_ms = int(day.end_of("day").timestamp() * 1000)

        daily_rows = await adapter.get_daily_usage(start_ms, end_ms)

        daily_users: List[DailyUserSummary] = []
        for row in daily_rows:
            # Cursor may return rows with or without email; ensure presence
            email = row.get("email") or "unknown@example.com"
            dus = DailyUserSummary(
                date_epoch_ms=row["date"],
                email=email,
                is_active=row.get("isActive", False),
                total_lines_added=row.get("totalLinesAdded", 0),
                total_lines_deleted=row.get("totalLinesDeleted", 0),
                accepted_lines_added=row.get("acceptedLinesAdded", 0),
                accepted_lines_deleted=row.get("acceptedLinesDeleted", 0),
                total_accepts=row.get("totalAccepts", 0),
                total_rejects=row.get("totalRejects", 0),
                total_tabs_shown=row.get("totalTabsShown", 0),
                total_tabs_accepted=row.get("totalTabsAccepted", 0),
                composer_requests=row.get("composerRequests", 0),
                chat_requests=row.get("chatRequests", 0),
                agent_requests=row.get("agentRequests", 0),
                subscription_included_reqs=row.get("subscriptionIncludedReqs", 0),
                api_key_reqs=row.get("apiKeyReqs", 0),
                usage_based_reqs=row.get("usageBasedReqs", 0),
                bugbot_usages=row.get("bugbotUsages", 0),
                most_used_model=row.get("mostUsedModel"),
            )

            # Enrich with token/costs by fetching usage events for that user/day (optional)
            # We page until no next page. Keep modest page size to bound time.
            page = 1
            total_input = total_output = total_cw = total_cr = 0
            total_cents = 0.0
            while True:
                events_resp = await adapter.get_filtered_usage_events(
                    start_epoch_ms=start_ms,
                    end_epoch_ms=end_ms,
                    email=email,
                    page=page,
                    page_size=100,
                )
                events = events_resp.get("usageEvents", [])
                for ev in events:
                    tu = ev.get("tokenUsage") or {}
                    total_input += int(tu.get("inputTokens", 0) or 0)
                    total_output += int(tu.get("outputTokens", 0) or 0)
                    total_cw += int(tu.get("cacheWriteTokens", 0) or 0)
                    total_cr += int(tu.get("cacheReadTokens", 0) or 0)
                    total_cents += float(tu.get("totalCents", 0.0) or 0.0)
                pagination = events_resp.get("pagination") or {}
                if not pagination.get("hasNextPage"):
                    break
                page = int(pagination.get("currentPage", page)) + 1

            dus.total_input_tokens = total_input
            dus.total_output_tokens = total_output
            dus.total_cache_write_tokens = total_cw
            dus.total_cache_read_tokens = total_cr
            dus.total_cents = round(total_cents, 6)

            daily_users.append(dus)

        # Aggregate org-level
        org_totals = org_aggregate(cfg.org_identifier, daily_users)

        # Build Port bulk upsert payload (org + per-user)
        entities: List[Dict[str, Any]] = []

        org_id = f"cursor:{cfg.org_identifier}:{day.to_date_string()}"
        entities.append(
            {
                "entity": {
                    "identifier": org_id,
                    "title": org_id,
                    "blueprint": "cursor_usage_record",
                    "properties": {
                        "record_date": org_totals.record_date_iso,
                        "org": cfg.org_identifier,
                        "total_accepts": org_totals.total_accepts,
                        "total_rejects": org_totals.total_rejects,
                        "total_tabs_shown": org_totals.total_tabs_shown,
                        "total_tabs_accepted": org_totals.total_tabs_accepted,
                        "total_lines_added": org_totals.total_lines_added,
                        "total_lines_deleted": org_totals.total_lines_deleted,
                        "accepted_lines_added": org_totals.accepted_lines_added,
                        "accepted_lines_deleted": org_totals.accepted_lines_deleted,
                        "composer_requests": org_totals.composer_requests,
                        "chat_requests": org_totals.chat_requests,
                        "agent_requests": org_totals.agent_requests,
                        "subscription_included_reqs": org_totals.subscription_included_reqs,
                        "api_key_reqs": org_totals.api_key_reqs,
                        "usage_based_reqs": org_totals.usage_based_reqs,
                        "bugbot_usages": org_totals.bugbot_usages,
                        "most_used_model": org_totals.most_used_model,
                        "total_active_users": org_totals.total_active_users,
                        "total_input_tokens": org_totals.total_input_tokens,
                        "total_output_tokens": org_totals.total_output_tokens,
                        "total_cache_write_tokens": org_totals.total_cache_write_tokens,
                        "total_cache_read_tokens": org_totals.total_cache_read_tokens,
                        "total_cents": org_totals.total_cents,
                        "breakdown": org_totals.breakdown,
                    },
                }
            }
        )

        for u in daily_users:
            user_id = f"cursor:{cfg.org_identifier}:{u.email}:{day.to_date_string()}"
            entities.append(
                {
                    "entity": {
                        "identifier": user_id,
                        "title": user_id,
                        "blueprint": "cursor_user_usage_record",
                        "properties": {
                            "record_date": org_totals.record_date_iso,
                            "org": cfg.org_identifier,
                            "email": u.email,
                            "is_active": u.is_active,
                            "total_accepts": u.total_accepts,
                            "total_rejects": u.total_rejects,
                            "total_tabs_shown": u.total_tabs_shown,
                            "total_tabs_accepted": u.total_tabs_accepted,
                            "total_lines_added": u.total_lines_added,
                            "total_lines_deleted": u.total_lines_deleted,
                            "accepted_lines_added": u.accepted_lines_added,
                            "accepted_lines_deleted": u.accepted_lines_deleted,
                            "composer_requests": u.composer_requests,
                            "chat_requests": u.chat_requests,
                            "agent_requests": u.agent_requests,
                            "subscription_included_reqs": u.subscription_included_reqs,
                            "api_key_reqs": u.api_key_reqs,
                            "usage_based_reqs": u.usage_based_reqs,
                            "bugbot_usages": u.bugbot_usages,
                            "most_used_model": u.most_used_model,
                            "total_input_tokens": u.total_input_tokens,
                            "total_output_tokens": u.total_output_tokens,
                            "total_cache_write_tokens": u.total_cache_write_tokens,
                            "total_cache_read_tokens": u.total_cache_read_tokens,
                            "total_cents": u.total_cents,
                        },
                    }
                }
            )

        payload = {"entities": entities}

        if not cfg.dry_run:
            await exporter.bulk_upsert(payload)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Cursor → Port daily ingestion (UTC)")
    ap.add_argument("--mode", choices=["daily", "backfill"], default="daily")
    ap.add_argument("--days", type=int, default=1, help="Number of days to process")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_once(args.mode, args.days))


if __name__ == "__main__":
    main()


