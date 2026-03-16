"""GitHub API client for fetching PR context."""

from dataclasses import dataclass, field
from github import Github



@dataclass
class PRContext:
    title: str
    body: str
    author: str
    base_branch: str
    head_branch: str
    url: str
    diff: str
    file_contents: dict[str, str] = field(default_factory=dict)
    review_comments: list[str] = field(default_factory=list)
    issue_comments: list[str] = field(default_factory=list)


def fetch_pr_context(token: str, owner_repo: str, pr_number: int) -> PRContext:
    """Fetch all relevant context for a PR."""
    g = Github(token)
    repo = g.get_repo(owner_repo)
    pr = repo.get_pull(pr_number)

    # Build unified diff from file patches
    diff_parts = []
    file_contents = {}
    for f in pr.get_files():
        if f.patch:
            diff_parts.append(f"--- a/{f.filename}\n+++ b/{f.filename}\n{f.patch}")
        # Fetch current file content for changed files
        try:
            content_file = repo.get_contents(f.filename, ref=pr.head.sha)
            if not isinstance(content_file, list):
                file_contents[f.filename] = content_file.decoded_content.decode(
                    "utf-8", errors="replace"
                )
        except Exception:
            pass  # File may have been deleted

    diff = "\n".join(diff_parts)

    # Collect review comments (inline)
    review_comments = []
    for comment in pr.get_review_comments():
        review_comments.append(
            f"[{comment.user.login} on {comment.path}:{comment.position}] {comment.body}"
        )

    # Collect issue comments (top-level)
    issue_comments = []
    for comment in pr.get_issue_comments():
        issue_comments.append(f"[{comment.user.login}] {comment.body}")

    ctx = PRContext(
        title=pr.title,
        body=pr.body or "",
        author=pr.user.login,
        base_branch=pr.base.ref,
        head_branch=pr.head.ref,
        url=pr.html_url,
        diff=diff,
        file_contents=file_contents,
        review_comments=review_comments,
        issue_comments=issue_comments,
    )

    return ctx
