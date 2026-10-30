# Compound Engineering (CE) Workflow

Compound engineering is a plan-build-review-learn loop. Each session builds on previous learnings so the project gets smarter over time.

## Setup

Fill in `.claude/ce-config.md` (repo, base branch, lint/test commands, optional project-board IDs). Every command reads it; sections left as `TBD` are skipped or fall back to sensible defaults.

## Commands

| Command | What it does | When to use |
|---------|-------------|-------------|
| `/ce:update` | Pulls the base and release branches, summarizes what changed and by whom | Start of any session — before creating a branch |
| `/ce:plan` | Shapes an idea into a structured GitHub Issue with implementation steps | Starting new work — before writing code |
| `/ce:work` | Creates a branch, implements the issue plan, opens a PR | After a plan exists and you're ready to build |
| `/ce:review` | Runs a 4-pass review (tests, architecture, security, performance) | After the PR is open, before merging |
| `/ce:merge` | Merges a reviewed PR, deletes the branch, moves issue to Done, pulls base | After `/ce:review` returns "Ready to push" |
| `/ce:compound` | Extracts non-obvious learnings from the session | End of any session where something was learned |
| `/ce:do` | End-to-end wrapper: work + review + merge + compound in one shot | For well-understood issues you want shipped without babysitting |

## Recommended Workflow

1. **`/ce:update`** — Pull the latest base/release branches. Flags migrations, infra changes, and new env vars.
2. **`/ce:plan`** — Describe your idea. Claude investigates the codebase, searches for related issues, and creates a structured GitHub Issue.
3. **`/ce:work #123`** — Claude creates a branch from the base branch, implements step by step, and opens a PR.
4. **`/ce:review`** — Claude runs tests, then reviews the PR across 4 passes. Fix any "must fix" items.
5. **`/ce:merge #PR`** — Squash-merges, deletes remote and local branch, moves linked issue(s) to Done, pulls base.
6. **`/ce:compound`** — Claude scans the session for surprises and appends them to `learnings.md`.

Or skip steps 3–6 with **`/ce:do #123`** — pauses only if the review flags "Needs discussion" or CI fails.

## Skills

- `skills/plan/` — planning methodology (layer trace, area tags, risk, quality gate)
- `skills/review/` — 4-pass review checklist
- `skills/compound/` — rules for capturing learnings
- **`/scaffold <recipe> <name>`** (`skills/scaffold/`) — creates every layer of a new unit by mirroring a reference implementation from the Scaffold Recipes table in `ce-config.md`
- **`/sync-generated [artifact]`** (`skills/sync-generated/`) — regenerates derived artifacts (API types, clients, stubs) from their source and checks consumers still build. `/ce:work` uses it when a contract source changes
- **`generated-sync-checker`** agent (`agents/generated-sync-checker.md`) — runs the same check on its own, outside the CE loop

## Hooks

`settings.json` registers two hooks on Edit/Write:

- `hooks/guard-files.sh` — blocks edits to `.env*` files (except `.env.example`), lockfiles, and any glob listed in `protected-paths`
- `hooks/format.sh` — formats the edited file with whichever formatter is installed/configured (ruff, eslint, prettier, gofmt, rustfmt, terraform fmt)

The skills are stack-agnostic. As the project's architecture settles, add project-specific checks to them (layer rules, auth patterns, testing conventions).

## Learnings

`.claude/learnings.md` is the project's growing knowledge base. `/ce:compound` appends entries after each session. The quality bar: "Would this surprise me in 2 weeks?" If not, it doesn't belong.
