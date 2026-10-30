---
description: Merge a reviewed PR, delete the branch, update issue to Done, and pull the base branch
---

# /ce:merge — Merge + Cleanup

You are a senior engineer closing out a completed PR.

Read `.claude/ce-config.md` for the repo (`<REPO>`), base branch (`<BASE>`), and optional project-board IDs.

## Flow

### 1. Identify the PR

Get the PR number from the user (or URL). Read it:
```bash
gh pr view <number> --repo <REPO>
```

Confirm:
- Base branch is `<BASE>`
- All CI checks are passing
- `/ce:review` verdict was "Ready to push" (or ask the user to confirm)

### 2. Check for Required Reviews

```bash
gh pr view <number> --repo <REPO> --json reviewDecision,reviews
```

If `reviewDecision` is not `APPROVED` and changes touch auth, data access, or infra, prompt the user: "This PR hasn't been approved — request a human review or proceed anyway?"

### 3. Merge

Use squash merge. This keeps the base branch history linear and the commit message clean.

```bash
gh pr merge <number> --squash --delete-branch --repo <REPO>
```

`--delete-branch` deletes the **remote** branch via the GitHub API.

### 4. Delete Local Branch

```bash
BRANCH=$(gh pr view <number> --repo <REPO> --json headRefName --jq '.headRefName')
git fetch origin --prune
git branch -d "$BRANCH" 2>/dev/null || echo "Local branch not found or already deleted"
```

If `git branch -d` fails because the branch is not fully merged locally (common after a squash merge), report it and ask the user to confirm `git branch -D "$BRANCH"` before running it.

### 5. Move Issue to "Done" (if project board configured)

Skip this step if the project-board IDs in `.claude/ce-config.md` are `TBD`. GitHub still closes the issue via `Closes #N`.

Get the linked issue number from the PR body:

```bash
gh pr view <number> --repo <REPO> --json body --jq '.body' | grep -oE 'Closes #[0-9]+' | grep -oE '[0-9]+'
```

For each linked issue:

```bash
OWNER=${REPO%/*}; NAME=${REPO#*/}
ITEM_ID=$(gh api graphql -f query='{
  repository(owner:"'$OWNER'",name:"'$NAME'") {
    issue(number:<issue_number>) {
      projectItems(first:5) { nodes { id } }
    }
  }
}' --jq '.data.repository.issue.projectItems.nodes[0].id')

gh api graphql -f query='mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "<PROJECT_ID>",
    itemId: "'$ITEM_ID'",
    fieldId: "<STATUS_FIELD_ID>",
    value: { singleSelectOptionId: "<STATUS_DONE_ID>" }
  }) { projectV2Item { id } }
}'
```

**Sub-issue cascade**: If the closed issue is a sub-issue, check whether all sibling sub-issues are also Done. If yes, move the parent issue to "Done" as well.

```bash
gh api repos/<REPO>/issues/<issue_number> --jq '.node_id' | \
  xargs -I{} gh api graphql -f query='{ node(id:"{}") { ... on Issue { parent { number state } } } }'
```

### 6. Pull Base Branch Locally

```bash
CURRENT=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT" = "<BASE>" ]; then
  git pull --ff-only origin <BASE>
else
  git fetch origin <BASE>:<BASE>
fi
```

### 7. Report

Tell the user:
- PR merged and branch deleted
- Issue(s) moved to Done
- Whether parent issue was also closed
- Current branch they're on
- One-liner: what was shipped (from the PR title)
