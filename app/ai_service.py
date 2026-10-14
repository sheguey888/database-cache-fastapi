import asyncio


class TemporaryAIError(Exception):
    """Raised when an AI provider is temporarily unavailable."""


async def generate_text(prompt: str, task: str = "response") -> str:
    """Fake asynchronous AI call used when no provider API key is configured."""
    await asyncio.sleep(0.01)
    return f"{task.title()} for: {prompt}"
