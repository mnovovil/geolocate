---
name: scaffold
description: Scaffold a new unit (endpoint, module, component, pipeline step...) across all its layers by mirroring a reference implementation listed in ce-config
user-invocable: true
disable-model-invocation: true
arguments:
  - name: recipe
    description: "Recipe name from the Scaffold Recipes table in .claude/ce-config.md (e.g. endpoint)"
    required: true
  - name: name
    description: "Name of the new unit in snake_case (e.g. geocode_request)"
    required: true
  - name: description
    description: "Brief description of what this unit represents"
    required: false
---

# Scaffold

Create a new `{recipe}` named `{name}` by copying the structure of an existing, known-good implementation — not by inventing a pattern.

## Steps

### 1. Load the recipe

Read the **Scaffold Recipes** section of `.claude/ce-config.md` and find the row for `{recipe}`. It gives:

- **Reference**: an existing unit to mirror (e.g. `user`)
- **Files**: path templates for each layer, using `{name}` as the placeholder
- **Register in**: files where the new unit must be wired up (router registry, `__init__`, index exports, DI container…)
- **Follow-up**: commands to run afterwards (migrations, codegen, tests)

If the recipe is missing or `TBD`, stop and tell the user. Offer to draft the recipe by looking for the most complete existing unit of that kind in the codebase, and confirm it with them before scaffolding.

### 2. Derive names

From `{name}` (snake_case) derive whatever casings the reference uses: PascalCase for types/classes, camelCase, kebab-case for URLs/files, and the plural form for collections and route prefixes. Match the reference's naming exactly (suffixes like `_service`, `Repository`, `Props`, etc.).

### 3. Read the reference

Read **every** file of the reference unit, plus the "Register in" files. Note:

- Imports, base classes, and helpers it reuses (reuse them — don't reimplement)
- Cross-cutting concerns it applies: auth, authorization/data scoping, validation, logging, error handling
- Docstring/comment language and density

### 4. Create each layer

For each path in **Files**, create the new file by adapting the reference:

- Rename identifiers to the derived names
- Replace the reference's domain fields with fields from `{description}` (ask if unclear — don't guess a schema)
- Keep every cross-cutting concern from the reference. Never drop auth or data scoping to "keep it simple"
- Remove logic specific to the reference's domain that doesn't apply

If a layer's file already exists, stop and report it instead of overwriting.

### 5. Register

Wire the new unit into each "Register in" file, placed next to the reference's registration.

### 6. Add tests

Mirror the reference's tests for the new unit (same file layout, same fixtures). At minimum: happy path, not-found/invalid input, and the auth/scoping behavior if the reference has any.

### 7. Verify and remind

Run the lint, type-check, and unit-test commands from `.claude/ce-config.md` on the new files. Then list the recipe's **Follow-up** steps for the user (e.g. "create a migration", "run `/sync-generated`").
