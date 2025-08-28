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


# AI Code Tracking API Models
class AiCommitMetric(BaseModel):
    # Derived from Cursor AI Code Tracking API /analytics/ai-code/commits
    commitHash: str
    userId: str
    userEmail: str
    repoName: Optional[str] = None
    branchName: Optional[str] = None
    isPrimaryBranch: Optional[bool] = None
    totalLinesAdded: int = 0
    totalLinesDeleted: int = 0
    tabLinesAdded: int = 0
    tabLinesDeleted: int = 0
    composerLinesAdded: int = 0
    composerLinesDeleted: int = 0
    nonAiLinesAdded: Optional[int] = None
    nonAiLinesDeleted: Optional[int] = None
    message: Optional[str] = None
    commitTs: Optional[str] = None
    createdAt: str


class AiCodeChangeFileMetadata(BaseModel):
    fileName: Optional[str] = None  # May be omitted in privacy mode
    fileExtension: Optional[str] = None
    linesAdded: int = 0
    linesDeleted: int = 0


class AiCodeChangeMetric(BaseModel):
    # Derived from Cursor AI Code Tracking API /analytics/ai-code/changes
    changeId: str
    userId: str
    userEmail: str
    source: str  # "TAB" or "COMPOSER"
    model: Optional[str] = None
    totalLinesAdded: int = 0
    totalLinesDeleted: int = 0
    createdAt: str
    metadata: List[AiCodeChangeFileMetadata] = Field(default_factory=list)


# Aggregated AI Code Tracking Models
class AiCommitTotals(BaseModel):
    total_commits: int = 0
    total_lines_added: int = 0
    total_lines_deleted: int = 0
    tab_lines_added: int = 0
    tab_lines_deleted: int = 0
    composer_lines_added: int = 0
    composer_lines_deleted: int = 0
    non_ai_lines_added: int = 0
    non_ai_lines_deleted: int = 0
    primary_branch_commits: int = 0
    total_unique_repos: int = 0
    most_active_repo: Optional[str] = None


class AiCodeChangeTotals(BaseModel):
    total_changes: int = 0
    total_lines_added: int = 0
    total_lines_deleted: int = 0
    tab_changes: int = 0
    composer_changes: int = 0
    tab_lines_added: int = 0
    tab_lines_deleted: int = 0
    composer_lines_added: int = 0
    composer_lines_deleted: int = 0
    most_used_model: Optional[str] = None
    unique_file_extensions: int = 0


class AiCommitRecord(BaseModel):
    identifier: str
    org: str
    user_email: str
    record_date_iso: str
    totals: AiCommitTotals
    breakdown: Dict[str, Any] = Field(default_factory=dict)


class AiCodeChangeRecord(BaseModel):
    identifier: str
    org: str
    user_email: str
    record_date_iso: str
    totals: AiCodeChangeTotals
    breakdown: Dict[str, Any] = Field(default_factory=dict)


# Individual Commit Record Models (replaces aggregated AiCommitRecord)
class IndividualCommitRecord(BaseModel):
    """Individual commit record with full details from the API"""
    identifier: str  # Based on commitHash
    commitHash: str
    userId: str
    userEmail: str
    repoName: str
    branchName: str
    isPrimaryBranch: bool
    totalLinesAdded: int = 0
    totalLinesDeleted: int = 0
    tabLinesAdded: int = 0
    tabLinesDeleted: int = 0
    composerLinesAdded: int = 0
    composerLinesDeleted: int = 0
    nonAiLinesAdded: int = 0
    nonAiLinesDeleted: int = 0
    message: str
    commitTs: str
    createdAt: str
    org: str  # Added for organization tracking




