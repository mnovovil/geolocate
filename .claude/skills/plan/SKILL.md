---
description: Planning methodology for this project's issues — sizing, risk, end-to-end trace, and structured plan output
---

# Planning Methodology

## End-to-End Trace

Every plan must identify which layers are touched. Read `CLAUDE.md` and the codebase to establish the project's actual layers, then trace the change through them from entry point to storage, for example:

```
Entry point (UI / CLI / API route) → Business logic → Data access → Storage / External service
```

Also trace any contract that is shared across boundaries (schemas, generated types, config, file formats) from where it is defined to every consumer.

## Step Area Tags

Tag every plan step with its area. Use the area tags in `.claude/ce-config.md` ("Code Areas"). If a step doesn't fit any tag, propose a new one and add it to the config.

## Cross-Layer Completeness

Changes that cross a boundary must land together. Common groups:

1. **New interface** (endpoint, command, public function): definition + implementation + registration/wiring + tests + docs
2. **Schema/data change**: model + migration + every consumer of the schema + tests
3. **Shared contract change**: definition + all consumers updated (regenerate any derived artifacts)
4. **Config/env change**: code + `.env.example` + every deployed environment

If a plan touches one side of a boundary but not the other, flag it.

## Priority Guide

| Priority | When to use |
|----------|-------------|
| **Very High** | Production blocker, data loss risk, security vulnerability |
| **High** | Important feature for current milestone, significant bug |
| **Normal** | Standard feature work, moderate improvements |
| **Low** | Nice-to-have, polish, minor improvements |

## Milestone Alignment

If milestones are defined in `.claude/ce-config.md`, suggest one based on scope and ask the user if ambiguous. Otherwise skip.

## Risk Assessment

Flag these risks explicitly:

- **Data migration**: Schema or data format changes requiring a migration
- **Contract break**: Changes to existing interfaces that break consumers
- **Auth/permissions changes**: Authentication or access-scoping modifications
- **Derived-artifact drift**: Source changes without regenerating dependent artifacts (types, clients, fixtures)
- **External dependencies**: New third-party APIs, rate limits, quotas, licensing
- **Infra changes**: Anything requiring a manual apply or new secrets
- **Cross-package**: Changes that span multiple packages/modules

## Plan Quality Gate

Before declaring a plan ready, verify:

- [ ] Every step has an area tag
- [ ] Cross-layer groups are complete
- [ ] Derived artifacts regenerated where needed
- [ ] Testing strategy covers all changed layers
- [ ] Priority justified
- [ ] Milestone assigned (if applicable)
- [ ] Risks identified with mitigation approach
- [ ] If > 8 steps, sub-issues are proposed

## Issue Types

| Type | When to use |
|------|-------------|
| **Feature** | New functionality, enhancements |
| **Bug** | Unexpected behavior, defects |
| **Chore** | Maintenance, deps, config, CI/CD |
| **Improvement** | Refactoring, performance, DX improvements |

## Testing Matrix

Use the test commands and locations from `.claude/ce-config.md` and `CLAUDE.md`. For each changed layer, state which kind of test covers it (unit / integration / E2E) and where it lives.
