---
description: Pull the base and release branches, then summarize what changed and by whom
---

# /ce:update — Stay Up to Date

You are a senior engineer helping the user stay on top of this project. Your job is to safely update the local base and release branches, then explain what changed since the last pull and who did it. Do not include information about uncommitted changes.

Read `.claude/ce-config.md` for the base branch (`<BASE>`) and release branch (`<RELEASE>`). If the release branch is `TBD` or equal to the base branch, only update `<BASE>`.

## Flow

### 1. Snapshot Current State

Record the starting point so we can diff old → new after the pull.

```bash
git rev-parse --abbrev-ref HEAD                 # remember current branch
git rev-parse <BASE> 2>/dev/null || echo "-"    # OLD_BASE
git rev-parse <RELEASE> 2>/dev/null || echo "-" # OLD_RELEASE
```

### 2. Fetch and Fast-Forward

Proceed regardless of working-tree state. `git pull --ff-only` and the cross-branch `fetch origin <branch>:<branch>` refspec do not touch other branches' working trees, so uncommitted changes do not block this command. Do **not** mention the working tree in the output.

Never switch branches:

```bash
git fetch origin
CURRENT=$(git rev-parse --abbrev-ref HEAD)

if [ "$CURRENT" = "<BASE>" ]; then
  git pull --ff-only origin <BASE>
  git fetch origin <RELEASE>:<RELEASE>
elif [ "$CURRENT" = "<RELEASE>" ]; then
  git pull --ff-only origin <RELEASE>
  git fetch origin <BASE>:<BASE>
else
  git fetch origin <BASE>:<BASE> <RELEASE>:<RELEASE>
fi
```

If any fast-forward fails (non-FF), report it and stop — the local branch has diverged and needs manual attention.

### 3. Compute the "What's New" Window

For each branch, if `OLD == NEW` say "no new commits" and skip its summary. Otherwise gather commits in `$OLD..$NEW`:

```bash
git log --no-merges $OLD..$NEW --pretty=format:'%h%x09%an%x09%ad%x09%s' --date=short
git log $OLD..$NEW --pretty=format:'%h %s' | grep -E 'Merge pull request #|\(#[0-9]+\)' || true

# File paths touched (for area grouping)
git log $OLD..$NEW --name-only --pretty=format: | sort -u | grep -v '^$'

# Co-Authored-By trailers (real contributor when squash-merged)
git log $OLD..$NEW --pretty=format:'%(trailers:key=Co-Authored-By,valueonly=true)' | grep -v '^$' | sort -u
```

### 4. Categorize Changes

Group touched files by area using the path prefixes in `.claude/ce-config.md` ("Code Areas"). Anything that matches no prefix goes under **root**.

### 5. Flag Noteworthy Items

Check the touched files against "Flagged Paths" in `.claude/ce-config.md` and against recurring gotchas in `.claude/learnings.md`. Also flag renames or large deletions (count and top paths).

If nothing applies, say so explicitly — silence is ambiguous.

### 6. Report

One block per branch with new commits, then a flags section. Keep it scannable.

```markdown
## /ce:update — Summary

**Branches updated:** <BASE> (`<OLD>..<NEW>`), <RELEASE> (`<OLD>..<NEW>`)
**Currently on:** `<branch>`

### <BASE> — N commits from M contributors

**Contributors:** Alice (3), Bob (2), …  *(includes Co-Authored-By)*

**By area:**
- **src** (4 commits)
  - `abc1234` Alice — feat: add X (#41)
- **infra** (1 commit)
  - …

### <RELEASE> — N commits from M contributors

*(same structure, or "no new commits since last pull")*

### Flags
- ⚠️ Infra changed: `infra/...` — manual apply may be needed
- ℹ️ `.env.example` updated — check for new keys
- (or: "No flagged items")
```

End with a single short sentence on the most important takeaway, e.g. "Heads-up: infra changed — apply before next deploy" or "All caught up, nothing risky."
