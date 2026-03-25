"""Claude CLI wrapper for architecture analysis.

Uses the local `claude` CLI (Claude Code) in print mode instead of the API.
Set ARCADE_MOCK=1 to skip all LLM calls and use heuristic fallbacks.
"""

import json
import os
import subprocess


MOCK_MODE = os.environ.get("ARCADE_MOCK", "").strip() in ("1", "true", "yes")
CLAUDE_MODEL = os.environ.get("ARCADE_MODEL", "sonnet")


def ask_claude(
    prompt: str,
    system: str = "",
    model: str | None = None,
    max_tokens: int = 8192,
) -> str:
    """Send a prompt to the local claude CLI and return the text response."""
    if MOCK_MODE:
        return "{}"

    model = model or CLAUDE_MODEL
    cmd = [
        "claude", "-p",
        "--model", model,
        "--output-format", "text",
        "--no-session-persistence",
    ]
    if system:
        cmd.extend(["--append-system-prompt", system])

    # Remove CLAUDECODE env var to allow running inside a Claude Code session
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed (exit {result.returncode}): {result.stderr}")

    return result.stdout.strip()


def ask_claude_json(
    prompt: str,
    system: str = "",
    model: str | None = None,
    max_tokens: int = 8192,
) -> dict:
    """Send a prompt to claude CLI and parse the JSON response."""
    if MOCK_MODE:
        return {}

    text = ask_claude(prompt, system=system, model=model, max_tokens=max_tokens)

    # Extract JSON from the response (handle markdown code blocks)
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # skip opening ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)
