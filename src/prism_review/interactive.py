"""Interactive follow-up REPL session."""

from collections.abc import Callable

from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.live import Live

from .github_client import PRContext
from .reviewer import _build_user_message


def start_session(
    api_key: str,
    messages: list[dict],
    model: str,
    reload_fn: Callable[[], PRContext] | None = None,
) -> None:
    """Run an interactive follow-up conversation loop."""
    client = OpenAI(api_key=api_key)
    console = Console()
    messages_system_content = messages[0]["content"]

    console.print("\n[bold]Interactive mode[/bold] — ask follow-up questions")
    console.print("  Commands: [dim]reload[/dim] — re-fetch PR/diff | [dim]quit/exit[/dim] — stop\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            console.print("Goodbye!")
            break

        if user_input.lower() == "reload":
            if not reload_fn:
                console.print("[yellow]Reload not available.[/yellow]")
                continue
            with Live(Spinner("dots", text="Reloading PR/diff..."), console=console, transient=True):
                try:
                    ctx = reload_fn()
                except Exception as e:
                    console.print(f"[red]Error reloading: {e}[/red]")
                    continue
            # Reset conversation: keep system prompt, replace with fresh context
            messages.clear()
            messages.append({"role": "system", "content": messages_system_content})
            messages.append({"role": "user", "content": _build_user_message(ctx)})
            messages.append({"role": "user", "content": "The PR/diff has been updated. Please review the latest changes."})

            with Live(Spinner("dots", text="Thinking..."), console=console, transient=True):
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                )

            reply = response.choices[0].message.content
            messages.append({"role": "assistant", "content": reply})

            console.print()
            console.print(Markdown(reply))
            console.print()
            continue

        messages.append({"role": "user", "content": user_input})

        with Live(Spinner("dots", text="Thinking..."), console=console, transient=True):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
            )

        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})

        console.print()
        console.print(Markdown(reply))
        console.print()
