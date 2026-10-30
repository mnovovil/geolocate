---
description: Capture non-obvious session learnings to the project knowledge base
---

# /ce:compound — Capture Session Learnings

You are a senior engineer extracting reusable knowledge from this session.

## Flow

### 1. Load Rules
Read `.claude/skills/compound/SKILL.md` for categories, format, and quality bar.

### 2. Analyze the Session

Look back at what happened in this session:
- What problems were encountered?
- What solutions were found?
- What was surprising or non-obvious?
- What took longer than expected and why?
- What patterns emerged?

### 3. Apply Quality Bar

For each potential learning, ask: **"Would this surprise me in 2 weeks?"**

Skip anything that's:
- Obvious from reading code or docs
- A universal engineering best practice
- Already captured in `CLAUDE.md`, `.claude/learnings.md`, or existing skills

### 4. Write Entries

For each learning that passes the quality bar, format it as:

```markdown
### [Category] Title — YYYY-MM-DD

2-4 sentence description. Context, what was non-obvious, why it matters.
```

Use the categories from `.claude/skills/compound/SKILL.md`.

### 5. Append to Learnings

Append new entries to `.claude/learnings.md`. NEVER overwrite existing content.

### 6. Evaluate for CLAUDE.md

If any learning represents a **fundamental project convention** (not a one-off), suggest adding it to `CLAUDE.md` instead. Tell the user what you'd add and where.

### 7. Report

Tell the user:
- How many learnings were captured
- Brief summary of each
- Whether any CLAUDE.md updates are suggested
