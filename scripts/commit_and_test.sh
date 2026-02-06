#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-/home/NUI}"
REMOTE_URL="https://github.com/nickhuang202/NUI"
BRANCH="main"
COMMIT_MSG="${2:-"chore: update"}"

if [[ ! -d "$REPO_DIR" ]]; then
  echo "Repo directory not found: $REPO_DIR" >&2
  exit 1
fi

cd "$REPO_DIR"

if [[ ! -d .git ]]; then
  echo "Not a git repository: $REPO_DIR" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  if [[ -f "$HOME/.local/bin/env" ]]; then
    # shellcheck disable=SC1090
    source "$HOME/.local/bin/env"
  fi
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found on PATH. Install uv and retry." >&2
  exit 1
fi

if ! git rev-parse --abbrev-ref HEAD >/dev/null 2>&1; then
  echo "Failed to determine current branch." >&2
  exit 1
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

# Stage and commit
if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "$COMMIT_MSG"
else
  echo "No changes to commit."
fi

# Run CI/CT tests after commit
uv run pytest -m "not hardware"

# Push after tests pass
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$current_branch" != "$BRANCH" ]]; then
  echo "Current branch is $current_branch; pushing to $BRANCH" >&2
fi

git push -u origin "$current_branch"
