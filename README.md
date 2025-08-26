## Cursor Utilization → Port 

Import Cursor Admin API metrics into Port as daily records (org + user) with event counts, line counts, and cost metrics. Uses bulk upsert endpoints for Port. Timezone: UTC.

### What this provides
- Daily sync (and backfill) from Cursor Admin API
- Aggregation per day (UTC):
  - Event counts: accepts/rejects/tabs shown/tabs accepted, chat/composer/agent requests, usage split
  - Line counts: total/accepted lines added/deleted
  - Costs and tokens from usage events: total cents, input/output tokens
- Port entities (bulk upsert):
  - `cursor_usage_record` (org/day)
  - `cursor_user_usage_record` (user/day)
  - `cursor_team_usage_record` (team/day, optional mapping)
  - Each includes a `breakdown` object for extra details

### Prerequisites
- Python 3.11+
- A Cursor Admin API key (org admin): `key_xxx...`
- Port client credentials (or an API token) and a Port app with blueprints

### Setup
1) Create and export environment variables (or copy `env.sample` to `.env` in your runner):

```
X_CURSOR_API_KEY=key_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PORT_CLIENT_ID=your_port_client_id
PORT_CLIENT_SECRET=your_port_client_secret
PORT_BASE_URL=https://api.getport.io
PORT_AUTH_URL=https://api.getport.io/v1/auth/access_token
ORG_IDENTIFIER=your-org
TIMEZONE=UTC
LOOKBACK_DAYS=1
DRY_RUN=false
```

2) Install dependencies:

```
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: . .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

3) Create the blueprints in Port (UI or API) using files under `blueprints/`.

4) Run locally:

```
python -m src.main --mode daily --days 1
```

Backfill last 30 days: 

```
python -m src.main --mode backfill --days 30
```

### GitHub Actions (recommended)
Workflow: `.github/workflows/cursor-utilization.yml` runs nightly and on demand. Configure repository secrets for the env vars above.

### Notes
- The Cursor Admin API enforces a 90-day max range per request to daily usage; the workflow slices ranges automatically.
- Optional team aggregation: provide a JSON or YAML mapping via `--team-map path/to/map.json` containing `{ "user@org.com": "team-name" }`. When provided, team/day entities are exported as `cursor_team_usage_record`.
- Relations: pass `--with-relations` to include Port relations between entities (user relations for user records, team member relations for team records).
- Anonymization: pass `--anonymize-emails` to hash emails in outputs.

### References
- Cursor Admin API: [Admin API docs](https://docs.cursor.com/en/account/teams/admin-api)



