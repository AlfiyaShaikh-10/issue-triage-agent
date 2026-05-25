# Rules: Issue Triage Agent

## Always do
- Return valid JSON only
- Apply one type label + one priority label per issue
- Skip already-triaged issues
- Wait 1 second between API calls

## Never do
- Close issues unless clearly duplicate
- Invent info not in the issue
- Triage the same issue twice

## When unsure
- Default label: question
- Default priority: low
- Set confidence below 0.6
