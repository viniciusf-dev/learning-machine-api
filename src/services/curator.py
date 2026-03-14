"""
Memory curation service for user memory management.

Handles clearing and pruning user memories.
"""

import logging
from agno.agent import Agent

from src.core.errors import LearningMachineError
from src.domain.models import SessionContext

logger = logging.getLogger(__name__)


class MemoryCurator:
    """
    Handles memory management operations.
    
    Responsibilities:
    - Clearing user memories
    - Pruning old data
    - Error handling
    """

    def __init__(self, agent: Agent):
        self.agent = agent
        logger.debug("MemoryCurator initialized")

    def clear_user_memory(self, user_id: str) -> None:
        """
        Clear all memory for a user.
        
        Args:
            user_id: User identifier
            
        Raises:
            InvalidUserIdError: If user_id is invalid
            LearningMachineError: If operation fails
        """
        SessionContext._validate_user_id(user_id)

        try:
            logger.info(f"Clearing all memory for user={user_id}")

            lm = self.agent.get_learning_machine()
            if lm is None:
                raise LearningMachineError(
                    "Learning machine not available on agent"
                )

            curator = lm.curator
            if curator is None:
                raise LearningMachineError(
                    "Memory curator not available on learning machine"
                )

            curator.prune(user_id=user_id, max_age_days=0)

            logger.info(f"Successfully cleared memory for user={user_id}")

        except LearningMachineError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to clear memory for user={user_id}: {e}",
                exc_info=True,
            )
            raise LearningMachineError(f"Failed to clear memory: {str(e)}") from e
