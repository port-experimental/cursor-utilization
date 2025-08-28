## Cursor Utilization → Port 

Import Cursor Admin API metrics and AI Code Tracking data into Port as both daily aggregated records and individual commit records. Includes user metrics, AI code tracking with commit-level detail, and relationships to existing services and pull requests. Uses bulk upsert endpoints for Port. Timezone: UTC. 

### What this provides

#### Daily Usage Metrics
- Daily sync (and backfill) from Cursor Admin API
- Aggregation per day (UTC):
  - Event counts: accepts/rejects/tabs shown/tabs accepted, chat/composer/agent requests, usage split
  - Line counts: total/accepted lines added/deleted
  - Costs and tokens from usage events: total cents, input/output tokens
- Port entities (bulk upsert):
  - `cursor_usage_record` (org/day)
  - `cursor_user_usage_record` (user/day)
  - `cursor_team_usage_record` (team/day, optional mapping)

#### AI Code Tracking
- **Individual commit records** from Cursor AI Code Tracking API:
  - Full commit details: hash, user, repository, branch, timestamps, messages
  - Line changes broken down by AI assistance type (TAB, Composer, non-AI)
- **Daily commit aggregations** by user:
  - Daily rollup of commit statistics per user
  - Repository activity summaries and primary branch metrics
- **AI code changes** tracking editor-level changes
- Port entities (bulk upsert):
  - `cursor_commit_record` - individual commits with full metadata and relationships
  - `cursor_daily_commit_record` - daily aggregated commit statistics by user
  - `cursor_ai_code_change_record` - AI-generated code changes in the editor

#### Relationships
- **Individual commits** relate to:
  - Users (via email) 
  - Services (via repository name → existing service blueprint)
  - GitHub Pull Requests (via commit SHA → existing githubPullRequest blueprint)
- **All user records** relate to Users (via email)

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

3) Create the blueprints in Port (UI or API) using files under `blueprints/`:
   - Daily usage blueprints: `cursor_usage_record`, `cursor_user_usage_record`, `cursor_team_usage_record` 
   - AI code tracking blueprints: `cursor_commit_record`, `cursor_daily_commit_record`, `cursor_ai_code_change_record`
   - Note: Ensure your existing `service` and `githubPullRequest` blueprints are available for commit relationships

4) Run locally:

**Daily usage metrics:**
```
python -m src.main --mode daily --days 1
```

**Backfill usage metrics for last 30 days:**
```
python -m src.main --mode backfill --days 30
```

**AI commit tracking (daily aggregated by user):**
```
python -m src.main --mode ai-commits --days 7
```

**Individual commit tracking (each commit as separate record):**
```
python -m src.main --mode individual-commits --days 7
```

**AI code changes (individual editor changes):**
```
python -m src.main --mode ai-changes --days 7
```

### GitHub Actions (recommended)
Workflow: `.github/workflows/cursor-utilization.yml` runs nightly and on demand. Configure repository secrets for the env vars above.

### Notes

#### Daily Usage Aggregations
- The Cursor Admin API enforces a 90-day max range per request to daily usage; the workflow slices ranges automatically.
- Optional team aggregation: provide a JSON or YAML mapping via `--team-map path/to/map.json` containing `{ "user@org.com": "team-name" }`. When provided, team/day entities are exported as `cursor_team_usage_record`.
- Relations: pass `--with-relations` to include Port relations between entities (user relations for user records, team member relations for team records).
- Anonymization: pass `--anonymize-emails` to hash emails in outputs.

#### AI Code Tracking  
- **AI Commits** (`--mode ai-commits`): Creates daily aggregated commit records per user (`cursor_daily_commit_record`) with summary statistics and repository activity.
- **Individual Commits** (`--mode individual-commits`): Creates individual commit records (`cursor_commit_record`) with full metadata and relationships to services and pull requests.
- **AI Code Changes** (`--mode ai-changes`): Tracks individual editor-level changes (`cursor_ai_code_change_record`) made with AI assistance (TAB/Composer).
- **Additional Options**:
  - `--user <email>`: Filter data for specific user
  - `--with-relations`: Include Port entity relationships
  - `--anonymize-emails`: Hash email addresses for privacy

### References
- Cursor Admin API: [Admin API docs](https://docs.cursor.com/en/account/teams/admin-api)



