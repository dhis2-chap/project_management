# Testing the Minimal Implementation

This document explains how to test the minimal working version of the OKR-Jira analysis system.

## What's Implemented

The minimal version includes:

- ✅ Configuration management (config.yaml, .env)
- ✅ Database schema and operations (SQLite)
- ✅ OKR parser (reads and parses OKR markdown files)
- ✅ Jira client (fetches issues via acli)
- ✅ Claude matcher (AI-based semantic matching)
- ✅ Basic workflow orchestration
- ✅ Database storage of results

## What's NOT Implemented Yet

- ❌ Markdown report generation
- ❌ Slack notifications
- ❌ Metrics and trend analysis
- ❌ Weekly automation

## Prerequisites

1. **Python 3.8+**
2. **Atlassian CLI (acli)** - For fetching Jira issues
   ```bash
   brew install atlassian-cli
   acli auth login
   ```

3. **Anthropic API Key** - For Claude AI matching
   - Get from: https://console.anthropic.com/

## Setup

1. Run the setup script:
   ```bash
   ./scripts/setup.sh
   ```

2. Edit `config/.env` with your API keys:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-...
   SLACK_WEBHOOK_URL=https://hooks.slack.com/...  # Optional for now
   ```

3. Verify acli is authenticated:
   ```bash
   acli jira project list --limit 5
   ```

## Running the Test

Run the main script:

```bash
source venv/bin/activate
python -m src.main
```

## What to Expect

The script will:

1. ✅ Load configuration from `config/config.yaml`
2. ✅ Initialize SQLite database at `output/data/okr_analysis.db`
3. ✅ Parse OKR file from `input/OKR/may_2026.md`
4. ✅ Fetch Jira issues from CLIM project (last 7 days)
5. ✅ Match each issue to OKRs using Claude AI
6. ✅ Store results in database
7. ✅ Print summary statistics

**Note:** The Claude API calls will take time - roughly 3-5 seconds per issue. If you have 20 issues, expect 1-2 minutes total.

## Expected Output

```
OKR-Jira Analysis System
============================================================

1. Loading configuration...
  ✓ Project: CLIM
  ✓ Analysis period: Last 7 days

2. Initializing database...
  ✓ Database: output/data/okr_analysis.db

3. Loading OKRs...
  ✓ Period: may_2026
  ✓ Objectives: 4

4. Fetching Jira issues...
  ✓ Fetched 15 issues

5. Matching issues to OKRs with Claude AI...
  This may take a while (15 API calls)...
  Processing issue 1/15: CLIM-123
  ...

6. Storing results...

✓ Analysis Complete!

Summary:
  Total issues analyzed: 15
  Aligned with OKRs: 12 (80.0%)
  Unaligned: 3 (20.0%)

Results stored in: output/data/okr_analysis.db
```

## Inspecting Results

You can inspect the database directly:

```bash
sqlite3 output/data/okr_analysis.db

# View all tables
.tables

# View OKRs
SELECT * FROM okrs;

# View issues
SELECT * FROM issues;

# View mappings
SELECT * FROM issue_okr_mappings;

# View unaligned issues
SELECT * FROM unaligned_issues;

# Exit
.exit
```

## Troubleshooting

### "acli command not found"
Install Atlassian CLI: `brew install atlassian-cli`

### "ANTHROPIC_API_KEY environment variable is not set"
Edit `config/.env` and add your API key

### "No issues found in the analysis period"
Adjust `analysis_days` in `config/config.yaml` to look back further (e.g., 30 days)

### "No OKR files found"
Make sure `input/OKR/may_2026.md` exists

## Next Steps

Once the minimal version works:

1. Implement markdown report generator
2. Add Slack notifications
3. Add metrics and trend analysis
4. Create automation script
5. Add comprehensive error handling
6. Write unit tests

## Cost Estimation

- Claude API: ~$0.03-0.05 per issue analyzed
- For 20 issues: ~$0.60-1.00 per run
- Weekly (if run once): ~$2.40-4.00 per month
