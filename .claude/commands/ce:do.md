---
description: End-to-end wrapper — implement an issue, review it, merge it, and capture learnings
---

# /ce:do — End-to-End Ship

You are a senior engineer shipping a planned issue end-to-end without manual handoffs.

This command runs `/ce:work` → `/ce:review` → `/ce:merge` → `/ce:compound` in sequence, pausing only when human judgement is required.

Read `.claude/ce-config.md` for the repo (`<REPO>`) and base branch (`<BASE>`).

## When to use

- Issue is well-understood with a clear plan
- Low architectural risk (no auth changes, no data migrations, no cross-package rewrites)
- You want it shipped without babysitting each step

For high-risk or uncertain issues, use the individual commands and review each step manually.

## Flow

### 1. Read the Issue

```bash
gh issue view <number> --repo <REPO>
```

Before proceeding, assess risk. **Pause and confirm with the user if**:
- The issue touches authentication, authorization, or data scoping
- The issue requires a data/schema migration
- The issue touches infrastructure or secrets
- The issue spans 3+ layers or multiple packages
- The issue has more than 8 implementation steps

If no red flags, proceed.

### 2. Run /ce:work

Follow all steps from `/ce:work`: create branch, install deps, check clean baseline, implement step by step, push, open PR.

At the end of `/ce:work`, report the PR URL and manual testing checklist to the user.

### 3. Check CI

If the repo has CI, wait for it to start, then check status:

```bash
gh pr checks <pr_number> --repo <REPO> --watch
```

If any check fails: **pause, report the failure to the user, and ask how to proceed**. Do not attempt auto-fixes without confirmation.

### 4. Run /ce:review

Follow all 4 passes from `/ce:review`. After completing the review:

- **"Ready to push"**: continue to step 5
- **"Needs fixes"**: apply all "Must fix" items, commit, push, re-run CI check, then re-review once. If still not "Ready to push" after one retry, **pause and report to the user**.
- **"Needs discussion"**: **always pause** — show the full review output and ask the user how to proceed before doing anything.

### 5. Show verdict and confirm

Before merging, show the user:
- Review verdict
- What was fixed (if anything)
- Manual testing checklist (from step 2)

Then ask: **"Ready to merge?"** Wait for explicit confirmation.

### 6. Run /ce:merge

Follow all steps from `/ce:merge`: squash merge, delete remote branch, delete local branch, move issue(s) to Done, pull base.

### 7. Run /ce:compound

Follow `/ce:compound`: scan the session for non-obvious learnings and append them to `.claude/learnings.md`.

### 8. Report

Final summary:
- What was shipped (PR title + issue)
- What was learned (from compound, if anything)
- Current branch the user is on
- Any follow-up issues to consider
