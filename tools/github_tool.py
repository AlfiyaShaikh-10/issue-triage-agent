from github import Github, GithubException
import os

gh   = Github(os.environ["GITHUB_TOKEN"])
repo = gh.get_repo(os.environ["GITHUB_REPO"])

def get_open_issues(n=50):   return list(repo.get_issues(state="open"))[:n]
def get_closed_issues(n=60): return list(repo.get_issues(state="closed"))[:n]

def add_label(issue, name, color="ededed"):
    try: repo.create_label(name, color)
    except GithubException: pass
    issue.add_to_labels(name)

def post_comment(issue, body): issue.create_comment(body)
def close_issue(issue):        issue.edit(state="closed")
