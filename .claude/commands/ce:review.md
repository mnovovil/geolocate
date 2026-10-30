---
description: Run a 4-pass structured code review with test coverage, architecture, security, and performance checks
---

# /ce:review — 4-Pass Structured Review

You are a senior engineer reviewing code changes in this project.

Read `.claude/ce-config.md` for the base branch (`<BASE>`) and lint/test commands.

## Pre-Review: Run Tests First

Before reviewing, run lint, type check, and tests on the changed areas:

```bash
# Check what changed
git diff --name-only <BASE>...HEAD
```

Then run the lint, type-check, and test commands from `.claude/ce-config.md` that cover the changed files.

Report test results before starting the review passes.

## Passes

Read `.claude/skills/review/SKILL.md` for the full checklist, plus `CLAUDE.md` and `.claude/learnings.md` for project conventions and known gotchas. Run all four passes:

1. **Test Coverage Gaps** — table of changed behavior vs. test status
2. **Architecture & Pattern Consistency** — layering, conventions, cross-layer completeness, contract sync
3. **Security** — rate each finding `critical` / `warning` / `info`
4. **Performance** — data access, external calls, compute, interface payloads

## Output

```markdown
## Review Summary

**Verdict**: [Ready to push | Needs fixes | Needs discussion]

**Tests**: [pass/fail summary]

### Test Coverage Gaps
| File | Function/Behavior | Test Status | Suggested Test |
|------|-------------------|-------------|----------------|

### Architecture Issues
- [findings]

### Security Findings
- [critical/warning/info] description

### Performance Concerns
- [findings]

### Action Items
1. **Must fix**: [items]
2. **Should fix**: [items]
3. **Nice to have**: [items]
```
