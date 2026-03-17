"""CLI entry point for prism-review."""

import os
import re
import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from .github_client import fetch_pr_context, fetch_diff_context
from .reviewer import perform_review
from .interactive import start_session


def parse_input(url: str) -> dict:
    """Parse a GitHub PR URL, compare diff URL, or owner/repo into structured input.

    Returns a dict with type and parsed fields.
    """
    # PR URL: https://github.com/owner/repo/pull/123
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)", url)
    if m:
        return {"type": "pr", "owner_repo": m.group(1), "pr_number": int(m.group(2))}

    # Compare URL (with or without .diff): https://github.com/owner/repo/compare/base...head[.diff]
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/compare/(.+?)(?:\.diff)?$", url)
    if m:
        base, _, head = m.group(2).partition("...")
        if head:
            return {"type": "diff", "owner_repo": m.group(1), "base": base, "head": head, "url": url}

    # Bare owner/repo (needs pr_number as second arg)
    if re.match(r"^[^/]+/[^/]+$", url):
        return {"type": "owner_repo", "owner_repo": url}

    raise click.BadParameter(
        f"Invalid input: {url}\n"
        "Expected: PR URL, compare URL, or owner/repo"
    )


@click.group()
def main():
    """prism-review — AI-powered PR code review."""
    load_dotenv()


@main.command()
@click.argument("pr_url")
@click.argument("pr_number", type=int, required=False, default=None)
@click.option("--model", default="gpt-5.4", help="OpenAI model to use.")
@click.option("--no-interactive", is_flag=True, help="Skip interactive follow-up session.")
@click.option("-o", "--save", is_flag=True, default=False, help="Save review report with auto-generated name.")
@click.option("--output", type=click.Path(), default=None, help="Save review report to a specific file.")
def review(pr_url: str, pr_number: int | None, model: str, no_interactive: bool, save: bool, output: str | None):
    """Review a GitHub pull request or compare diff.

    Accepts a PR URL, compare .diff URL, or owner/repo + PR number:

    \b
      prism review https://github.com/owner/repo/pull/123
      prism review https://github.com/owner/repo/compare/main...branch.diff
      prism review owner/repo 123
    """
    console = Console()

    # Parse input
    try:
        parsed = parse_input(pr_url)
    except click.BadParameter as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    if parsed["type"] == "owner_repo" and pr_number is not None:
        parsed = {"type": "pr", "owner_repo": parsed["owner_repo"], "pr_number": pr_number}
    elif parsed["type"] == "owner_repo":
        console.print("[red]Error: PR number required when using owner/repo format.[/red]")
        sys.exit(1)

    owner_repo = parsed["owner_repo"]

    # Validate env vars
    github_token = os.environ.get("GITHUB_TOKEN")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    missing = []
    if not github_token:
        missing.append("GITHUB_TOKEN")
    if not openai_api_key:
        missing.append("OPENAI_API_KEY")
    if missing:
        console.print(
            f"[red]Error: missing environment variable(s): {', '.join(missing)}[/red]\n"
            "Set them in your shell or in a .env file. See .env.example."
        )
        sys.exit(1)

    # Fetch context
    try:
        if parsed["type"] == "pr":
            pr_num = parsed["pr_number"]
            console.print(f"Fetching PR #{pr_num} from {owner_repo}...")
            ctx = fetch_pr_context(github_token, owner_repo, pr_num)
        else:
            console.print(f"Fetching diff from {owner_repo} ({parsed['base']}...{parsed['head']})...")
            ctx = fetch_diff_context(github_token, parsed["url"], owner_repo, parsed["base"], parsed["head"])
    except Exception as e:
        console.print(f"[red]Error fetching PR: {e}[/red]")
        sys.exit(1)

    console.print(f"Reviewing: [bold]{ctx.title}[/bold]{' by ' + ctx.author if ctx.author else ''}\n")

    # Perform review
    console.print(f"Sending to {model} for review...\n")
    try:
        review_text, messages = perform_review(openai_api_key, ctx, model)
    except Exception as e:
        console.print(f"[red]Error during review: {e}[/red]")
        sys.exit(1)

    # Render review
    console.print(Markdown(review_text))

    # Save report
    if save or output:
        if not output:
            repo_name = owner_repo.replace("/", "-")
            if parsed["type"] == "pr":
                output = f"review-{repo_name}-{parsed['pr_number']}.md"
            else:
                output = f"review-{repo_name}-{parsed['head'].replace('/', '-')}.md"
        with open(output, "w") as f:
            f.write(f"# Code Review: {ctx.title}\n\n")
            f.write(f"**PR**: {ctx.url}  \n")
            f.write(f"**Author**: {ctx.author}  \n")
            f.write(f"**Model**: {model}\n\n---\n\n")
            f.write(review_text)
        console.print(f"\nReport saved to [bold]{output}[/bold]")

    # Interactive follow-up
    if not no_interactive:
        start_session(openai_api_key, messages, model)
