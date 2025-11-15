"""
Base agent class that all specialized agents inherit from.
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from services.anthropic_client import get_claude_client


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(self, name: str):
        self.name = name
        self.claude = get_claude_client()

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Must be implemented by each agent.
        """
        pass

    def think(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0
    ) -> str:
        """
        Use Claude to think through a problem.

        Args:
            prompt: The task or question
            context: Optional context information
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            Claude's response
        """
        system_prompt = self.get_system_prompt()

        return self.claude.generate_with_context(
            prompt=prompt,
            context=context,
            system=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )

    def log(self, message: str):
        """Log a message with agent name."""
        print(f"[{self.name}] {message}")
