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

from __future__ import annotations

import base64
from typing import List, Dict, Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class CursorAdapter:
    def __init__(self, api_key: str, base_url: str = "https://api.cursor.com") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        auth_header = base64.b64encode(f"{api_key}:".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def get_team_members(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/teams/members"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("teamMembers", [])

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def get_daily_usage(self, start_epoch_ms: int, end_epoch_ms: int) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/teams/daily-usage-data"
        payload = {"startDate": start_epoch_ms, "endDate": end_epoch_ms}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def get_filtered_usage_events(
        self,
        start_epoch_ms: Optional[int] = None,
        end_epoch_ms: Optional[int] = None,
        email: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/teams/filtered-usage-events"
        payload: Dict[str, Any] = {"page": page, "pageSize": page_size}
        if start_epoch_ms is not None:
            payload["startDate"] = start_epoch_ms
        if end_epoch_ms is not None:
            payload["endDate"] = end_epoch_ms
        if email is not None:
            payload["email"] = email
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            resp.raise_for_status()
            return resp.json()


