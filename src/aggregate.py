from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Tuple
import pendulum as pdt

from .models import (
    DailyUserSummary,
    UsageEvent,
    OrgTotals,
    UserTotals,
    OrgRecord,
    UserRecord,
    TeamRecord,
    TeamTotals,
)


def epoch_ms_day_to_iso_utc(epoch_ms: int) -> str:
    return pdt.from_timestamp(epoch_ms / 1000, tz="UTC").to_date_string() + "T00:00:00Z"


def aggregate_daily(
    org: str,
    date_epoch_ms: int,
    summaries: Iterable[DailyUserSummary],
    events: Iterable[UsageEvent],
) -> Tuple[OrgRecord, List[UserRecord]]:
    # Map user -> UserTotals
    user_totals: Dict[str, UserTotals] = {}
    models_counter: Counter = Counter()

    # Aggregate from summaries (lines/events)
    for s in summaries:
        email = s.email or "unknown"
        ut = user_totals.get(email)
        if ut is None:
            ut = UserTotals(email=email, is_active=s.isActive)
            user_totals[email] = ut
        else:
            ut.is_active = ut.is_active or s.isActive

        ut.total_accepts += s.totalAccepts
        ut.total_rejects += s.totalRejects
        ut.total_tabs_shown += s.totalTabsShown
        ut.total_tabs_accepted += s.totalTabsAccepted
        ut.total_lines_added += s.totalLinesAdded
        ut.total_lines_deleted += s.totalLinesDeleted
        ut.accepted_lines_added += s.acceptedLinesAdded
        ut.accepted_lines_deleted += s.acceptedLinesDeleted
        ut.composer_requests += s.composerRequests
        ut.chat_requests += s.chatRequests
        ut.agent_requests += s.agentRequests
        ut.subscription_included_reqs += s.subscriptionIncludedReqs
        ut.api_key_reqs += s.apiKeyReqs
        ut.usage_based_reqs += s.usageBasedReqs
        ut.bugbot_usages += s.bugbotUsages
        if s.mostUsedModel:
            ut.most_used_model = s.mostUsedModel
            models_counter[s.mostUsedModel] += 1

    # Aggregate from events (tokens/costs + model freq)
    for e in events:
        email = e.userEmail or "unknown"
        ut = user_totals.get(email)
        if ut is None:
            ut = UserTotals(email=email, is_active=True)
            user_totals[email] = ut
        if e.model:
            models_counter[e.model] += 1
            ut.most_used_model = ut.most_used_model or e.model
        if e.tokenUsage:
            ut.input_tokens += e.tokenUsage.inputTokens
            ut.output_tokens += e.tokenUsage.outputTokens
            ut.cache_write_tokens += e.tokenUsage.cacheWriteTokens
            ut.cache_read_tokens += e.tokenUsage.cacheReadTokens
            ut.total_cents += float(e.tokenUsage.totalCents or 0.0)

    # Build org totals
    org_totals = OrgTotals()
    for ut in user_totals.values():
        org_totals.total_accepts += ut.total_accepts
        org_totals.total_rejects += ut.total_rejects
        org_totals.total_tabs_shown += ut.total_tabs_shown
        org_totals.total_tabs_accepted += ut.total_tabs_accepted
        org_totals.total_lines_added += ut.total_lines_added
        org_totals.total_lines_deleted += ut.total_lines_deleted
        org_totals.accepted_lines_added += ut.accepted_lines_added
        org_totals.accepted_lines_deleted += ut.accepted_lines_deleted
        org_totals.composer_requests += ut.composer_requests
        org_totals.chat_requests += ut.chat_requests
        org_totals.agent_requests += ut.agent_requests
        org_totals.subscription_included_reqs += ut.subscription_included_reqs
        org_totals.api_key_reqs += ut.api_key_reqs
        org_totals.usage_based_reqs += ut.usage_based_reqs
        org_totals.bugbot_usages += ut.bugbot_usages
        if ut.is_active:
            org_totals.total_active_users += 1
        org_totals.total_input_tokens += ut.input_tokens
        org_totals.total_output_tokens += ut.output_tokens
        org_totals.total_cache_write_tokens += ut.cache_write_tokens
        org_totals.total_cache_read_tokens += ut.cache_read_tokens
        org_totals.total_cents += ut.total_cents

    if models_counter:
        org_totals.most_used_model = models_counter.most_common(1)[0][0]

    date_iso = epoch_ms_day_to_iso_utc(date_epoch_ms)
    org_identifier = f"cursor:{org}:{date_iso[:10]}"

    org_breakdown: Dict[str, Any] = {
        "users": [u.model_dump() for u in user_totals.values()]
    }

    org_record = OrgRecord(
        identifier=org_identifier,
        org=org,
        record_date_iso=date_iso,
        totals=org_totals,
        breakdown=org_breakdown,
    )

    user_records: List[UserRecord] = []
    for ut in user_totals.values():
        user_id = f"cursor:{org}:{ut.email}:{date_iso[:10]}"
        user_records.append(
            UserRecord(
                identifier=user_id,
                org=org,
                record_date_iso=date_iso,
                totals=ut,
                breakdown={},
            )
        )

    return org_record, user_records


