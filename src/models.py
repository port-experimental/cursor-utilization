from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DailyUserSummary(BaseModel):
    # Derived from Cursor Admin API /teams/daily-usage-data
    date: int
    email: Optional[str] = None
    isActive: bool
    totalLinesAdded: int = 0
    totalLinesDeleted: int = 0
    acceptedLinesAdded: int = 0
    acceptedLinesDeleted: int = 0
    totalApplies: int = 0
    totalAccepts: int = 0
    totalRejects: int = 0
    totalTabsShown: int = 0
    totalTabsAccepted: int = 0
    composerRequests: int = 0
    chatRequests: int = 0
    agentRequests: int = 0
    cmdkUsages: int = 0
    subscriptionIncludedReqs: int = 0
    apiKeyReqs: int = 0
    usageBasedReqs: int = 0
    bugbotUsages: int = 0
    mostUsedModel: Optional[str] = None
    applyMostUsedExtension: Optional[str] = None
    tabMostUsedExtension: Optional[str] = None
    clientVersion: Optional[str] = None


class UsageEventTokenUsage(BaseModel):
    inputTokens: int = 0
    outputTokens: int = 0
    cacheWriteTokens: int = 0
    cacheReadTokens: int = 0
    totalCents: float = 0.0


class UsageEvent(BaseModel):
    # Derived from Cursor Admin API /teams/filtered-usage-events
    timestamp: str
    model: Optional[str] = None
    kind: Optional[str] = None
    maxMode: Optional[bool] = None
    requestsCosts: Optional[float] = None
    isTokenBasedCall: Optional[bool] = None
    tokenUsage: Optional[UsageEventTokenUsage] = None
    isFreeBugbot: Optional[bool] = None
    userEmail: Optional[str] = None


class OrgTotals(BaseModel):
    total_accepts: int = 0
    total_rejects: int = 0
    total_tabs_shown: int = 0
    total_tabs_accepted: int = 0
    total_lines_added: int = 0
    total_lines_deleted: int = 0
    accepted_lines_added: int = 0
    accepted_lines_deleted: int = 0
    composer_requests: int = 0
    chat_requests: int = 0
    agent_requests: int = 0
    subscription_included_reqs: int = 0
    api_key_reqs: int = 0
    usage_based_reqs: int = 0
    bugbot_usages: int = 0
    total_active_users: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cents: float = 0.0
    most_used_model: Optional[str] = None


class UserTotals(BaseModel):
    email: str
    is_active: bool
    total_accepts: int = 0
    total_rejects: int = 0
    total_tabs_shown: int = 0
    total_tabs_accepted: int = 0
    total_lines_added: int = 0
    total_lines_deleted: int = 0
    accepted_lines_added: int = 0
    accepted_lines_deleted: int = 0
    composer_requests: int = 0
    chat_requests: int = 0
    agent_requests: int = 0
    subscription_included_reqs: int = 0
    api_key_reqs: int = 0
    usage_based_reqs: int = 0
    bugbot_usages: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    total_cents: float = 0.0
    most_used_model: Optional[str] = None


class OrgRecord(BaseModel):
    identifier: str
    org: str
    record_date_iso: str
    totals: OrgTotals
    breakdown: Dict[str, Any] = Field(default_factory=dict)


class UserRecord(BaseModel):
    identifier: str
    org: str
    record_date_iso: str
    totals: UserTotals
    breakdown: Dict[str, Any] = Field(default_factory=dict)


class TeamTotals(BaseModel):
    team: str
    total_accepts: int = 0
    total_rejects: int = 0
    total_tabs_shown: int = 0
    total_tabs_accepted: int = 0
    total_lines_added: int = 0
    total_lines_deleted: int = 0
    accepted_lines_added: int = 0
    accepted_lines_deleted: int = 0
    composer_requests: int = 0
    chat_requests: int = 0
    agent_requests: int = 0
    subscription_included_reqs: int = 0
    api_key_reqs: int = 0
    usage_based_reqs: int = 0
    bugbot_usages: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    total_cents: float = 0.0
    most_used_model: str | None = None
    total_active_users: int = 0


class TeamRecord(BaseModel):
    identifier: str
    org: str
    team: str
    record_date_iso: str
    totals: TeamTotals
    breakdown: Dict[str, Any] = Field(default_factory=dict)

