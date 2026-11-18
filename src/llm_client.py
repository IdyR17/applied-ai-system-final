"""
Thin wrapper around the Claude API.

This is the only file that knows which AI provider we use. Everything else
calls ask_llm(prompt, system) and gets a plain string back.
"""

import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-opus-5-5"


class LLMError(RuntimeError):
    """Raised when the AI can't be reached or returns no usable answer."""


def ask_llm(prompt: str, system: str) -> str:
    """Send one prompt to Claude and return its text reply."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMError(
            "ANTHROPIC_API_KEY is missing. Create a .env file in the project root "
            "with the line: ANTHROPIC_API_KEY=your-key-here"
        )

    model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key, timeout=60.0)

    try:
        response = client.beta.messages.create(
            model=model,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            # Short, simple tasks: low effort keeps it fast and cheap.
            output_config={"effort": "low"},
            # If a safety classifier declines, let the API retry on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise LLMError("The API key was rejected. Check ANTHROPIC_API_KEY in .env.") from e
    except anthropic.RateLimitError as e:
        raise LLMError("Rate limited by the API. Try again in a minute.") from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise LLMError("Could not connect to the API. Check your internet connection.") from e

    if response.stop_reason == "refusal":
        raise LLMError("The model declined to answer this request.")

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise LLMError("The model returned an empty answer.")
    return text
