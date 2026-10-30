#!/usr/bin/env bash
# PostToolUse (Edit|Write): auto-format the edited file with whatever formatter
# the project uses. Each formatter runs only if it is installed and, for JS/TS,
# only if the project has a config for it. Never fails the tool call.
file=$(jq -r '.tool_input.file_path // empty')
[ -z "$file" ] || [ ! -f "$file" ] && exit 0
root="$CLAUDE_PROJECT_DIR"

has_config() { compgen -G "$root/$1" >/dev/null; }

case "$file" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff format --quiet "$file" 2>/dev/null
      ruff check --fix --quiet "$file" 2>/dev/null
    fi ;;
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs)
    if has_config "eslint.config.*" || has_config ".eslintrc*"; then
      (cd "$root" && npx --no-install eslint --fix --quiet "$file") 2>/dev/null
    fi
    if has_config ".prettierrc*" || has_config "prettier.config.*"; then
      (cd "$root" && npx --no-install prettier --write --log-level silent "$file") 2>/dev/null
    fi ;;
  *.go)
    command -v gofmt >/dev/null 2>&1 && gofmt -w "$file" 2>/dev/null ;;
  *.rs)
    command -v rustfmt >/dev/null 2>&1 && rustfmt --quiet "$file" 2>/dev/null ;;
  *.tf)
    command -v terraform >/dev/null 2>&1 && terraform fmt "$file" >/dev/null 2>&1 ;;
esac
exit 0
