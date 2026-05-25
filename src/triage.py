import os, json, time, re, argparse
import anthropic
from github import Github, GithubException

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
REPO_NAME = os.environ["GITHUB_REPO"]

VALID_LABELS = ["bug", "feature", "question", "docs", "chore"]
VALID_PRIORITY = ["high", "medium", "low"]

gh = Github(GITHUB_TOKEN)
claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
repo = gh.get_repo(REPO_NAME)

SYSTEM_PROMPT = """You are an expert GitHub issue triager. Return ONLY a JSON object:
{
  "label": "bug|feature|question|docs|chore",
  "priority": "high|medium|low",
  "summary": "one concise sentence",
  "suggested_fix": "one sentence hint or null",
  "duplicate_of": null,
  "confidence": 0.95
}
No markdown, no explanation. JSON only."""

LABEL_COLORS = {
    "bug": "d73a4a",
    "feature": "a2eeef",
    "question": "d876e3",
    "docs": "0075ca",
    "chore": "e4e669",
    "high": "b60205",
    "medium": "fbca04",
    "low": "0e8a16",
}


def build_prompt(issue, closed):
    titles = "\n".join(f"  #{i.number}: {i.title}" for i in closed[:40])
    return f"Issue #{issue.number}\nTitle: {issue.title}\nBody:\n{(issue.body or '(empty)')[:2000]}\n\nClosed issues:\n{titles or 'none'}"


def classify(issue, closed):
    msg = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(issue, closed)}],
    )
    raw = msg.content[0].text.strip()
    try:
        data = json.loads(raw)
    except:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group())
    data["label"] = data.get("label", "question").lower()
    data["priority"] = data.get("priority", "low").lower()
    if data["label"] not in VALID_LABELS:
        data["label"] = "question"
    if data["priority"] not in VALID_PRIORITY:
        data["priority"] = "low"
    return data


def ensure_label(name):
    try:
        repo.create_label(name, LABEL_COLORS.get(name, "ededed"))
    except:
        pass


def apply_labels(issue, result):
    for l in [result["label"], result["priority"]]:
        ensure_label(l)
    issue.add_to_labels(result["label"], result["priority"])
    print(f"  Labels: {result['label']} / {result['priority']}")


def post_comment(issue, result):
    bar = "X" * round(result["confidence"] * 10) + "-" * (
        10 - round(result["confidence"] * 10)
    )
    dup = f"\nDuplicate of #{result['duplicate_of']}" if result["duplicate_of"] else ""
    fix = f"\nHint: {result['suggested_fix']}" if result.get("suggested_fix") else ""
    issue.create_comment(
        f"""### Auto-triage\n**{result['summary']}**{dup}{fix}\n\n|Field|Value|\n|---|---|\n|Type|`{result['label']}`|\n|Priority|`{result['priority']}`|\n|Confidence|`{bar}` {result['confidence']:.0%}|\n\n*Auto-triaged. Maintainer will review.*"""
    )


def flag_dup(issue, num):
    try:
        orig = repo.get_issue(int(num))
        issue.create_comment(f"Duplicate of #{num} ({orig.title}). Closing.")
        issue.edit(state="closed")
        ensure_label("duplicate")
        issue.add_to_labels("duplicate")
    except Exception as e:
        print(f"  Dup error: {e}")


def triaged(issue):
    return bool({l.name for l in issue.labels} & set(VALID_LABELS))


def triage_all(max_issues=50, dry_run=False):
    open_i = list(repo.get_issues(state="open"))[:max_issues]
    closed_i = list(repo.get_issues(state="closed"))[:60]
    pending = [i for i in open_i if not triaged(i)]
    print(f"{len(pending)} issues to triage")
    for issue in pending:
        print(f"#{issue.number}: {issue.title[:60]}")
        try:
            r = classify(issue, closed_i)
            print(f"  -> {r['label']}/{r['priority']} ({r['confidence']:.0%})")
            if not dry_run:
                apply_labels(issue, r)
                post_comment(issue, r)
                if r["duplicate_of"]:
                    flag_dup(issue, r["duplicate_of"])
            time.sleep(1)
        except Exception as e:
            print(f"  Error: {e}")
    print("Done!")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max", type=int, default=50)
    p.add_argument("--issue", type=int, default=None)
    args = p.parse_args()
    if args.issue:
        issue = repo.get_issue(args.issue)
        closed = list(repo.get_issues(state="closed"))[:60]
        r = classify(issue, closed)
        print(json.dumps(r, indent=2))
        if not args.dry_run:
            apply_labels(issue, r)
            post_comment(issue, r)
    else:
        triage_all(args.max, args.dry_run)
