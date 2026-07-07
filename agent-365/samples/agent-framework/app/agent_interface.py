"""Defines the common interface required by hosted agent implementations."""

from abc import ABC, abstractmethod
from typing import Optional

from microsoft_agents.hosting.core import Authorization, TurnContext


class AgentInterface(ABC):
    """Declares the lifecycle and messaging contract for agent implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Prepare the agent before it starts handling turns."""
        pass

    @abstractmethod
    async def process_user_message(
        self, message: str, auth: Authorization, auth_handler_name: Optional[str], context: TurnContext
    ) -> str:
        """Process a user message and return the response text."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Release resources owned by the agent implementation."""
        pass


def check_agent_inheritance(agent_class) -> bool:
    """Return whether the supplied class implements AgentInterface."""
    if not issubclass(agent_class, AgentInterface):
        print(f"❌ Agent {agent_class.__name__} does not inherit from AgentInterface")
        return False
    return True
