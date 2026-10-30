---
name: sync-generated
description: Regenerate derived artifacts (API types/clients, schemas, docs, fixtures) from their source and verify downstream consumers still build
user-invocable: true
disable-model-invocation: true
arguments:
  - name: artifact
    description: "Artifact name from the Generated Artifacts table in .claude/ce-config.md (omit to sync all)"
    required: false
---

# Sync Generated Artifacts

Keep generated files in sync with the source they are derived from (e.g. OpenAPI spec → TypeScript types, protobuf → stubs, DB schema → models).

## Steps

### 1. Load the config

Read the **Generated Artifacts** section of `.claude/ce-config.md`. Each row gives:

- **Source**: where the truth lives (a file, or a URL of a running service)
- **Precondition**: what must be running/available first (or `-`)
- **Fetch**: command that refreshes the local copy of the source (or `-` if the source is a file in the repo)
- **Generate**: command that regenerates the artifact
- **Outputs**: generated paths
- **Verify**: command(s) that check downstream consumers still build

If `{artifact}` is given, sync only that row; otherwise sync all rows. If the section is empty or `TBD`, report "No generated artifacts configured" and stop.

### 2. Check the precondition

If there's a precondition (e.g. a service must be reachable), check it, for example:

```bash
curl -sf <source URL> > /dev/null
```

If it fails, tell the user how to start it (use the "Start local services" command from `.claude/ce-config.md`) and stop. Do not proceed against a stale or missing source.

### 3. Fetch the source (if remote)

Run the **Fetch** command. Then check whether it changed:

```bash
git diff --stat -- <fetched source file>
```

If neither the source nor the outputs have changed since the last generation, report "Already in sync" and stop.

### 4. Regenerate

Run the **Generate** command. Don't hand-edit outputs; they are usually listed in `.claude/protected-paths`.

### 5. Verify consumers

Run the **Verify** command(s). If they fail, show the errors grouped by consumer and identify which source change caused each one.

### 6. Report

- What changed in the source (added/removed/changed endpoints, schemas, fields)
- Files regenerated
- Whether consumers build, and what needs fixing if not
