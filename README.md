# Issue Triage Agent

Auto-labels, summarises, and deduplicates GitHub issues using Claude.

## Setup

1. Add `ANTHROPIC_API_KEY` to GitHub Secrets (Settings → Secrets → Actions)
2. Copy all files into your repo
3. Push and open a test issue - agent runs automatically!

## Local test
```bash
pip install anthropic PyGithub
export GITHUB_TOKEN=ghp_...
export ANTHROPIC_API_KEY=sk-ant-...
export GITHUB_REPO=yourname/yourrepo

python src/triage.py --dry-run
```
