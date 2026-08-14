# Accounts Orchestration for AWS IAM

This script connects every eligible AWS account in your Organization to
Lumos via the AWS IAM connector. Each account becomes a separate integration,
allowing Lumos to manage the local IAM users, groups, and policies within it.

Before running it, complete the AWS setup in [`AWS_SETUP.md`](./AWS_SETUP.md)
— deploying the cross-account role and generating a Lumos API key.

## What you'll need

1. The cross-account role deployed via CloudFormation StackSet to the accounts
   you want Lumos to manage (`AWS_SETUP.md`, Step 3).
2. An AWS login with access to your Organization's accounts and StackSets.
3. A Lumos API key (`AWS_SETUP.md`, Step 4).
4. Your **Service Role External ID**, shown in the connector's setup form in
   the Lumos app (`AWS_SETUP.md`, Step 1).

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Authenticating with AWS

The script needs valid AWS credentials with `organizations:ListAccounts` and
`cloudformation:ListStackInstances` in your management account:

```bash
aws configure          # if you use IAM access keys
# or
aws sso login          # if you use IAM Identity Center / AWS SSO
```

Confirm you're authenticated before running:

```bash
aws sts get-caller-identity
```

## Usage

First, do a dry run to preview what will be connected:

```bash
export LUMOS_API_KEY=<your-lumos-api-key>
python orchestrate.py \
  --stack-set-name lumos-iam-cross-account-role \
  --service-role-external-id <external-id> \
  --verbose
```

Once the output looks right, add `--live` to actually create the integrations:

```bash
export LUMOS_API_KEY=<your-lumos-api-key>
python orchestrate.py \
  --stack-set-name lumos-iam-cross-account-role \
  --service-role-external-id <external-id> \
  --live \
  --verbose
```

Running the script again later is safe — accounts that are already connected
are skipped automatically.

## Options

| Flag | Required | Description |
|---|---|---|
| `--stack-set-name` | Yes | The StackSet name from `AWS_SETUP.md` Step 3. |
| `--service-role-external-id` | Yes | From `AWS_SETUP.md` Step 1. |
| `--lumos-api-key` | Yes | From `AWS_SETUP.md` Step 4. Prefer `LUMOS_API_KEY` env var. |
| `--per-account-role-name` | No | Defaults to `LumosAwsIamCrossAccountRole`. |
| `--region` | No | Defaults to `us-east-1`. Must match the StackSet's region. |
| `--live` | No | Actually creates integrations. Without it, dry-run only. |
| `-v`, `--verbose` | No | Detailed logging. |
| `--version` | No | Print the script version and exit. |

## What happens when you run it

1. Every active account in your Organization is listed.
2. For each one, the script checks whether the cross-account role was
   successfully deployed there via the StackSet. Accounts without it are skipped.
3. For every account with the role deployed, a Lumos integration is created
   (or previewed, without `--live`).
4. Accounts that are already connected are skipped automatically.
5. A summary is printed at the end.

A single account failure won't stop the rest of the run.
