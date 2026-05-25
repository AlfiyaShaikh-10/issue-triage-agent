# Skill: Issue Triage

## What this skill does
Classifies a GitHub issue into label, priority, and summary using Claude.

## Input
- Issue title + body
- List of recently closed issues (for duplicate detection)

## Output (JSON)
```json
{
  "label": "bug | feature | question | docs | chore",
  "priority": "high | medium | low",
  "summary": "one sentence",
  "suggested_fix": "hint or null",
  "duplicate_of": "number or null",
  "confidence": 0.95
}
```

## Label Rules
| Label    | When |
|----------|------|
| bug      | Something broken |
| feature  | New functionality |
| question | User needs help |
| docs     | Docs issue |
| chore    | Maintenance/CI |

## Priority Rules
| Priority | When |
|----------|------|
| high     | Crash/data loss/security |
| medium   | Has workaround |
| low      | Nice to have |
