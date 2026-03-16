"""OpenAI-based code review logic."""

from openai import OpenAI

from .github_client import PRContext


SYSTEM_PROMPT = """\
You are a senior software engineer performing a thorough code review on a GitHub pull request.

Your review should cover:
- **Correctness**: Logic errors, edge cases, off-by-one errors, race conditions
- **Security**: Injection vulnerabilities, auth issues, data exposure
- **Performance**: Unnecessary allocations, N+1 queries, missing indexes
- **Maintainability**: Naming, structure, duplication, missing abstractions
- **Testing**: Missing test coverage, brittle tests

Format your review in Markdown. Start with a brief summary, then list specific findings \
grouped by severity (Critical / Warning / Suggestion / Nitpick). Reference file names and \
line numbers from the diff when possible.

If the PR looks good, say so — don't invent issues."""


def _build_user_message(ctx: PRContext) -> str:
    """Assemble the PR context into a single user message."""
    sections = [
        f"# PR #{ctx.url.split('/')[-1]}: {ctx.title}",
        f"**Author**: {ctx.author}  ",
        f"**Branches**: {ctx.head_branch} → {ctx.base_branch}",
    ]

    if ctx.body:
        sections.append(f"\n## Description\n{ctx.body}")

    sections.append(f"\n## Diff\n```diff\n{ctx.diff}\n```")

    if ctx.file_contents:
        sections.append("\n## Full File Contents (changed files)")
        for path, content in ctx.file_contents.items():
            sections.append(f"\n### {path}\n```\n{content}\n```")

    if ctx.review_comments:
        sections.append("\n## Existing Review Comments")
        for c in ctx.review_comments:
            sections.append(f"- {c}")

    if ctx.issue_comments:
        sections.append("\n## Issue Comments")
        for c in ctx.issue_comments:
            sections.append(f"- {c}")

    return "\n".join(sections)


def perform_review(
    api_key: str, ctx: PRContext, model: str = "gpt-5.4"
) -> tuple[str, list[dict]]:
    """Send PR context to OpenAI and return (review_text, messages)."""
    client = OpenAI(api_key=api_key)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_message(ctx)},
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
    )

    review_text = response.choices[0].message.content
    messages.append({"role": "assistant", "content": review_text})

    return review_text, messages
