from __future__ import annotations

import logging
from typing import Any, Dict, List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import OrgRecord, UserRecord, TeamRecord


class PortExporter:
    def __init__(self, base_url: str, auth_url: str, bulk_upsert_url: str, client_id: str, client_secret: str, dry_run: bool = False) -> None:
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

    def export_org_users_teams(self, org_record: OrgRecord, user_records: List[UserRecord], team_records: List[TeamRecord]) -> None:
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
            # Add user relation separately
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
            team_entities.append(self._format_entity(tr.identifier, tp))

        # Send separate requests per blueprint
        if org_entities:
            self._bulk_in_chunks_by_blueprint("cursor_usage_record", org_entities)
        if user_entities:
            self._bulk_in_chunks_by_blueprint("cursor_user_usage_record", user_entities)
        if team_entities:
            self._bulk_in_chunks_by_blueprint("cursor_team_usage_record", team_entities)
