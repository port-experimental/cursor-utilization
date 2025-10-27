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

**Required Variables:**
```bash
X_CURSOR_API_KEY=key_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PORT_CLIENT_ID=your_port_client_id
PORT_CLIENT_SECRET=your_port_client_secret
ORG_IDENTIFIER=your-org-identifier
```

**Optional Variables (with defaults):**
```bash
PORT_BASE_URL=https://api.getport.io              # Port API base URL
PORT_AUTH_URL=https://api.getport.io/v1/auth/access_token  # Port auth endpoint
DRY_RUN=false                                     # Set to 'true' for testing without writes
USER_BLUEPRINT=_user                              # Blueprint identifier for user entities
SERVICE_BLUEPRINT=service                         # Blueprint identifier for service/repository entities
GITHUB_PULL_REQUEST_BLUEPRINT=githubPullRequest  # Blueprint identifier for GitHub PR entities
RATE_LIMIT_REQUESTS_PER_MINUTE=55                # Max requests/min to Cursor API (default 55, limit is 60)
RATE_LIMIT_DELAY_BETWEEN_PAGES=1.5               # Delay in seconds between pagination requests
```

**Deprecated/Unused Variables:**
```bash
# These are no longer used but may exist in old configs
TIMEZONE=UTC                                      # Timezone handling is now built-in
LOOKBACK_DAYS=1                                   # Use --days command line argument instead
```

2) Install dependencies:

```
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: . .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

3) Set up the blueprints in Port with configurable relation targets:

**Option A: Use the automated setup (recommended):**
```bash
python -m src.main --mode setup-blueprints
```

**Option B: Create manually using files under `blueprints/`:**
   - Daily usage blueprints: `cursor_usage_record`, `cursor_user_usage_record`, `cursor_team_usage_record` 
   - AI code tracking blueprints: `cursor_commit_record`, `cursor_daily_commit_record`, `cursor_ai_code_change_record`
   - Note: The blueprint files now use configurable relation targets that can be customized via environment variables

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

**AI code changes tracking (daily aggregated by user):**
```
python -m src.main --mode ai-changes --days 7
```

**Set up blueprints with configurable relation targets:**
```
python -m src.main --mode setup-blueprints
```

#### Mode Selection Guide

| Mode | Use Case | Output | Frequency |
|------|----------|--------|-----------|
| `daily` | Regular usage monitoring | Daily usage aggregations per user/org | Daily scheduled |
| `backfill` | Historical data import | Same as daily, for date ranges | One-time/manual |
| `ai-commits` | Daily commit analytics | User daily commit summaries | Daily scheduled |
| `individual-commits` | Detailed commit analysis | Each commit as separate record with relationships | Manual/periodic |
| `ai-changes` | Editor-level AI usage | Individual code changes from TAB/Composer | Manual/periodic |

### GitHub Actions (recommended)

The workflow `.github/workflows/cursor-utilization.yml` provides automated syncing with multiple scheduling options:

#### Scheduled Runs
- **02:15 UTC daily**: Usage metrics sync (`--mode daily`)
- **02:30 UTC daily**: AI commits sync (`--mode ai-commits`)

#### Manual Execution
Use GitHub's "Run workflow" button with these options:
- **Mode**: Choose from `daily`, `backfill`, `ai-commits`, `individual-commits`, `ai-changes`
- **Days**: Number of days to process (default: 1)
- **Date Range**: Optional start/end dates (YYYY-MM-DD)
- **User Filter**: Filter AI data for specific user (email)
- **Relations**: Include Port entity relationships 
- **Anonymize**: Hash emails for privacy

#### Required Repository Configuration

**Secrets** (sensitive data):
```bash
X_CURSOR_API_KEY          # Your Cursor Admin API key
PORT_CLIENT_ID            # Port application client ID
PORT_CLIENT_SECRET        # Port application client secret  
ORG_IDENTIFIER           # Your organization identifier
```

**Variables** (optional, public):
```bash
PORT_BASE_URL            # Default: https://api.getport.io
PORT_AUTH_URL            # Default: https://api.getport.io/v1/auth/access_token
```

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



