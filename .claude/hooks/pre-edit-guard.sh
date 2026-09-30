#!/usr/bin/env bash
# PreToolUse guard: block writes to .env files and to already-applied Alembic migrations.
# Exit 2 = block (stderr is shown to Claude).
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
[ -z "$file" ] && exit 0

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
base=$(basename "$file")

case "$base" in
  .env|.env.*)
    if [ "$base" != ".env.example" ]; then
      echo "Blocked: writing $base is not allowed (secrets live only in .env, edited by the user)." >&2
      exit 2
    fi
    ;;
esac

case "$file" in
  */secrets/*)
    echo "Blocked: files under secrets/ must not be edited." >&2
    exit 2
    ;;
esac

applied="$root/backend/app/db/migrations/APPLIED"
case "$file" in
  */db/migrations/versions/*.py)
    if [ -f "$applied" ] && grep -Fxq "$base" "$applied" 2>/dev/null; then
      echo "Blocked: migration $base is already applied (listed in migrations/APPLIED). Write a new migration (expand -> migrate -> contract)." >&2
      exit 2
    fi
    ;;
esac
exit 0
