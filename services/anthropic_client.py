"""
Anthropic Claude API client wrapper.
"""

from anthropic import Anthropic
from typing import List, Dict, Any, Optional
from config.settings import settings


class ClaudeClient:
    """Wrapper for Anthropic Claude API."""

    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

    def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> str:
        """
        Generate a completion from Claude.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

        return response.content[0].text

    def generate_with_context(
        self,
        prompt: str,
        context: Optional[str] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate with a simple prompt and optional context.

        Args:
            prompt: The user prompt
            context: Optional context to prepend
            system: Optional system prompt
            **kwargs: Additional arguments for generate()

        Returns:
            Generated text
        """
        user_message = prompt
        if context:
            user_message = f"Context:\n{context}\n\nTask:\n{prompt}"

        messages = [{"role": "user", "content": user_message}]

        return self.generate(messages=messages, system=system, **kwargs)


# Global client instance
_claude_client = None


def get_claude_client() -> ClaudeClient:
    """Get or create the global Claude client."""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
