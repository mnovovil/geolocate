---
description: Shape an idea into a structured GitHub Issue with a full implementation plan
---

# /ce:plan — From Idea to Ready Issue

You are a senior engineer planning work for this project.

## Prerequisites

Read `.claude/ce-config.md` for the repo (`<REPO>`), labels, issue types, and optional project-board IDs.

If the project board is configured, ProjectV2 mutations require the `project` scope on the GitHub token. Check once per session:

```bash
gh auth status | grep -q 'project' || echo "⚠️  Run: gh auth refresh -s project"
```

If the scope is missing, stop and ask the user to run `gh auth refresh -s project` before proceeding.

## Flow

### 1. Listen & Clarify
Listen to the user's idea. Ask **at most 2** clarifying questions if critical details are missing. Don't over-question — start investigating.

### 2. Load Context
Read these files:
- `CLAUDE.md` — architecture and conventions
- `.claude/skills/plan/SKILL.md` — planning methodology
- `.claude/learnings.md` — past learnings that may inform this plan

### 3. Search Related Issues
```bash
gh issue list --search "<keywords from idea>" --repo <REPO> --limit 10
```
Flag any duplicates or related issues to the user.

### 4. Investigate Codebase
Read the relevant files to understand current state. Trace the change end-to-end as described in the planning skill. Don't plan blind — understand what exists.

### 5. Write Structured Plan

Create the issue body with this structure:

```markdown
## Goal
One sentence describing the desired outcome.

## Context
Why this matters. Link related issues if any.

## Approach

### Steps
1. `[area]` Step description
2. `[area]` Step description
...

### Files to Change
- `path/to/file` — what changes and why

## Testing Strategy
- Unit: what to test
- Integration: what to test
- E2E / manual: what to verify

## Risks
- Risk description → mitigation approach
```

### 6. Create the Issue

```bash
gh issue create \
  --title "<PREFIX> Short imperative description" \
  --body "$(cat <<'EOF'
<plan body>
EOF
)" \
  --label "<label>" \
  --repo <REPO>
```

Use the title prefix and labels from `.claude/ce-config.md` (omit if `TBD`). Only apply labels that exist (`gh label list --repo <REPO>`).

If issue-type IDs are configured, set the Issue Type via GraphQL:

```bash
ISSUE_ID=$(gh api repos/<REPO>/issues/<number> --jq '.node_id')
gh api graphql -f query='mutation { updateIssue(input: { id: "'$ISSUE_ID'", issueTypeId: "<TYPE_ID>" }) { issue { number } } }'
```

### 7. Set Project Fields (if project board configured)

Add to the project and set fields using the IDs in `.claude/ce-config.md`:

```bash
gh api graphql -f query='mutation { addProjectV2ItemById(input: { projectId: "<PROJECT_ID>", contentId: "'$ISSUE_ID'" }) { item { id } } }'
```

**Always ask the user to confirm**:
- **Status**: Default suggestion is `Backlog`, but ask — might be `Todo` for immediate work
- **Priority**: Suggest based on scope/urgency (Very High / High / Normal / Low)
- **Milestone**: Suggest one if milestones are configured, or none

### 8. Sub-Issues (if needed)

If the plan has > 8 steps:
- Create sub-issues linked to the parent via the `addSubIssue` mutation
- Each sub-issue should be independently implementable
- Sub-issues get the same project fields as regular issues

```bash
gh api graphql -f query='mutation { addSubIssue(input: { issueId: "'$PARENT_ID'", subIssueId: "'$CHILD_ID'" }) { issue { number } subIssue { number } } }'
```

### 9. Plan Quality Gate

Run the checklist from `.claude/skills/plan/SKILL.md` and report the results to the user.
