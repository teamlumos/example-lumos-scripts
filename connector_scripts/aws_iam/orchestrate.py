"""
Multi-account onboarding orchestration for the AWS IAM connector.

For every account in the Organization, checks whether the per-account StackSet role
(`LumosAwsIamCrossAccountRole` by default) deployed there, then creates a Lumos
integration for each account that has it.

Lumos authenticates using its own global service account, the customer's per-account role must trust that ARN.

Run without --live to preview what would be created (dry-run).

This script is self-contained.
"""

__version__ = "1.0.0"

import argparse
import logging
import os
import sys
from typing import Any

import boto3
import httpx
from botocore.exceptions import ClientError

logger = logging.getLogger("aws_iam_orchestration")


class LumosClient:
    """Handles all interactions with the Lumos platform API."""

    def __init__(self, api_key: str, base_url: str = "https://api.lumos.com") -> None:
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._base_url = base_url

    def integration_exists(self, app_class_id: str, instance_identifier: str) -> bool:
        """
        Returns True if a non-disconnected integration with this identifier already exists.
        Used for idempotency — re-running the script won't duplicate integrations.

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

    Subclass this and implement all three methods.
    The app_class_id can be confirmed via:
      GET /integrations/<app_class_id>/connection-schema
    """

    app_class_id: str

    def instance_identifier(self, account_id: str) -> str:
        raise NotImplementedError

    def auth_payload(self) -> dict[str, Any]:
        raise NotImplementedError

    def settings_payload(self, account_id: str, service_role_arn: str) -> dict[str, Any]:
        raise NotImplementedError


class AwsOrchestrator:
    """Handles AWS account enumeration via Organizations and CloudFormation StackSets."""

    def __init__(self, region: str, stack_set_name: str) -> None:
        self._stack_set_name = stack_set_name
        session = boto3.Session(region_name=region)
        self._orgs_client = session.client("organizations")
        self._cfn_client = session.client("cloudformation")

    def list_active_accounts(self) -> list[dict[str, Any]]:
        """
        Returns all ACTIVE accounts in the organization.
        https://docs.aws.amazon.com/boto3/latest/reference/services/organizations/client/list_accounts.html
        """
        accounts: list[dict[str, Any]] = []
        paginator = self._orgs_client.get_paginator("list_accounts")
        for page in paginator.paginate():
            for account in page["Accounts"]:
                if account.get("Status") == "ACTIVE":
                    accounts.append(account)
                else:
                    logger.info(
                        "Skipping account %s (%s) — status is %s",
                        account["Id"],
                        account.get("Name"),
                        account.get("Status"),
                    )
        logger.info("Found %d active account(s) in the org", len(accounts))
        return accounts

    def deployed_account_ids(self) -> set[str]:
        """
        Returns account IDs where the StackSet's stack-instance status is CURRENT.
        https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ListStackInstances.html
        """
        account_ids: set[str] = set()
        paginator = self._cfn_client.get_paginator("list_stack_instances")
        for page in paginator.paginate(StackSetName=self._stack_set_name):
            for instance in page["Summaries"]:
                account_id = instance["Account"]
                status = instance.get("Status")
                if status == "CURRENT":
                    account_ids.add(account_id)
                else:
                    logger.warning(
                        "Stack instance for account %s is %s, not CURRENT — skipping",
                        account_id,
                        status,
                    )
        logger.info(
            "Found %d account(s) with role deployed via StackSet %s",
            len(account_ids),
            self._stack_set_name,
        )
        return account_ids

    def service_role_arn_for(self, account_id: str) -> str:
        return f"arn:aws:iam::{account_id}:role/{PER_ACCOUNT_ROLE_NAME}"


def run_orchestration(
    aws: AwsOrchestrator,
    lumos: LumosClient,
    connector: ConnectorConfig,
    live: bool = False,
) -> None:
    """
    Main orchestration loop: for each AWS account with the role deployed,
    creates a Lumos integration, skipping accounts that are already connected.
    A single account failure never stops the rest.
    """
    accounts = aws.list_active_accounts()
    deployed_ids = aws.deployed_account_ids()

    created, skipped, already_exists, failed = 0, 0, 0, 0

    for account in accounts:
        account_id = account["Id"]

        if account_id not in deployed_ids:
            logger.warning(
                "Skipping account %s (%s) — StackSet has not deployed the role there",
                account_id,
                account.get("Name"),
            )
            skipped += 1
            continue

        service_role_arn = aws.service_role_arn_for(account_id)
        instance_id = connector.instance_identifier(account_id)

        try:
            if lumos.integration_exists(connector.app_class_id, instance_id):
                logger.info("Account %s already has an integration — skipping", account_id)
                already_exists += 1
                continue
        except httpx.HTTPError as e:
            logger.warning(
                "Could not check for existing integration for %s — proceeding anyway: %s",
                account_id,
                e,
            )

        try:
            lumos.create_integration(
                connector.app_class_id,
                connector.auth_payload(),
                connector.settings_payload(account_id, service_role_arn),
                live=live,
            )
            created += 1
        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to create integration for %s: %s %s",
                account_id,
                e.response.status_code,
                e.response.text,
            )
            failed += 1
        except httpx.HTTPError as e:
            logger.error("Failed to create integration for %s: %s", account_id, e)
            failed += 1

    logger.info(
        "Done. %d integration(s) %s, %d already existed, %d failed, %d account(s) skipped.",
        created,
        "created" if live else "dry-run logged (pass --live to actually create them)",
        already_exists,
        failed,
        skipped,
    )


PER_ACCOUNT_ROLE_NAME = "LumosAwsIamCrossAccountRole"


class AwsIamConnectorConfig(ConnectorConfig):
    app_class_id = "aws-iam_ics"

    def __init__(self, region: str, service_role_external_id: str) -> None:
        self._region = region
        self._service_role_external_id = service_role_external_id

    def instance_identifier(self, account_id: str) -> str:
        return f"aws-iam-{account_id}"

    def auth_payload(self) -> dict[str, Any]:
        return {
            "key": {},
            "impersonation_email": "",
            "tenant_id": "",
            "scopes": [],
        }

    def settings_payload(self, account_id: str, service_role_arn: str) -> dict[str, Any]:
        return {
            "region": self._region,
            "service_role_arn": service_role_arn,
            "service_role_external_id": self._service_role_external_id,
            "app_instance_identifier": service_role_arn,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--stack-set-name",
        required=True,
        help="Name of the CloudFormation StackSet that deployed the per-account role "
        "(see AWS_SETUP.md Step 3), e.g. lumos-iam-cross-account-role.",
    )
    parser.add_argument(
        "--service-role-external-id",
        required=True,
        help="Unique per customer — shown in the connector's setup form in the Lumos app.",
    )
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument(
        "--lumos-api-key",
        default=os.environ.get("LUMOS_API_KEY"),
        help="Lumos platform API key. Can also be set via the LUMOS_API_KEY environment variable.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually create integrations. Without this flag, only logs what would be done.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not args.lumos_api_key:
        logger.error("--lumos-api-key (or LUMOS_API_KEY env var) is required")
        sys.exit(1)

    connector = AwsIamConnectorConfig(
        region=args.region,
        service_role_external_id=args.service_role_external_id,
    )
    aws = AwsOrchestrator(
        region=args.region,
        stack_set_name=args.stack_set_name,
    )
    lumos = LumosClient(api_key=args.lumos_api_key)

    try:
        run_orchestration(aws, lumos, connector, live=args.live)
    except ClientError as e:
        logger.error("Fatal AWS error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
