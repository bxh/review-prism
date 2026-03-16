"""Interactive follow-up REPL session."""

from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.live import Live


def start_session(api_key: str, messages: list[dict], model: str) -> None:
    """Run an interactive follow-up conversation loop."""
    client = OpenAI(api_key=api_key)
    console = Console()

    console.print("\n[bold]Interactive mode[/bold] — ask follow-up questions (quit/exit/Ctrl-C to stop)\n")

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
