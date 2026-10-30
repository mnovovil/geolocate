---
description: Structured 4-pass review checklist — test coverage, architecture, security, performance
---

# Review Checklist

Before reviewing, read `CLAUDE.md` and `.claude/learnings.md` — project conventions and past gotchas take precedence over the generic checks below.

## Pass 1: Test Coverage Gaps

Output a table:

```
| File | Function/Behavior | Test Status | Suggested Test |
|------|-------------------|-------------|----------------|
```

Test Status values: covered, partial, missing

### What to check
- New public functions, endpoints, and commands have tests
- Edge cases covered: empty input, invalid input, boundaries, error paths
- External services (HTTP, DB, cloud APIs) are mocked/faked at a consistent boundary
- Input validation logic has tests for both accepted and rejected values
- Bug fixes include a regression test

## Pass 2: Architecture & Pattern Consistency

### General
- Lock files not modified manually
- No `.env` files, secrets, or large data files in the diff
- New code matches surrounding conventions (naming, structure, comment style, language)
- No dead code, debug prints, or commented-out blocks left behind

### Layering
- Each layer does its own job: entry points (routes/CLI/UI) delegate to business logic; business logic uses a data-access layer rather than raw queries/IO
- Schemas/types used for all external input and output
- New modules registered/wired where the project expects them

### Cross-Layer Completeness
If a new interface was added, verify every layer exists and is wired up, tests exist, and any derived artifacts (generated types, clients, docs) are regenerated or flagged.

### Contract Synchronization
- If a shared contract changed, are all consumers updated?
- Do downstream packages/modules still build and type-check?

## Pass 3: Security Review

Rate each finding: `critical` / `warning` / `info`

### Check for:
- **Auth bypass**: Endpoints/commands missing required authentication or authorization
- **Data leakage**: Queries not scoped to the caller's tenant/user; sensitive fields in responses or logs
- **Input validation**: All external input validated (including file uploads, paths, coordinates, URLs)
- **Secret exposure**: No hardcoded keys, tokens, or connection strings
- **Injection**: Parameterized queries; no shell/SQL built from user input
- **SSRF / path traversal**: User-controlled URLs or file paths constrained
- **Dependency vulnerabilities**: Known CVEs in added packages
- **PII handling**: Personal or location data stored, logged, and retained only as needed

## Pass 4: Performance

### Data access
- Queries use appropriate indexes
- No N+1 patterns (loops issuing one query per item)
- Large result sets paginated or streamed
- Async/sync usage consistent with the rest of the codebase

### External calls
- Calls to external APIs batched, cached, and rate-limit aware
- Timeouts and retries set

### Compute
- No accidental quadratic algorithms over large inputs
- Expensive results cached where reused
- Large files streamed rather than loaded fully into memory

### Interfaces
- Responses don't expose internal fields
- Bulk operations preferred over many individual requests

## Output Format

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
