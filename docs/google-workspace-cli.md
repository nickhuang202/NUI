# Google Workspace CLI (gws)

## Overview
Unified CLI tool for ALL Google Workspace services (Drive, Gmail, Calendar, Sheets, Docs, Chat, Admin, etc.)
- **GitHub**: https://github.com/googleworkspace/cli
- **NPM**: `npm install -g @googleworkspace/cli`
- **Language**: Rust (fast, efficient)
- **Stars**: 17.7k+ ⭐

## Key Capabilities
- **Dynamic API discovery**: Uses Google Discovery Service - auto-updates when new APIs launch
- **100+ AI agent skills**: Pre-built workflows and recipes for common tasks
- **Structured JSON output**: Perfect for automation and AI agents
- **Multiple auth methods**: OAuth, service accounts, tokens, headless/CI mode
- **Advanced features**: Auto-pagination, dry-run, multipart uploads, Model Armor sanitization

## Installation
```bash
# Via npm (includes pre-built binaries)
npm install -g @googleworkspace/cli

# Via cargo
cargo install --git https://github.com/googleworkspace/cli --locked

# Via nix
nix run github:googleworkspace/cli
```

## Quick Start
```bash
# Setup Google Cloud project and auth (requires gcloud CLI)
gws auth setup

# Or manual login with existing OAuth credentials
gws auth login

# List Drive files
gws drive files list --params '{"pageSize": 10}'

# Create spreadsheet
gws sheets spreadsheets create --json '{"properties": {"title": "Q1 Budget"}}'

# Send Chat message
gws chat spaces messages create \
  --params '{"parent": "spaces/xyz"}' \
  --json '{"text": "Deploy complete."}'

# Dry run (preview request)
gws drive files list --dry-run
```

## Authentication Methods (Priority Order)
1. **Access token**: `GOOGLE_WORKSPACE_CLI_TOKEN` (highest priority)
2. **Credentials file**: `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` (OAuth or service account JSON)
3. **Encrypted credentials**: `gws auth login` (stored in OS keyring via AES-256-GCM)
4. **Plaintext credentials**: `~/.config/gws/credentials.json`

### Auth Workflows
```bash
# Interactive (desktop) - one-time setup
gws auth setup  # Requires gcloud CLI

# Manual login
gws auth login

# Service account (server-to-server)
export GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=/path/to/service-account.json

# Pre-obtained token
export GOOGLE_WORKSPACE_CLI_TOKEN=$(gcloud auth print-access-token)

# Export for headless/CI
gws auth export --unmasked > credentials.json
```

## Advanced Features

### Pagination
```bash
# Auto-paginate (NDJSON output - one page per line)
gws drive files list --params '{"pageSize": 100}' --page-all

# Limit pages and add delay
gws drive files list --page-limit 5 --page-delay 200
```

### File Uploads
```bash
# Multipart upload
gws drive files create --json '{"name": "report.pdf"}' --upload ./report.pdf
```

### Schema Introspection
```bash
# View any method's request/response schema
gws schema drive.files.list
gws schema sheets.spreadsheets.values.get
```

### Model Armor (Response Sanitization)
```bash
# Scan API responses for prompt injection
gws gmail users messages get --params '...' \
  --sanitize "projects/P/locations/L/templates/T"

# Environment variables
export GOOGLE_WORKSPACE_CLI_SANITIZE_TEMPLATE="projects/P/locations/L/templates/T"
export GOOGLE_WORKSPACE_CLI_SANITIZE_MODE="warn"  # or "block"
```

## AI Agent Integration

### Install Skills
```bash
# All skills at once
npx skills add https://github.com/googleworkspace/cli

# Specific service skills
npx skills add https://github.com/googleworkspace/cli/tree/main/skills/gws-drive
npx skills add https://github.com/googleworkspace/cli/tree/main/skills/gws-gmail
```

### Gemini CLI Extension
```bash
# Install extension (after gws auth setup)
gemini extensions install https://github.com/googleworkspace/cli
```

## Common Use Cases

### Gmail
```bash
# List messages
gws gmail users messages list --params '{"userId": "me", "maxResults": 10}'

# Get message
gws gmail users messages get --params '{"userId": "me", "id": "MSG_ID"}'

# Send message
gws gmail users messages send --json '{"raw": "BASE64_ENCODED_EMAIL"}'
```

### Google Sheets
```bash
# Read cells (note: wrap ranges with ! in single quotes)
gws sheets spreadsheets values get \
  --params '{"spreadsheetId": "ID", "range": "Sheet1!A1:C10"}'

# Append rows
gws sheets spreadsheets values append \
  --params '{"spreadsheetId": "ID", "range": "Sheet1!A1", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [["Name", "Score"], ["Alice", 95]]}'
```

### Google Drive
```bash
# Search files
gws drive files list --params '{"q": "name contains 'report'"}'

# Create folder
gws drive files create --json '{"name": "My Folder", "mimeType": "application/vnd.google-apps.folder"}'

# Share file
gws drive permissions create \
  --params '{"fileId": "FILE_ID"}' \
  --json '{"role": "reader", "type": "user", "emailAddress": "user@example.com"}'
```

## Environment Variables
```bash
GOOGLE_WORKSPACE_CLI_TOKEN                # Pre-obtained access token
GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE     # OAuth/service account JSON path
GOOGLE_WORKSPACE_CLI_CLIENT_ID            # OAuth client ID
GOOGLE_WORKSPACE_CLI_CLIENT_SECRET        # OAuth client secret
GOOGLE_WORKSPACE_CLI_CONFIG_DIR           # Config dir (default: ~/.config/gws)
GOOGLE_WORKSPACE_CLI_SANITIZE_TEMPLATE    # Model Armor template
GOOGLE_WORKSPACE_CLI_SANITIZE_MODE        # warn or block
GOOGLE_WORKSPACE_PROJECT_ID               # GCP project ID override
```

## Troubleshooting

### "Access blocked" / 403 during login
- OAuth app in testing mode & account not in test users
- Fix: Console → OAuth consent screen → Test users → Add users

### "Google hasn't verified this app"
- Expected in testing mode
- Click "Advanced" → "Go to <app> (unsafe)" to proceed

### Too many scopes error
- Unverified apps limited to ~25 scopes
- Fix: Select specific services: `gws auth login --scopes drive,gmail,calendar`

### `redirect_uri_mismatch`
- OAuth client not created as "Desktop app"
- Fix: Delete & recreate as Desktop app in Credentials page

### API not enabled (`accessNotConfigured`)
- Enable API via URL in error message or run `gws auth setup`

## Architecture Highlights
1. Single-phase parsing: Reads service from argv[1]
2. Fetches Discovery Document (cached 24h)
3. Builds dynamic clap::Command tree
4. Re-parses remaining args
5. Authenticates & executes HTTP request
6. Returns structured JSON output

## Why Use gws?
- **For humans**: No more curl + REST docs, built-in help, dry-run mode
- **For AI agents**: Structured JSON, 100+ pre-built skills, zero custom tooling
- **Auto-updates**: New Google APIs appear automatically via Discovery Service
- **Universal**: One CLI for entire Workspace suite

## Resources
- **Docs**: https://github.com/googleworkspace/cli/blob/main/README.md
- **Skills Index**: https://github.com/googleworkspace/cli/blob/main/docs/skills.md
- **Examples**: https://github.com/googleworkspace/cli/tree/main/examples
- **.env template**: https://github.com/googleworkspace/cli/blob/main/.env.example