def aggregate_teams(
    org: str,
    date_epoch_ms: int,
    user_records: List[UserRecord],
    email_to_team: Dict[str, str],
) -> List[TeamRecord]:
    # Group user totals by team
    team_to_totals: Dict[str, TeamTotals] = {}
    team_model_counts: Dict[str, Counter] = defaultdict(Counter)

    for ur in user_records:
        team = email_to_team.get(ur.totals.email, "unknown")
        tt = team_to_totals.get(team)
        if tt is None:
            tt = TeamTotals(team=team)
            team_to_totals[team] = tt
        if ur.totals.is_active:
            tt.total_active_users += 1
        tt.total_accepts += ur.totals.total_accepts
        tt.total_rejects += ur.totals.total_rejects
        tt.total_tabs_shown += ur.totals.total_tabs_shown
        tt.total_tabs_accepted += ur.totals.total_tabs_accepted
        tt.total_lines_added += ur.totals.total_lines_added
        tt.total_lines_deleted += ur.totals.total_lines_deleted
        tt.accepted_lines_added += ur.totals.accepted_lines_added
        tt.accepted_lines_deleted += ur.totals.accepted_lines_deleted
        tt.composer_requests += ur.totals.composer_requests
        tt.chat_requests += ur.totals.chat_requests
        tt.agent_requests += ur.totals.agent_requests
        tt.subscription_included_reqs += ur.totals.subscription_included_reqs
        tt.api_key_reqs += ur.totals.api_key_reqs
        tt.usage_based_reqs += ur.totals.usage_based_reqs
        tt.bugbot_usages += ur.totals.bugbot_usages
        tt.input_tokens += ur.totals.input_tokens
        tt.output_tokens += ur.totals.output_tokens
        tt.cache_write_tokens += ur.totals.cache_write_tokens
        tt.cache_read_tokens += ur.totals.cache_read_tokens
        tt.total_cents += ur.totals.total_cents
        if ur.totals.most_used_model:
            team_model_counts[team][ur.totals.most_used_model] += 1

    date_iso = epoch_ms_day_to_iso_utc(date_epoch_ms)
    team_records: List[TeamRecord] = []
    for team, tt in team_to_totals.items():
        if team_model_counts[team]:
            tt.most_used_model = team_model_counts[team].most_common(1)[0][0]
        identifier = f"cursor:{org}:{team}:{date_iso[:10]}"
        team_records.append(
            TeamRecord(
                identifier=identifier,
                org=org,
                team=team,
                record_date_iso=date_iso,
                totals=tt,
                breakdown={},
            )
        )
    return team_records

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Any

import pendulum as pdt

from .models import DailyUserSummary, OrgTotals


def to_iso_utc(date_epoch_ms: int) -> str:
    return pdt.from_timestamp(date_epoch_ms / 1000, tz="UTC").start_of("day").to_iso8601_string()


def org_aggregate(org: str, daily_users: List[DailyUserSummary]) -> OrgTotals:
    totals: Dict[str, int] = defaultdict(int)
    active_users = set()
    model_counter: Counter[str] = Counter()

    for u in daily_users:
        if u.is_active:
            active_users.add(u.email)

        totals["total_accepts"] += u.total_accepts
        totals["total_rejects"] += u.total_rejects
        totals["total_tabs_shown"] += u.total_tabs_shown
        totals["total_tabs_accepted"] += u.total_tabs_accepted
        totals["total_lines_added"] += u.total_lines_added
        totals["total_lines_deleted"] += u.total_lines_deleted
        totals["accepted_lines_added"] += u.accepted_lines_added
        totals["accepted_lines_deleted"] += u.accepted_lines_deleted
        totals["composer_requests"] += u.composer_requests
        totals["chat_requests"] += u.chat_requests
        totals["agent_requests"] += u.agent_requests
        totals["subscription_included_reqs"] += u.subscription_included_reqs
        totals["api_key_reqs"] += u.api_key_reqs
        totals["usage_based_reqs"] += u.usage_based_reqs
        totals["bugbot_usages"] += u.bugbot_usages

        totals["total_input_tokens"] += u.total_input_tokens
        totals["total_output_tokens"] += u.total_output_tokens
        totals["total_cache_write_tokens"] += u.total_cache_write_tokens
        totals["total_cache_read_tokens"] += u.total_cache_read_tokens
        totals["total_cents"] += int(round(u.total_cents * 100)) / 100  # keep cents precision

        if u.most_used_model:
            model_counter[u.most_used_model] += 1

    most_used_model = model_counter.most_common(1)[0][0] if model_counter else None

    # assumes all daily_users correspond to the same date
    record_date_iso = to_iso_utc(daily_users[0].date_epoch_ms) if daily_users else pdt.now("UTC").start_of("day").to_iso8601_string()

    breakdown_users: List[Dict[str, Any]] = [
        {
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
        }
        for u in daily_users
    ]

    return OrgTotals(
        record_date_iso=record_date_iso,
        org=org,
        total_accepts=totals["total_accepts"],
        total_rejects=totals["total_rejects"],
        total_tabs_shown=totals["total_tabs_shown"],
        total_tabs_accepted=totals["total_tabs_accepted"],
        total_lines_added=totals["total_lines_added"],
        total_lines_deleted=totals["total_lines_deleted"],
        accepted_lines_added=totals["accepted_lines_added"],
        accepted_lines_deleted=totals["accepted_lines_deleted"],
        composer_requests=totals["composer_requests"],
        chat_requests=totals["chat_requests"],
        agent_requests=totals["agent_requests"],
        subscription_included_reqs=totals["subscription_included_reqs"],
        api_key_reqs=totals["api_key_reqs"],
        usage_based_reqs=totals["usage_based_reqs"],
        bugbot_usages=totals["bugbot_usages"],
        most_used_model=most_used_model,
        total_active_users=len(active_users),
        total_input_tokens=totals["total_input_tokens"],
        total_output_tokens=totals["total_output_tokens"],
        total_cache_write_tokens=totals["total_cache_write_tokens"],
        total_cache_read_tokens=totals["total_cache_read_tokens"],
        total_cents=totals["total_cents"],
        breakdown={"users": breakdown_users},
    )


