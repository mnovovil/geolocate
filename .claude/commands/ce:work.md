---
description: Create a branch, implement an issue plan step by step, and open a PR
---

# /ce:work — Branch + Code + PR

You are a senior engineer implementing a planned issue for this project.

## Prerequisites

Read `.claude/ce-config.md` for the repo (`<REPO>`), base branch (`<BASE>`), commands, commit style, and optional project-board IDs.

If the project board is configured, check the token has the `project` scope once per session:

```bash
gh auth status | grep -q 'project' || echo "⚠️  Run: gh auth refresh -s project"
```

If the scope is missing, stop and ask the user to run `gh auth refresh -s project` before proceeding.

## Flow

### 1. Read the Issue
Get the issue number from the user (or URL). Read it:
```bash
gh issue view <number> --repo <REPO>
```

### 2. Load Context
Read:
- `CLAUDE.md` — architecture and conventions
- `.claude/learnings.md` — past learnings relevant to this work

### 3. Create Branch

```bash
git checkout <BASE>
git pull origin <BASE>
git checkout -b feat/<issue>-<slug>
```

Branch naming: `feat/<issue>-<short-slug>`. Use `fix/` for bugs, `chore/` for chores.

**Important**: Branch from `<BASE>`, PR targets `<BASE>`.

### 4. Pre-flight Checklist

Run the install command from `.claude/ce-config.md`.

Verify the working tree is clean (no pre-existing uncommitted changes that would pollute the diff):
```bash
git status --short
```

If there are uncommitted changes, report them to the user and ask how to proceed before writing any code.

Start local services if the config defines a command for it. Report any pre-flight failures before proceeding.

### 5. Move Issue to "In Progress" (if project board configured)

Applies to **all issues, including sub-issues**. Skip if the project-board IDs are `TBD`.

```bash
OWNER=${REPO%/*}; NAME=${REPO#*/}
ITEM_ID=$(gh api graphql -f query='{
  repository(owner:"'$OWNER'",name:"'$NAME'") {
    issue(number:<number>) {
      projectItems(first:5) { nodes { id } }
    }
  }
}' --jq '.data.repository.issue.projectItems.nodes[0].id')

gh api graphql -f query='mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "<PROJECT_ID>",
    itemId: "'$ITEM_ID'",
    fieldId: "<STATUS_FIELD_ID>",
    value: { singleSelectOptionId: "<STATUS_IN_PROGRESS_ID>" }
  }) { projectV2Item { id } }
}'
```

### 6. Implement Step by Step

Follow the plan from the issue body. For each step:
1. **Implement** the change
2. **Lint**: run the lint command from the config
3. **Test**: run the relevant tests
4. **Commit**: use the commit style from the config (default: conventional commits, e.g. `feat: add X`)

### 7. Regenerate Derived Artifacts (if needed)

If the change affects anything generated from source (types, clients, fixtures, docs), run `/sync-generated` (configured in `.claude/ce-config.md`) and include the regenerated files in the PR. If the plan calls for a new endpoint/module/component and a matching recipe exists, use `/scaffold` to create it.

### 8. Push & Create PR

```bash
git push -u origin feat/<issue>-<slug>

gh pr create \
  --title "feat: short description" \
  --body "$(cat <<'EOF'
## Summary
- What changed and why

Closes #<issue>

## Test plan
- [ ] Tests pass
- [ ] Lint passes
- [ ] Type check passes
- [ ] Derived artifacts regenerated (if applicable)

## Manual testing
1. ...
EOF
)" \
  --base <BASE> \
  --repo <REPO>
```

### 9. Move Issue to "To Review" (if project board configured)

Same mutation as step 5 with `<STATUS_TO_REVIEW_ID>`. Applies to **all issues, including sub-issues**.

### 10. Report

Tell the user:
- PR URL
- Summary of what was implemented
- Any deviations from the plan
- Any follow-up work needed

**Manual testing checklist**: Based on what was implemented, provide a short numbered checklist of how to verify it by hand: what to run or open, what action to take, and what to observe as the success condition. Add this checklist to both the report and the PR description.

For backend/CLI-only changes, provide a concrete command (`curl`, CLI invocation, script run) that exercises the change.
