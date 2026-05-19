#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "Refusing to continue: .env is tracked by git."
  exit 1
fi

if ! git check-ignore .env >/dev/null 2>&1; then
  echo "Refusing to continue: .env is not ignored by git."
  exit 1
fi

if git ls-files | grep -E '(^|/)data/|\.log$' >/dev/null; then
  echo "Refusing to continue: runtime data or log files are tracked."
  exit 1
fi

if git grep -nE '([0-9]{7,}:[A-Za-z0-9_-]{25,}|TELEGRAM_BOT_TOKEN=[^[:space:]]{10,})' -- . ':(exclude).env.example' ':(exclude)scripts/pre_push_check.sh'; then
  echo "Potential secret found in tracked files."
  exit 1
fi

echo "Pre-push safety check passed."

