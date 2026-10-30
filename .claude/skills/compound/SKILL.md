---
description: Rules for capturing and categorizing session learnings in this project
---

# Compound Learning Rules

## Quality Bar

Only capture what would **surprise you in 2 weeks**. If it's obvious from reading the code or docs, skip it.

Good learnings:
- A non-obvious interaction between systems
- A gotcha that cost debugging time
- A pattern that worked better than the obvious approach
- A constraint discovered only through implementation

Bad learnings (skip these):
- Facts stated in a library's own documentation
- Generic advice ("databases need indexes")
- Universal practice ("tests should pass before committing")

## Entry Format

```markdown
### [Category] Title — YYYY-MM-DD

2-4 sentence description of the learning. What was the context? What was non-obvious?
Why does it matter?

<!-- optional code snippet -->
```

## Categories

| Category | What belongs here |
|----------|------------------|
| **Architecture** | Module boundaries, data flow, package/dependency structure |
| **Testing** | Test patterns, mocking/fixtures, flaky-test causes |
| **API Design** | Interface contracts, schema/validation quirks |
| **Data** | Data sources, formats, schema, migrations, data quality gotchas |
| **Performance** | Query/algorithm optimization, caching, async patterns |
| **Deployment** | Infra, containers, CI/CD pipeline issues |
| **Dependencies** | Package conflicts, version pins, tooling issues |

Add new categories when a recurring theme doesn't fit — and list them here.

## Append-Only Rule

NEVER overwrite or delete existing entries in `learnings.md`. Always append to the end of the file. If a previous learning is wrong, add a new entry that corrects it with a reference.

## Cross-Project IP Isolation

- General engineering patterns (testing strategies, git workflows, debugging techniques) can exist in learnings across projects
- Business logic, data models, API schemas, client names, pricing, and product-specific architecture must NEVER cross between projects
- When in doubt, keep it project-specific

## When to Suggest CLAUDE.md Updates

If a learning represents a **fundamental project convention** (not a one-off discovery), suggest adding it to `CLAUDE.md` instead. Examples:
- A new naming convention
- A new cross-module rule that applies to all future work
- A testing requirement that should be enforced universally
