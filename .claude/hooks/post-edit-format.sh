#!/usr/bin/env bash
# PostToolUse: format changed Python files with ruff and TS/TSX with prettier. Never fails the edit.
input=$(cat)
file=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
[ -z "$file" ] || [ ! -f "$file" ] && exit 0

case "$file" in
  *.py)
    if command -v uv >/dev/null 2>&1 && [ -f "${CLAUDE_PROJECT_DIR:-.}/backend/pyproject.toml" ]; then
      (cd "${CLAUDE_PROJECT_DIR:-.}/backend" && uv run ruff check --fix --quiet "$file" && uv run ruff format --quiet "$file") >&2 || true
    elif command -v ruff >/dev/null 2>&1; then
      ruff check --fix --quiet "$file" >&2 || true
      ruff format --quiet "$file" >&2 || true
    fi
    ;;
  *.ts|*.tsx)
    if [ -x "${CLAUDE_PROJECT_DIR:-.}/frontend/node_modules/.bin/prettier" ]; then
      "${CLAUDE_PROJECT_DIR:-.}/frontend/node_modules/.bin/prettier" --write --log-level warn "$file" >&2 || true
    elif command -v prettier >/dev/null 2>&1; then
      prettier --write --log-level warn "$file" >&2 || true
    fi
    ;;
esac
exit 0
