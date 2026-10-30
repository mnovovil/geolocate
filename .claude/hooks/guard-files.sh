#!/usr/bin/env bash
# PreToolUse (Edit|Write): block edits to files that must not be hand-edited.
# Exit 2 blocks the tool call and feeds stderr back to Claude.
file=$(jq -r '.tool_input.file_path // empty')
[ -z "$file" ] && exit 0

case "$file" in
  *.env.example) ;;
  *.env|*.env.*)
    echo "BLOCK: do not edit .env files directly — update .env.example instead" >&2; exit 2 ;;
  */pnpm-lock.yaml|*/package-lock.json|*/yarn.lock|*/uv.lock|*/poetry.lock|*/Cargo.lock|*/go.sum)
    echo "BLOCK: do not edit lockfiles by hand — run the package manager instead" >&2; exit 2 ;;
esac

# Project-specific protected paths: one glob per line in .claude/protected-paths
# (e.g. vendored code, generated files). Lines starting with # are ignored.
list="$CLAUDE_PROJECT_DIR/.claude/protected-paths"
if [ -f "$list" ]; then
  rel=${file#"$CLAUDE_PROJECT_DIR"/}
  while IFS= read -r pattern; do
    [[ -z "$pattern" || "$pattern" == \#* ]] && continue
    # shellcheck disable=SC2053
    if [[ "$rel" == $pattern ]]; then
      echo "BLOCK: $rel matches protected path '$pattern' (.claude/protected-paths) — regenerate it or change it at its source" >&2
      exit 2
    fi
  done < "$list"
fi
exit 0
