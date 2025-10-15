"""User management service for DOMjudge API."""

import json
from typing import Any

from dom.infrastructure.api.client import DomJudgeClient
from dom.logging_config import get_logger
from dom.types.api import models

logger = get_logger(__name__)


class UserService:
    """
    Service for managing users in DOMjudge.

    Handles all user-related API operations.
    """

    def __init__(self, client: DomJudgeClient):
        """
        Initialize the user service.

        Args:
            client: Base API client for HTTP operations
        """
        self.client = client

    def get(self, user_id: int) -> models.User:
        """
        Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User model
        """
        data = self.client.get(f"/api/v4/users/{user_id}/", cache_key=f"user_{user_id}")
        logger.debug(f"Fetched user {user_id}")
        return models.User(**data)

    def list_all(self) -> list[dict[str, Any]]:
        """
        List all users.

        Returns:
            List of user dictionaries
        """
        data = self.client.get("/api/v4/users", cache_key="users_list")
        logger.debug(f"Fetched {len(data)} users")
        return data  # type: ignore[return-value]

    def add(self, user_data: models.AddUser) -> str:
        """
        Add a user or get existing one.

        Args:
            user_data: User data to add

        Returns:
            User ID
        """
        # Check if user already exists
        for user in self.list_all():
            if user["name"] == user_data.username:
                logger.info(f"User '{user_data.username}' already exists")
                return user["id"]  # type: ignore[no-any-return]

        # Create new user
        data = json.loads(user_data.model_dump_json(exclude_unset=True))
        data["password"] = user_data.password.get_secret_value()  # type: ignore[union-attr]

        response = self.client.post("/api/v4/users", json=data, invalidate_cache="users_list")

        logger.info(f"Created user '{user_data.username}'")
        return response  # type: ignore[return-value]
