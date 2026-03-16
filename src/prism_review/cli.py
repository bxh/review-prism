"""CLI entry point for prism-review."""

import os
import re
import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from .github_client import fetch_pr_context
from .reviewer import perform_review
from .interactive import start_session


def parse_pr_url(url: str) -> tuple[str, int]:
    """Parse a GitHub PR URL into (owner/repo, pr_number).

    Accepts:
      - https://github.com/owner/repo/pull/123
      - owner/repo 123
    """
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)", url)
    if m:
        return m.group(1), int(m.group(2))
    raise click.BadParameter(
        f"Invalid PR URL: {url}\n"
        "Expected format: https://github.com/owner/repo/pull/123 or owner/repo PR_NUMBER"
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
    """Review a GitHub pull request.

    Accepts a PR URL or owner/repo + PR number:

    \b
      prism review https://github.com/owner/repo/pull/123
      prism review owner/repo 123
    """
    console = Console()

    # Parse input: either a full URL or owner/repo + number
    if pr_number is not None:
        owner_repo = pr_url
    else:
        try:
            owner_repo, pr_number = parse_pr_url(pr_url)
        except click.BadParameter as e:
            console.print(f"[red]{e}[/red]")
            sys.exit(1)

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

    # Fetch PR context
    console.print(f"Fetching PR #{pr_number} from {owner_repo}...")
    try:
        ctx = fetch_pr_context(github_token, owner_repo, pr_number)
    except Exception as e:
        console.print(f"[red]Error fetching PR: {e}[/red]")
        sys.exit(1)

    console.print(f"Reviewing: [bold]{ctx.title}[/bold] by {ctx.author}\n")

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
            output = f"review-{repo_name}-{pr_number}.md"
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
