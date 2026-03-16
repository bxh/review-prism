# prism-review

AI-powered GitHub PR code review CLI. Fetches PR data (diff, file contents, comments) and sends it to OpenAI for a thorough code review, with an interactive follow-up session.

## Setup

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- A GitHub personal access token
- An OpenAI API key

### Installation

```bash
git clone https://github.com/your-username/prism-review.git
cd prism-review
uv venv && source .venv/bin/activate
uv pip install -e .
```

### Configuration

Set the required environment variables:

```bash
export GITHUB_TOKEN=ghp_your_token_here
export OPENAI_API_KEY=sk-your_key_here
```

Or copy `.env.example` to `.env` and fill in the values.

## Usage

```bash
prism review <pr-url-or-owner/repo> [pr_number] [--model MODEL] [--no-interactive]
```

### Examples

```bash
# Review a PR by URL
prism review https://github.com/facebook/react/pull/42

# Or by owner/repo + number
prism review facebook/react 42

# Use a specific model
prism review https://github.com/django/django/pull/18231 --model gpt-4.1

# Skip interactive follow-up
prism review https://github.com/torvalds/linux/pull/999 --no-interactive
```

### Options

| Option             | Default   | Description                        |
| ------------------ | --------- | ---------------------------------- |
| `--model`          | `gpt-5.4` | OpenAI model to use                |
| `--no-interactive` | `false`   | Skip interactive follow-up session |

## How It Works

1. Fetches PR metadata, diff, changed file contents, and comments via the GitHub API
2. Sends the assembled context to OpenAI with a senior code reviewer system prompt
3. Renders the review as Markdown in the terminal
4. Enters an interactive session for follow-up questions (type `quit` or `exit` to stop)

## License

MIT
