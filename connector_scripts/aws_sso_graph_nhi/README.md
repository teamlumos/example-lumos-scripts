# Accounts Orchestration for AWS NHI

This script connects every eligible AWS account in your Organization to
Lumos. You run it yourself, using your own AWS login.

Before running it, complete the AWS setup in [`AWS_SETUP.md`](./AWS_SETUP.md)
— deploying the read-only role and generating a Lumos API key.

## What you'll need

1. The read-only role deployed via CloudFormation StackSet to the accounts
   you want Lumos to read (`AWS_SETUP.md`, Step 3).
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

The script needs valid AWS credentials for an identity that has
`organizations:ListAccounts` and `cloudformation:ListStackInstances` in your
management account — the same access you already used to set up the
StackSet. It does not require the AWS CLI to be installed, but the CLI is
the easiest way to get credentials in place before running it:

```bash
aws configure          # if you use IAM access keys
# or
aws sso login          # if you use IAM Identity Center / AWS SSO
```

Alternatively, run the script from an environment that already has AWS
credentials available, such as AWS CloudShell or an EC2 instance with an
attached role. Either way, confirm you're authenticated before running the
script:

```bash
aws sts get-caller-identity
```

## Usage

First, do a dry run to preview what will be connected — nothing gets created,
but the Lumos API key is needed to check which accounts are already connected:

```bash
export LUMOS_API_KEY=<your-lumos-api-key>
python orchestrate.py \
  --stack-set-name lumos-nhi-cross-account-role \
  --service-role-external-id <external-id> \
  --verbose
```

Once the output looks right, set your API key and add `--live` to actually
create the integrations:

```bash
export LUMOS_API_KEY=<your-lumos-api-key>
python orchestrate.py \
  --stack-set-name lumos-nhi-cross-account-role \
  --service-role-external-id <external-id> \
  --live \
  --verbose
```

You can also pass the key directly as a flag instead of using the environment variable:

```bash
python orchestrate.py \
  --stack-set-name lumos-nhi-cross-account-role \
  --service-role-external-id <external-id> \
  --live \
  --lumos-api-key <your-lumos-api-key> \
  --verbose
```

Running the script again later is safe — accounts that are already connected
are skipped, and only new or missing accounts are added.

### Options

| Flag | Required | Description |
|---|---|---|
| `--stack-set-name` | Yes | The StackSet name you chose in `AWS_SETUP.md` Step 3. |
| `--service-role-external-id` | Yes | Unique to your organization — from `AWS_SETUP.md` Step 1. |
| `--lumos-api-key` | Yes | From `AWS_SETUP.md` Step 4. Prefer `LUMOS_API_KEY` env var to keep the key out of shell history. |
| `--customer-integrator-role-arn` | No | Same for every customer — only override if Lumos tells you to use a different value. |
| `--per-account-role-name` | No | Defaults to `LumosNhiCrossAccountRole`. Only change this if you renamed the role in the template. |
| `--region` | No | Defaults to `us-east-1`. Must match the region you deployed the StackSet in. |
| `--disable-fetch` | No | Repeatable. Turns off collection of a specific resource type (e.g. `--disable-fetch fetch_eks`). |
| `--live` | No | Actually creates integrations. Without it, the script only shows what it would do. |
| `-v`, `--verbose` | No | Detailed logging. |

## What happens when you run it

1. Every account in your Organization is listed.
2. For each one, the script checks whether the read-only role was
   successfully deployed there. Accounts without it are skipped.
3. For every account with the role deployed, a Lumos integration is created
   (or previewed, without `--live`).
4. Accounts that are already connected are skipped automatically.
5. A summary is printed at the end: how many accounts were connected,
   already existed, failed, or were skipped.

If an account fails to connect, the script continues with the rest — a
single failure won't stop the whole run!
