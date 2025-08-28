from __future__ import annotations

import logging
from typing import Any, Dict, List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import OrgRecord, UserRecord, TeamRecord, AiCommitRecord, AiCodeChangeRecord, IndividualCommitRecord


class PortExporter:
    def __init__(self, base_url: str, auth_url: str, client_id: str, client_secret: str, dry_run: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth_url = auth_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.dry_run = dry_run
        self._client = httpx.Client(timeout=60.0)
        self._token = None

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = self._client.post(
            self.auth_url,
            json={"clientId": self.client_id, "clientSecret": self.client_secret},
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("accessToken") or data.get("access_token")
        if not token:
            raise RuntimeError("Failed to obtain Port access token")
        self._token = token
        return token

    def _headers(self) -> Dict[str, str]:
        token = self._get_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _format_entity(self, identifier: str, properties: Dict[str, Any], relations: Dict[str, Any] = None) -> Dict[str, Any]:
        # Port API expects entity format without "entity" wrapper for bulk endpoints
        entity = {
            "identifier": identifier,
            "properties": properties,
        }
        if relations:
            entity["relations"] = relations
        return entity

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    def bulk_upsert_blueprint(self, blueprint: str, entities: List[Dict[str, Any]]) -> None:
        if self.dry_run:
            return
        # Use correct Port API endpoint: /v1/blueprints/{blueprint}/entities/bulk
        url = f"{self.base_url}/v1/blueprints/{blueprint}/entities/bulk?upsert=true&merge=true"
        resp = self._client.post(url, headers=self._headers(), json={"entities": entities})
        resp.raise_for_status()

    def _bulk_in_chunks_by_blueprint(self, blueprint: str, entities: List[Dict[str, Any]], chunk_size: int = 20) -> None:
        # Port allows max 20 entities per request
        for i in range(0, len(entities), chunk_size):
            chunk = entities[i : i + chunk_size]
            self.bulk_upsert_blueprint(blueprint, chunk)

    def export_org_users_teams(self, org_record: OrgRecord, user_records: List[UserRecord], team_records: List[TeamRecord], with_relations: bool = False) -> None:
        # Group entities by blueprint for separate API calls
        org_entities: List[Dict[str, Any]] = []
        user_entities: List[Dict[str, Any]] = []
        team_entities: List[Dict[str, Any]] = []

        # Org entities
        org_props = {
            "record_date": org_record.record_date_iso,
            "org": org_record.org,
            "total_accepts": org_record.totals.total_accepts,
            "total_rejects": org_record.totals.total_rejects,
            "total_tabs_shown": org_record.totals.total_tabs_shown,
            "total_tabs_accepted": org_record.totals.total_tabs_accepted,
            "total_lines_added": org_record.totals.total_lines_added,
            "total_lines_deleted": org_record.totals.total_lines_deleted,
            "accepted_lines_added": org_record.totals.accepted_lines_added,
            "accepted_lines_deleted": org_record.totals.accepted_lines_deleted,
            "composer_requests": org_record.totals.composer_requests,
            "chat_requests": org_record.totals.chat_requests,
            "agent_requests": org_record.totals.agent_requests,
            "subscription_included_reqs": org_record.totals.subscription_included_reqs,
            "api_key_reqs": org_record.totals.api_key_reqs,
            "usage_based_reqs": org_record.totals.usage_based_reqs,
            "bugbot_usages": org_record.totals.bugbot_usages,
            "most_used_model": org_record.totals.most_used_model,
            "total_active_users": org_record.totals.total_active_users,
            "total_input_tokens": org_record.totals.total_input_tokens,
            "total_output_tokens": org_record.totals.total_output_tokens,
            "total_cache_write_tokens": org_record.totals.total_cache_write_tokens,
            "total_cache_read_tokens": org_record.totals.total_cache_read_tokens,
            "total_cents": org_record.totals.total_cents,
            "breakdown": org_record.breakdown,
        }
        org_entities.append(self._format_entity(org_record.identifier, org_props))

        # User entities
        for ur in user_records:
            up = {
                "record_date": ur.record_date_iso,
                "org": ur.org,
                "email": ur.totals.email,
                "is_active": ur.totals.is_active,
                "total_accepts": ur.totals.total_accepts,
                "total_rejects": ur.totals.total_rejects,
                "total_tabs_shown": ur.totals.total_tabs_shown,
                "total_tabs_accepted": ur.totals.total_tabs_accepted,
                "total_lines_added": ur.totals.total_lines_added,
                "total_lines_deleted": ur.totals.total_lines_deleted,
                "accepted_lines_added": ur.totals.accepted_lines_added,
                "accepted_lines_deleted": ur.totals.accepted_lines_deleted,
                "composer_requests": ur.totals.composer_requests,
                "chat_requests": ur.totals.chat_requests,
                "agent_requests": ur.totals.agent_requests,
                "subscription_included_reqs": ur.totals.subscription_included_reqs,
                "api_key_reqs": ur.totals.api_key_reqs,
                "usage_based_reqs": ur.totals.usage_based_reqs,
                "bugbot_usages": ur.totals.bugbot_usages,
                "most_used_model": ur.totals.most_used_model,
                "input_tokens": ur.totals.input_tokens,
                "output_tokens": ur.totals.output_tokens,
                "cache_write_tokens": ur.totals.cache_write_tokens,
                "cache_read_tokens": ur.totals.cache_read_tokens,
                "total_cents": ur.totals.total_cents,
                "breakdown": ur.breakdown,
            }
            # Add user relation only if requested
            user_relations = None
            if with_relations:
                user_relations = {
                    "user": ur.totals.email
                }
            user_entities.append(self._format_entity(ur.identifier, up, user_relations))
        
        # Team entities
        for tr in team_records:
            tp = {
                "record_date": tr.record_date_iso,
                "org": tr.org,
                "team": tr.team,
                "total_accepts": tr.totals.total_accepts,
                "total_rejects": tr.totals.total_rejects,
                "total_tabs_shown": tr.totals.total_tabs_shown,
                "total_tabs_accepted": tr.totals.total_tabs_accepted,
                "total_lines_added": tr.totals.total_lines_added,
                "total_lines_deleted": tr.totals.total_lines_deleted,
                "accepted_lines_added": tr.totals.accepted_lines_added,
                "accepted_lines_deleted": tr.totals.accepted_lines_deleted,
                "composer_requests": tr.totals.composer_requests,
                "chat_requests": tr.totals.chat_requests,
                "agent_requests": tr.totals.agent_requests,
                "subscription_included_reqs": tr.totals.subscription_included_reqs,
                "api_key_reqs": tr.totals.api_key_reqs,
                "usage_based_reqs": tr.totals.usage_based_reqs,
                "bugbot_usages": tr.totals.bugbot_usages,
                "most_used_model": tr.totals.most_used_model,
                "total_active_users": tr.totals.total_active_users,
                "input_tokens": tr.totals.input_tokens,
                "output_tokens": tr.totals.output_tokens,
                "cache_write_tokens": tr.totals.cache_write_tokens,
                "cache_read_tokens": tr.totals.cache_read_tokens,
                "total_cents": tr.totals.total_cents,
                "breakdown": tr.breakdown,
            }
            # Add team member relations only if requested
            team_relations = None
            if with_relations and "team_member_identifiers" in tr.breakdown:
                team_relations = {
                    "team_members": tr.breakdown["team_member_identifiers"]
                }
            team_entities.append(self._format_entity(tr.identifier, tp, team_relations))

        # Send separate requests per blueprint
        if org_entities:
            self._bulk_in_chunks_by_blueprint("cursor_usage_record", org_entities)
        if user_entities:
            self._bulk_in_chunks_by_blueprint("cursor_user_usage_record", user_entities)
        if team_entities:
            self._bulk_in_chunks_by_blueprint("cursor_team_usage_record", team_entities)

    def export_ai_commit_records(self, commit_records: List[AiCommitRecord], with_relations: bool = False) -> None:
        """Export AI commit records to Port"""
        commit_entities: List[Dict[str, Any]] = []

        for cr in commit_records:
            props = {
                "record_date": cr.record_date_iso,
                "org": cr.org,
                "user_email": cr.user_email,
                "total_commits": cr.totals.total_commits,
                "total_lines_added": cr.totals.total_lines_added,
                "total_lines_deleted": cr.totals.total_lines_deleted,
                "tab_lines_added": cr.totals.tab_lines_added,
                "tab_lines_deleted": cr.totals.tab_lines_deleted,
                "composer_lines_added": cr.totals.composer_lines_added,
                "composer_lines_deleted": cr.totals.composer_lines_deleted,
                "non_ai_lines_added": cr.totals.non_ai_lines_added,
                "non_ai_lines_deleted": cr.totals.non_ai_lines_deleted,
                "primary_branch_commits": cr.totals.primary_branch_commits,
                "total_unique_repos": cr.totals.total_unique_repos,
                "most_active_repo": cr.totals.most_active_repo,
                "breakdown": cr.breakdown,
            }

            # Add user relation if requested
            commit_relations = None
            if with_relations:
                commit_relations = {
                    "user": cr.user_email
                }
            
            commit_entities.append(self._format_entity(cr.identifier, props, commit_relations))

        if commit_entities:
            self._bulk_in_chunks_by_blueprint("cursor_daily_commit_record", commit_entities)

    def export_ai_code_change_records(self, change_records: List[AiCodeChangeRecord], with_relations: bool = False) -> None:
        """Export AI code change records to Port"""
        change_entities: List[Dict[str, Any]] = []

        for ccr in change_records:
            props = {
                "record_date": ccr.record_date_iso,
                "org": ccr.org,
                "user_email": ccr.user_email,
                "total_changes": ccr.totals.total_changes,
                "total_lines_added": ccr.totals.total_lines_added,
                "total_lines_deleted": ccr.totals.total_lines_deleted,
                "tab_changes": ccr.totals.tab_changes,
                "composer_changes": ccr.totals.composer_changes,
                "tab_lines_added": ccr.totals.tab_lines_added,
                "tab_lines_deleted": ccr.totals.tab_lines_deleted,
                "composer_lines_added": ccr.totals.composer_lines_added,
                "composer_lines_deleted": ccr.totals.composer_lines_deleted,
                "most_used_model": ccr.totals.most_used_model,
                "unique_file_extensions": ccr.totals.unique_file_extensions,
                "breakdown": ccr.breakdown,
            }

            # Add user relation and AI commits relation if requested
            change_relations = None
            if with_relations:
                change_relations = {
                    "user": ccr.user_email
                    # Note: ai_commits relation would need to be implemented based on date matching
                }
            
            change_entities.append(self._format_entity(ccr.identifier, props, change_relations))

        if change_entities:
            self._bulk_in_chunks_by_blueprint("cursor_ai_code_change_record", change_entities)

    def export_individual_commit_records(self, commit_records: List[IndividualCommitRecord], with_relations: bool = False) -> None:
        """Export individual commit records to Port"""
        commit_entities: List[Dict[str, Any]] = []

        for cr in commit_records:
            props = {
                "commitHash": cr.commitHash,
                "userId": cr.userId,
                "userEmail": cr.userEmail,
                "repoName": cr.repoName,
                "branchName": cr.branchName,
                "isPrimaryBranch": cr.isPrimaryBranch,
                "totalLinesAdded": cr.totalLinesAdded,
                "totalLinesDeleted": cr.totalLinesDeleted,
                "tabLinesAdded": cr.tabLinesAdded,
                "tabLinesDeleted": cr.tabLinesDeleted,
                "composerLinesAdded": cr.composerLinesAdded,
                "composerLinesDeleted": cr.composerLinesDeleted,
                "nonAiLinesAdded": cr.nonAiLinesAdded,
                "nonAiLinesDeleted": cr.nonAiLinesDeleted,
                "message": cr.message,
                "commitTs": cr.commitTs,
                "createdAt": cr.createdAt,
                "org": cr.org,
            }

            # Add relations if requested
            commit_relations = None
            if with_relations:
                commit_relations = {
                    "user": cr.userEmail,
                    "repository": cr.repoName  # Maps to service blueprint
                }
                # githubPullRequest relation would need PR lookup logic based on commit SHA
                # This could be enhanced with actual PR lookup logic
            
            commit_entities.append(self._format_entity(cr.identifier, props, commit_relations))

        if commit_entities:
            self._bulk_in_chunks_by_blueprint("cursor_commit_record", commit_entities)


