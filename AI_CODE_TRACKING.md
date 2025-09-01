# Cursor AI Code Tracking Integration with Port

This document describes the integration of Cursor's AI Code Tracking API with Port, enabling you to track and analyze AI-generated code contributions across your development teams.

## Overview

The Cursor AI Code Tracking API provides comprehensive analytics that can be imported into Port in multiple ways:

1. **AI Commit Metrics** - Daily aggregated per-user metrics that attribute lines to TAB, COMPOSER, and non-AI sources
2. **Individual Commits** - Full individual commit records with relationships to services and pull requests  
3. **AI Code Change Metrics** - Granular accepted AI changes from the editor, independent of commits

## Prerequisites

⚠️ **Enterprise Teams Only**: The AI Code Tracking API is only available for Cursor enterprise teams.

### Required Configuration

Ensure your environment variables are set:

```bash
# Required
X_CURSOR_API_KEY=your_cursor_api_key             # Cursor Admin API key (org admin)
ORG_IDENTIFIER=your_org                          # Your organization identifier  
PORT_CLIENT_ID=your_port_client_id               # Port application client ID
PORT_CLIENT_SECRET=your_port_client_secret       # Port application client secret

# Optional (with defaults)
PORT_BASE_URL=https://api.getport.io             # Port API base URL
PORT_AUTH_URL=https://api.getport.io/v1/auth/access_token  # Port auth endpoint  
DRY_RUN=false                                    # Set to 'true' for testing
```

### GitHub Actions Integration

The workflow automatically runs AI commit tracking daily at 02:30 UTC. You can also trigger individual modes manually through GitHub's "Run workflow" interface with full control over:

- Mode selection (ai-commits, individual-commits, ai-changes)
- Date ranges and user filtering
- Privacy options (email anonymization)
- Relationship inclusion

## Port Blueprints

Three blueprints are available for AI code tracking data:

### 1. cursor_daily_commit_record

Tracks daily aggregated AI commit metrics per user:

- **Identifier**: `cursor-ai-commits:{org}:{user_email}:{date}`
- **Key Metrics**:
  - Total commits with AI contribution
  - Lines added/deleted breakdown (TAB, Composer, Non-AI)
  - Primary branch commit count
  - Repository activity metrics
  - AI assistance percentage (calculated)
- **Relations**: User entities

### 2. cursor_commit_record  

Tracks individual AI commit records with full metadata:

- **Identifier**: Based on commit hash
- **Key Metrics**:
  - Full commit details (hash, message, timestamp, branch)
  - Lines added/deleted breakdown (TAB, Composer, Non-AI)  
  - Repository and user information
  - AI assistance percentage (calculated)
- **Relations**: User entities, Service entities (repositories), GitHub Pull Request entities

### 3. cursor_ai_code_change_record

Tracks daily aggregated AI code change metrics per user:

- **Identifier**: `cursor-ai-changes:{org}:{user_email}:{date}`
- **Key Metrics**:
  - Total AI changes (TAB + Composer)
  - Lines added/deleted by source
  - Model usage statistics
  - File extension diversity
  - Productivity ratios (calculated)
- **Relations**: User entities, Daily commit records

## Usage Examples

### 1. Sync Daily Aggregated AI Commit Data (Last 7 Days)

```bash
python -m src.main --mode ai-commits --days 7
```

### 2. Sync Individual AI Commit Records (Last 7 Days)

```bash
python -m src.main --mode individual-commits --days 7
```

### 3. Sync AI Code Changes (Last 30 Days)

```bash
python -m src.main --mode ai-changes --days 30
```

### 4. Sync Specific Date Range

```bash
python -m src.main --mode ai-commits --start 2024-01-01 --end 2024-01-31
```

### 5. Individual Commits with Relationships

```bash
python -m src.main --mode individual-commits --days 7 --with-relations
```

### 6. Filter by Specific User

```bash
python -m src.main --mode ai-changes --user developer@company.com --days 14
```

### 7. Export with Relations and Email Anonymization

```bash
python -m src.main --mode ai-commits --days 7 --with-relations --anonymize-emails
```

### 8. Dry Run (Test Without Writing to Port)

```bash
DRY_RUN=true python -m src.main --mode individual-commits --days 1
```

## Command Line Options

