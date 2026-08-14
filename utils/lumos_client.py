"""
Reference implementation of LumosClient and ConnectorConfig.

Copy these classes into your orchestrate.py — scripts remain self-contained
and should not import from this file directly.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LumosClient:
    """Handles all interactions with the Lumos platform API."""

    def __init__(self, api_key: str, base_url: str = "https://api.lumos.com") -> None:
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._base_url = base_url

    def integration_exists(self, app_class_id: str, instance_identifier: str) -> bool:
        """
        Returns True if a non-disconnected integration with this identifier already exists.
        Used for idempotency — re-running the main script won't duplicate integrations.

        docs: https://developers.lumos.com/reference/listapps-1
        """
        response = httpx.get(
            f"{self._base_url}/apps",
            headers=self._headers,
            params={
                "name_search": instance_identifier,
                "exact_match": "true",
                "disconnected": "false",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
        return any(item.get("app_class_id") == app_class_id for item in items)

    def create_integration(
        self,
        app_class_id: str,
        auth: dict[str, Any],
        settings: dict[str, Any],
        live: bool = False,
    ) -> str | None:
        """
        Creates a Lumos integration via POST /apps.
        Returns the created app ID, or None in dry-run mode.

        docs: https://developers.lumos.com/reference/createapp-1
        """
        payload: dict[str, Any] = {
            "app_class_id": app_class_id,
            "auth": auth,
            "settings": settings,
        }

        if not live:
            logger.info("[DRY RUN] Would POST %s/apps with: %s", self._base_url, payload)
            return None

        response = httpx.post(
            f"{self._base_url}/apps",
            headers=self._headers,
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        app_id: str = response.json().get("id")
        logger.info("Created Lumos integration id=%s", app_id)
        return app_id


class ConnectorConfig:
    """
    Base for connector-specific configuration.

    Subclass this in your orchestrate.py and implement all three methods.
    The app_class_id can be confirmed via:
      GET /integrations
    """

    app_class_id: str

    def instance_identifier(self, account_id: str) -> str:
        """
        Stable, deterministic per-account identifier used for idempotency.
        Must be unique within the connector — used as the integration name on search.

        Change this with care: altering it breaks idempotency for existing integrations.
        """
        raise NotImplementedError

    def auth_payload(self) -> dict[str, Any]:
        """
        Auth block sent to POST /apps.
        Shape is connector-specific — check the connection schema for the exact key name.
        """
        raise NotImplementedError

    def settings_payload(self) -> dict[str, Any]:
        """
        Settings block sent to POST /apps.
        Shape is connector-specific.
        """
        raise NotImplementedError
