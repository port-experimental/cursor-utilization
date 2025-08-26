from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Tuple
import logging
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
    AiCommitMetric,
    AiCodeChangeMetric,
    AiCommitTotals,
    AiCodeChangeTotals,
    AiCommitRecord,
    AiCodeChangeRecord,
    AiCodeChangeFileMetadata,
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
) -> Tuple[List[TeamRecord], List[str]]:
    # Group user totals by team
    team_to_totals: Dict[str, TeamTotals] = {}
    team_model_counts: Dict[str, Counter] = defaultdict(Counter)
    team_to_user_identifiers: Dict[str, List[str]] = defaultdict(list)
    unmapped_users: List[str] = []

    for ur in user_records:
        if ur.totals.email not in email_to_team:
            unmapped_users.append(ur.totals.email)
            logging.warning(f"User '{ur.totals.email}' has no team mapping, assigning to 'unknown' team")
        
        team = email_to_team.get(ur.totals.email, "unknown")
        tt = team_to_totals.get(team)
        if tt is None:
            tt = TeamTotals(team=team)
            team_to_totals[team] = tt
        
        # Track user identifiers for this team (for relations)
        team_to_user_identifiers[team].append(ur.identifier)
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
        
        # Add team member identifiers to breakdown for potential relations
        breakdown = {
            "team_member_identifiers": team_to_user_identifiers[team]
        }
        
        team_records.append(
            TeamRecord(
                identifier=identifier,
                org=org,
                team=team,
                record_date_iso=date_iso,
                totals=tt,
                breakdown=breakdown,
            )
        )
    
    # Log validation summary
    if unmapped_users:
        logging.warning(f"Found {len(unmapped_users)} unmapped users. They were assigned to 'unknown' team.")
    
    return team_records, unmapped_users


def aggregate_ai_commits(
    org: str,
    date_epoch_ms: int,
    commits: Iterable[AiCommitMetric],
) -> List[AiCommitRecord]:
    """
    Aggregate AI commit metrics by user for a given day
    """
    # Group commits by user
    user_commits: Dict[str, List[AiCommitMetric]] = defaultdict(list)
    
    for commit in commits:
        user_email = commit.userEmail or "unknown"
        user_commits[user_email].append(commit)
    
    date_iso = epoch_ms_day_to_iso_utc(date_epoch_ms)
    commit_records: List[AiCommitRecord] = []
    
    for user_email, user_commit_list in user_commits.items():
        # Calculate totals for this user
        totals = AiCommitTotals()
        repos_counter: Counter = Counter()
        
        for commit in user_commit_list:
            totals.total_commits += 1
            totals.total_lines_added += commit.totalLinesAdded
            totals.total_lines_deleted += commit.totalLinesDeleted
            totals.tab_lines_added += commit.tabLinesAdded
            totals.tab_lines_deleted += commit.tabLinesDeleted
            totals.composer_lines_added += commit.composerLinesAdded
            totals.composer_lines_deleted += commit.composerLinesDeleted
            totals.non_ai_lines_added += commit.nonAiLinesAdded or 0
            totals.non_ai_lines_deleted += commit.nonAiLinesDeleted or 0
            
            if commit.isPrimaryBranch:
                totals.primary_branch_commits += 1
            
            if commit.repoName:
                repos_counter[commit.repoName] += 1
        
        totals.total_unique_repos = len(repos_counter)
        if repos_counter:
            totals.most_active_repo = repos_counter.most_common(1)[0][0]
        
        # Create breakdown with detailed commit info
        breakdown = {
            "commits": [c.model_dump() for c in user_commit_list],
            "repositories": dict(repos_counter),
            "ai_contribution_breakdown": {
                "tab_percentage": round((totals.tab_lines_added + totals.tab_lines_deleted) / 
                                      max(1, totals.total_lines_added + totals.total_lines_deleted) * 100, 2),
                "composer_percentage": round((totals.composer_lines_added + totals.composer_lines_deleted) / 
                                           max(1, totals.total_lines_added + totals.total_lines_deleted) * 100, 2),
                "non_ai_percentage": round((totals.non_ai_lines_added + totals.non_ai_lines_deleted) / 
                                         max(1, totals.total_lines_added + totals.total_lines_deleted) * 100, 2)
            }
        }
        
        identifier = f"cursor-ai-commits:{org}:{user_email}:{date_iso[:10]}"
        
        commit_records.append(
            AiCommitRecord(
                identifier=identifier,
                org=org,
                user_email=user_email,
                record_date_iso=date_iso,
                totals=totals,
                breakdown=breakdown,
            )
        )
    
    return commit_records


def aggregate_ai_code_changes(
    org: str,
    date_epoch_ms: int,
    changes: Iterable[AiCodeChangeMetric],
) -> List[AiCodeChangeRecord]:
    """
    Aggregate AI code change metrics by user for a given day
    """
    # Group changes by user
    user_changes: Dict[str, List[AiCodeChangeMetric]] = defaultdict(list)
    
    for change in changes:
        user_email = change.userEmail or "unknown"
        user_changes[user_email].append(change)
    
    date_iso = epoch_ms_day_to_iso_utc(date_epoch_ms)
    change_records: List[AiCodeChangeRecord] = []
    
    for user_email, user_change_list in user_changes.items():
        # Calculate totals for this user
        totals = AiCodeChangeTotals()
        model_counter: Counter = Counter()
        extension_counter: Counter = Counter()
        source_counter: Counter = Counter()
        
        for change in user_change_list:
            totals.total_changes += 1
            totals.total_lines_added += change.totalLinesAdded
            totals.total_lines_deleted += change.totalLinesDeleted
            
            # Count by source
            source_counter[change.source] += 1
            if change.source == "TAB":
                totals.tab_changes += 1
                totals.tab_lines_added += change.totalLinesAdded
                totals.tab_lines_deleted += change.totalLinesDeleted
            elif change.source == "COMPOSER":
                totals.composer_changes += 1
                totals.composer_lines_added += change.totalLinesAdded
                totals.composer_lines_deleted += change.totalLinesDeleted
            
            # Count models
            if change.model:
                model_counter[change.model] += 1
            
            # Count file extensions
            for file_meta in change.metadata:
                if file_meta.fileExtension:
                    extension_counter[file_meta.fileExtension] += 1
        
        totals.unique_file_extensions = len(extension_counter)
        if model_counter:
            totals.most_used_model = model_counter.most_common(1)[0][0]
        
        # Create breakdown with detailed change info
        breakdown = {
            "changes": [c.model_dump() for c in user_change_list],
            "source_distribution": dict(source_counter),
            "model_usage": dict(model_counter),
            "file_extensions": dict(extension_counter),
            "productivity_metrics": {
                "average_lines_per_change": round((totals.total_lines_added + totals.total_lines_deleted) / 
                                                max(1, totals.total_changes), 2),
                "tab_vs_composer_ratio": round(totals.tab_changes / max(1, totals.composer_changes), 2) if totals.composer_changes > 0 else None,
                "tab_efficiency": round((totals.tab_lines_added + totals.tab_lines_deleted) / max(1, totals.tab_changes), 2),
                "composer_efficiency": round((totals.composer_lines_added + totals.composer_lines_deleted) / max(1, totals.composer_changes), 2)
            }
        }
        
        identifier = f"cursor-ai-changes:{org}:{user_email}:{date_iso[:10]}"
        
        change_records.append(
            AiCodeChangeRecord(
                identifier=identifier,
                org=org,
                user_email=user_email,
                record_date_iso=date_iso,
                totals=totals,
                breakdown=breakdown,
            )
        )
    
    return change_records

