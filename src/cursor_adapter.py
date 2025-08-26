from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


CURSOR_API_BASE = "https://api.cursor.com"


class CursorAdapter:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.Client(base_url=CURSOR_API_BASE, timeout=60.0)

    def _auth(self) -> httpx.Auth:
        # Basic auth with API key as username and empty password
        return httpx.BasicAuth(self.api_key, "")

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    def get_team_members(self) -> List[Dict[str, Any]]:
        resp = self._client.get("/teams/members", auth=self._auth())
        resp.raise_for_status()
        data = resp.json()
        return data.get("teamMembers", [])

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    def get_daily_usage(self, start_epoch_ms: int, end_epoch_ms: int) -> List[Dict[str, Any]]:
        payload = {"startDate": start_epoch_ms, "endDate": end_epoch_ms}
        resp = self._client.post("/teams/daily-usage-data", auth=self._auth(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    def get_filtered_usage_events(
        self,
        start_epoch_ms: Optional[int] = None,
        end_epoch_ms: Optional[int] = None,
        email: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"page": page, "pageSize": page_size}
        if start_epoch_ms is not None:
            payload["startDate"] = start_epoch_ms
        if end_epoch_ms is not None:
            payload["endDate"] = end_epoch_ms
        if email is not None:
            payload["email"] = email
        resp = self._client.post("/teams/filtered-usage-events", auth=self._auth(), json=payload)
        resp.raise_for_status()
        return resp.json()

    # AI Code Tracking API Methods
    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    def get_ai_commit_metrics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Get AI commit metrics (paginated JSON)
        
        Args:
            start_date: ISO date string, "now", or relative like "7d" 
            end_date: ISO date string, "now", or relative like "0d"
            user: Email, encoded ID, or numeric ID to filter by user
            page: Page number (1-based)
            page_size: Results per page (max 1000)
        """
        params: Dict[str, Any] = {"page": page, "pageSize": page_size}
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        if user is not None:
            params["user"] = user
        
        # Rate limiting: 5 requests per minute per team, per endpoint
        resp = self._client.get("/analytics/ai-code/commits", auth=self._auth(), params=params)
        resp.raise_for_status()
        return resp.json()

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    def get_ai_commit_metrics_csv(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user: Optional[str] = None,
    ) -> str:
        """
        Get AI commit metrics as CSV (streaming)
        
        Returns raw CSV content as string
        """
        params: Dict[str, Any] = {}
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        if user is not None:
            params["user"] = user
        
        resp = self._client.get("/analytics/ai-code/commits.csv", auth=self._auth(), params=params)
        resp.raise_for_status()
        return resp.text

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    def get_ai_code_change_metrics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Get AI code change metrics (paginated JSON)
        
        Args:
            start_date: ISO date string, "now", or relative like "14d"
            end_date: ISO date string, "now", or relative like "0d"
            user: Email, encoded ID, or numeric ID to filter by user
            page: Page number (1-based)
            page_size: Results per page (max 1000)
        """
        params: Dict[str, Any] = {"page": page, "pageSize": page_size}
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        if user is not None:
            params["user"] = user
        
        resp = self._client.get("/analytics/ai-code/changes", auth=self._auth(), params=params)
        resp.raise_for_status()
        return resp.json()

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
    def get_ai_code_change_metrics_csv(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user: Optional[str] = None,
    ) -> str:
        """
        Get AI code change metrics as CSV (streaming)
        
        Returns raw CSV content as string
        """
        params: Dict[str, Any] = {}
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        if user is not None:
            params["user"] = user
        
        resp = self._client.get("/analytics/ai-code/changes.csv", auth=self._auth(), params=params)
        resp.raise_for_status()
        return resp.text

