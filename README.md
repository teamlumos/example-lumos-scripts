# Accounts Orchestration

Developer tooling for bulk-creating Lumos integrations across many accounts or tenants.
Each script automates what would otherwise be done manually in the Lumos UI — discovering
which accounts are ready to connect and calling `POST /apps` for each one.

---

## Available connectors

| Connector | Description |
|---|---|
| `connectors/aws_sso_graph_nhi/` | Multi-account onboarding for the AWS SSO Graph (NHI) connector |
| `connectors/aws_iam/` | Multi-account onboarding for the AWS IAM connector |

See each connector's `README.md` for setup and usage instructions.

---

## How scripts work

Each `orchestrate.py` script:
1. Discovers which accounts/tenants have the prerequisites deployed (e.g. a cross-account role via CloudFormation StackSets).
2. Calls `GET /apps` to check whether an integration already exists for each account (idempotent — safe to re-run).
3. Calls `POST /apps` to create the integration for accounts that don't have one yet.

All scripts default to dry-run mode and require `--live` to actually create integrations.

---

## Adding a new connector script

1. Create a new directory under `connectors/<connector_name>/`.
2. Copy `lumos_client.py` into your `orchestrate.py` — scripts must be self-contained, no shared imports.
3. Subclass `ConnectorConfig` with the connector-specific `app_class_id`, `auth_payload`, `settings_payload`, and `instance_identifier`.
4. Add `requirements.txt`, `README.md`, and any setup guides or infrastructure templates.

The `app_class_id` and auth credential key name for a connector can be confirmed via:
```
GET /integrations/<app_class_id>/connection-schema
```

---

## Reference: LumosClient

`lumos_client.py` is the canonical source for `LumosClient` and `ConnectorConfig`.
When it changes, update the inlined copies in each connector script.

**`LumosClient`** — wraps `GET /apps` (idempotency check) and `POST /apps` (create integration).

**`ConnectorConfig`** — base class with three methods to implement:
- `instance_identifier(account_id)` — stable per-account name, used for idempotency
- `auth_payload()` — connector-specific auth block sent to `POST /apps`
- `settings_payload(account_id)` — connector-specific settings block
