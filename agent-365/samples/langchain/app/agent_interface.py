# Copyright (c) Microsoft. All rights reserved.

"""Shared host contract for LangChain-compatible agents."""

from abc import ABC, abstractmethod
from typing import Optional

from microsoft_agents.hosting.core import Authorization, TurnContext


class AgentInterface(ABC):
    """
    Abstract base class that any hosted agent must inherit from.

    This ensures agents implement the required methods at class definition time,
    providing stronger guarantees than a Protocol.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent and any required resources."""
        pass

    @abstractmethod
    async def process_user_message(
        self,
        message: str,
        auth: Authorization,
        auth_handler_name: Optional[str],
        context: TurnContext,
    ) -> str:
        """Process a user message and return a response."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up any resources used by the agent."""
        pass


def check_agent_inheritance(agent_class) -> bool:
    """Check that an agent class inherits from AgentInterface."""
    if not issubclass(agent_class, AgentInterface):
        print(f"❌ Agent {agent_class.__name__} does not inherit from AgentInterface")
        return False
    return True
