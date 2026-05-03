"""
Base interface shared by every Neuro chat agent.
"""

from __future__ import annotations

from typing import Callable, Optional


class NeuroAgent:
    """Common interface that every provider agent must satisfy."""

    @property
    def available(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "unknown"

    def chat(self, message: str, on_token: Optional[Callable[[str], None]] = None) -> str:
        raise NotImplementedError

    def trigger_login(self) -> int:
        """Run the provider's interactive login flow. Returns exit code (0 = success)."""
        return 1

    def clear_history(self) -> None:
        pass

    def refresh_context(self) -> None:
        pass


class UnavailableAgent(NeuroAgent):
    """Returned by the factory when a provider cannot be initialised."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    @property
    def available(self) -> bool:
        return False

    @property
    def provider_name(self) -> str:
        return "unavailable"

    def chat(self, message: str, on_token: Optional[Callable[[str], None]] = None) -> str:
        return f"[Agent unavailable: {self.reason}]"
