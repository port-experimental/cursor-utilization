from __future__ import annotations

import argparse
import logging
from typing import Dict, List, Optional
import pendulum as pdt

from .config import load_config
from .cursor_adapter import CursorAdapter
from .models import DailyUserSummary, UsageEvent
from .aggregate import aggregate_daily, aggregate_teams
from .port_exporter import PortExporter

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
    logging.info(f"Starting Cursor → Port sync: mode={mode}, days={days}")
    
    cfg = load_config()
    logging.info(f"Configuration loaded - org: {cfg.org_identifier}, dry_run: {cfg.dry_run}")
    
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
    logging.info(f"Processing {len(day_starts)} days: {[pdt.from_timestamp(d/1000).to_date_string() for d in day_starts]}")

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

    for i, day_start in enumerate(day_starts, 1):
        day_end = day_start + 24 * 60 * 60 * 1000 - 1
        day_str = pdt.from_timestamp(day_start/1000).to_date_string()
        
        logging.info(f"Processing day {i}/{len(day_starts)}: {day_str}")

        try:
            daily_data = cursor.get_daily_usage(day_start, day_end)
            summaries = [DailyUserSummary(**d) for d in daily_data]
            logging.info(f"  Retrieved {len(summaries)} user summaries from Cursor API")

            # Optional: events for cost/tokens
            # Page through until exhausted
            events: List[UsageEvent] = []
            page = 1
            total_events = 0
            while True:
                ev = cursor.get_filtered_usage_events(start_epoch_ms=day_start, end_epoch_ms=day_end, page=page, page_size=200)
                usage_events = ev.get("usageEvents", [])
                if not usage_events:
                    break
                events.extend(UsageEvent(**e) for e in usage_events)
                total_events += len(usage_events)
                pagination = ev.get("pagination", {})
                if not pagination.get("hasNextPage"):
                    break
                page += 1
            logging.info(f"  Retrieved {total_events} usage events from Cursor API")
            


            org_record, user_records = aggregate_daily(cfg.org_identifier, day_start, summaries, events)
            logging.info(f"  Aggregated data: 1 org record, {len(user_records)} user records")

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
                logging.info("  Applied email anonymization")

            team_records = []
            if email_to_team:
                team_records = aggregate_teams(cfg.org_identifier, day_start, user_records, email_to_team)
                logging.info(f"  Generated {len(team_records)} team records")

            if cfg.dry_run:
                logging.info("  DRY RUN: Skipping Port API export")
            else:
                logging.info("  Exporting to Port API...")
            
            exporter.export_org_users_teams(org_record, user_records, team_records)
            
            if not cfg.dry_run:
                logging.info("  ✓ Successfully exported to Port")
                
        except Exception as e:
            logging.error(f"  ✗ Failed processing {day_str}: {e}")
            raise
    
    logging.info("🎉 Cursor → Port sync completed successfully!")


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