| Option              | Description                                                      | AI Modes Support |
| ------------------- | ---------------------------------------------------------------- | ---------------- |
| `--mode`            | Sync mode: `daily`, `backfill`, `ai-commits`, `individual-commits`, `ai-changes` | Required         |
| `--days`            | Number of days to process (default: 1)                         | ✅               |
| `--start`           | Start date (YYYY-MM-DD) UTC                                     | ✅               |
| `--end`             | End date (YYYY-MM-DD) UTC                                       | ✅               |
| `--user`            | Filter by specific user (email, encoded ID, or numeric ID)     | ✅               |
| `--anonymize-emails` | Hash emails before export                                       | ✅               |
| `--with-relations`   | Include Port relations between entities                         | ✅               |

## API Rate Limiting

The AI Code Tracking API has rate limits:
- **5 requests per minute per team, per endpoint**

The integration handles this automatically by:
- Using larger page sizes (200 items) to minimize requests
- Built-in retry logic with exponential backoff
- Proper error handling and logging

## Data Structure and Insights

### AI Commit Record Breakdown

Each AI commit record includes detailed breakdown data:

```json
{
  "commits": [...],                    // Individual commit details
  "repositories": {                    // Repository activity counts
    "repo1": 5,
    "repo2": 3
  },
  "ai_contribution_breakdown": {       // AI assistance percentages
    "tab_percentage": 45.2,
    "composer_percentage": 30.1,
    "non_ai_percentage": 24.7
  }
}
```

### AI Code Change Record Breakdown

Each AI code change record includes:

```json
{
  "changes": [...],                    // Individual change details
  "source_distribution": {             // TAB vs Composer usage
    "TAB": 12,
    "COMPOSER": 8
  },
  "model_usage": {                     // AI model statistics
    "gpt-4o": 15,
    "claude-3": 5
  },
  "file_extensions": {                 // Programming languages
    "ts": 10,
    "py": 6,
    "js": 4
  },
  "productivity_metrics": {            // Efficiency calculations
    "average_lines_per_change": 8.5,
    "tab_vs_composer_ratio": 1.5,
    "tab_efficiency": 6.2,
    "composer_efficiency": 12.3
  }
}
```

## Port Dashboards and Analytics

Once data is synced to Port, you can create powerful dashboards to track:

### Team Productivity Metrics
- AI assistance adoption rates
- Code generation efficiency
- TAB vs Composer usage patterns
- Repository-specific AI contribution

### Individual Developer Insights
- Daily AI code generation volume
- Preferred AI tools (TAB vs Composer)
- Programming language AI adoption
- Commit frequency with AI assistance

### Organizational KPIs
- Overall AI adoption across teams
- Code quality impact measurement
- Developer productivity acceleration
- AI tool ROI analysis

## Advanced Configuration

### Custom Date Ranges

The AI API supports flexible date formats:

```bash
# Relative dates
--start 7d --end now

# ISO dates
--start 2024-01-01 --end 2024-01-31

# Mix relative and absolute
--start 2024-01-01 --end 7d
```

### Large Data Extraction

For historical data analysis over extended periods:

```bash
# Backfill last 90 days of AI commits
python -m src.main --mode ai-commits --days 90

# Specific quarter analysis
python -m src.main --mode ai-changes --start 2024-01-01 --end 2024-03-31
```

## Troubleshooting

### Common Issues

1. **API Access Error**: Ensure your organization has enterprise-level access
2. **Rate Limiting**: The tool automatically handles rate limits with retries
3. **Date Format Issues**: Use YYYY-MM-DD format or relative terms like "7d"
4. **Missing Data**: Some metrics may be null if privacy mode is enabled

### Logging

Enable detailed logging for debugging:

```bash
# Set log level to DEBUG
PYTHONPATH=. python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('src/main.py').read())
" --mode ai-commits --days 1
```

## Integration Roadmap

### Completed ✅
- [x] Pydantic models for AI Code Tracking API
- [x] Port blueprints for commit and change metrics
- [x] CursorAdapter API methods
- [x] Data aggregation logic
- [x] CLI modes for AI tracking
- [x] PortExporter integration
- [x] Comprehensive documentation

### Future Enhancements 🚀
- [ ] Rate limiting optimization
- [ ] CSV streaming for large datasets
- [ ] Team-level aggregations
- [ ] Real-time sync capabilities
- [ ] Custom webhook integrations
- [ ] Advanced analytics dashboards

## Support

For questions or issues:
1. Check the logs for detailed error messages
2. Verify your Cursor API key has enterprise access
3. Ensure Port configuration is correct
4. Review the [Cursor AI Code Tracking API documentation](https://docs.cursor.com/en/account/teams/ai-code-tracking-api)

## Examples Repository

Check the `examples/` directory (coming soon) for:
- Sample Port dashboard configurations
- Custom aggregation scripts  
- Integration with CI/CD pipelines
- Advanced analytics queries
