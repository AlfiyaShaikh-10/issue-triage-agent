import os, json, time, re, argparse
import google.generativeai as genai
from github import Github, GithubException

GH_TOKEN = os.environ["GH_TOKEN"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]

REPOS_TO_WATCH = [
    "AlfiyaShaikh-10/triage-issues-test2"
]

VALID_LABELS = ["bug", "feature", "question", "docs", "chore"]
VALID_PRIORITY = ["high", "medium", "low"]

gh = Github(GH_TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = """You are an expert GitHub issue triager. Return ONLY a JSON object:
{
  "label": "bug|feature|question|docs|chore",
  "priority": "high|medium|low",
  "summary": "one concise sentence",
  "suggested_fix": "one sentence hint or null",
  "duplicate_of": null,
  "confidence": 0.95
}
IMPORTANT: Return ONLY raw JSON. No json fences. No extra text."""

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


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError("No JSON found in response")


def build_prompt(issue, closed):
    titles = "\n".join(f"  #{i.number}: {i.title}" for i in closed[:40])
    return f"Issue #{issue.number}\nTitle: {issue.title}\nBody:\n{(issue.body or '(empty)')[:2000]}\n\nClosed issues:\n{titles or 'none'}"


def classify(issue, closed):
    prompt = SYSTEM_PROMPT + "\n\n" + build_prompt(issue, closed)
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        data = extract_json(raw)
        data["label"] = data.get("label", "question").lower()
        data["priority"] = data.get("priority", "low").lower()
        if data["label"] not in VALID_LABELS:
            data["label"] = "question"
        if data["priority"] not in VALID_PRIORITY:
            data["priority"] = "low"
        return data
    except Exception as e:
        print(f"Classification error: {e}")
        return {
            "label": "question",
            "priority": "low",
            "summary": "Failed to analyze issue",
            "suggested_fix": None,
            "duplicate_of": None,
            "confidence": 0.0,
        }


def ensure_label(repo, name):
    try:
        repo.create_label(name, LABEL_COLORS.get(name, "ededed"))
    except:
        pass


def apply_labels(repo, issue, result):
    for l in [result["label"], result["priority"]]:
        ensure_label(repo, l)
    issue.add_to_labels(result["label"], result["priority"])
    print(f"  Labels: {result['label']} / {result['priority']}")


def post_comment(issue, result):
    bar = "█" * round(result["confidence"] * 10) + "░" * (
        10 - round(result["confidence"] * 10)
    )
    dup = (
        f"\n> Possible duplicate of #{result['duplicate_of']}"
        if result["duplicate_of"]
        else ""
    )
    fix = f"\n> Hint: {result['suggested_fix']}" if result.get("suggested_fix") else ""
    issue.create_comment(
        f"### Auto-triage Summary\n\n"
        f"**{result['summary']}**\n"
        f"{dup}{fix}\n\n"
        f"| Field | Value |\n|---|---|\n"
        f"| Type | `{result['label']}` |\n"
        f"| Priority | `{result['priority']}` |\n"
        f"| Confidence | `{bar}` {result['confidence']:.0%} |\n\n"
        f"Auto-triaged · Maintainer will review shortly"
    )


def triaged(issue):
    return bool({l.name for l in issue.labels} & set(VALID_LABELS))


def triage_repo(repo_name, dry_run=False):
    print(f"\nRepo: {repo_name}")
    try:
        repo = gh.get_repo(repo_name)
        open_i = list(repo.get_issues(state="open"))[:50]
        closed_i = list(repo.get_issues(state="closed"))[:60]
        pending = [i for i in open_i if not triaged(i)]
        print(f"   {len(pending)} issues to triage")

        for issue in pending:
            print(f"  #{issue.number}: {issue.title[:60]}")
            try:
                r = classify(issue, closed_i)
                print(f"    -> {r['label']}/{r['priority']} ({r['confidence']:.0%})")
                if not dry_run:
                    apply_labels(repo, issue, r)
                    post_comment(issue, r)
                time.sleep(1.5)
            except Exception as e:
                print(f"    Error: {e}")

    except Exception as e:
        print(f"   Repo error: {e}")


def triage_all_repos(dry_run=False):
    print(f"Starting triage for {len(REPOS_TO_WATCH)} repos...")
    for repo_name in REPOS_TO_WATCH:
        triage_repo(repo_name, dry_run)
    print("\nAll repos done!")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--repo", type=str, default=None, help="Single repo to triage e.g. user/repo"
    )
    args = p.parse_args()

    if args.repo:
        triage_repo(args.repo, args.dry_run)
    else:
        triage_all_repos(args.dry_run)
