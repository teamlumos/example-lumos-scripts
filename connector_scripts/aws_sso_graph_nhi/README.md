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
  --customer-integrator-role-arn <customer-integrator-role-arn> \
  --verbose
```

Once the output looks right, set your API key and add `--live` to actually
create the integrations:

```bash
export LUMOS_API_KEY=<your-lumos-api-key>
python orchestrate.py \
  --stack-set-name lumos-nhi-cross-account-role \
  --service-role-external-id <external-id> \
  --customer-integrator-role-arn <customer-integrator-role-arn> \
  --live \
  --verbose
```

You can also pass the key directly as a flag instead of using the environment variable:

```bash
python orchestrate.py \
  --stack-set-name lumos-nhi-cross-account-role \
  --service-role-external-id <external-id> \
  --customer-integrator-role-arn <customer-integrator-role-arn> \
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
| `--customer-integrator-role-arn` | Yes | Copy from the connector's setup form in the Lumos platform (`AWS_SETUP.md` Step 1). |
| `--regions` | No | Comma-separated AWS region codes (e.g. `us-east-1,eu-west-1`) written into each created integration's `regions` setting. Leave empty to let the connector auto-discover and scan every region enabled on the account. |
| `--stackset-region` | No | Defaults to `us-east-1`. Must exactly match the region you created the StackSet in (`AWS_SETUP.md` Step 3.9) — StackSet lookups only work from that region. Unrelated to `--regions`. |
| `--disable-fetch` | No | Comma-separated fetch_* toggles to turn off (e.g. `--disable-fetch fetch_eks,fetch_bedrock_agent`). Every toggle not listed here is on by default, except `fetch_ecs_standalone_cloudtrail` — see `--enable-ecs-standalone-cloudtrail`. |
| `--enable-ecs-standalone-cloudtrail` | No | Turns on `fetch_ecs_standalone_cloudtrail`, the one fetch toggle that defaults off. Significantly slows down syncing — consult Lumos before enabling. |
| `--live` | No | Actually creates integrations. Without it, the script only shows what it would do. |
| `-v`, `--verbose` | No | Detailed logging. |

### Available `--disable-fetch` toggles

Every toggle below is **on by default** for every account this script connects, except
`fetch_ecs_standalone_cloudtrail` (off by default — pass `--enable-ecs-standalone-cloudtrail`
to turn it on). Pass `--disable-fetch <toggle1>,<toggle2>,...` to turn specific ones off —
e.g. `--disable-fetch fetch_eks,fetch_bedrock_agent`.

| Toggle | What it collects |
|---|---|
| `fetch_iam_users` | IAM users |
| `fetch_iam_groups` | IAM group membership and inherited group permissions |
| `fetch_iam_roles` | IAM role entitlements |
| `fetch_iam_policies` | IAM policy terminal resources (the ARNs a role's policies grant access to) |
| `fetch_federated_principals` | Federated principals (OIDC/SAML) |
| `fetch_lambda` | Lambda functions |
| `fetch_ecs` | ECS tasks & services |
| `fetch_ec2` | EC2 instance profiles |
| `fetch_glue` | Glue jobs |
| `fetch_step_functions` | Step Functions |
| `fetch_firehose` | Kinesis Firehose streams |
| `fetch_codepipeline` | CodePipeline pipelines |
| `fetch_sagemaker` | SageMaker jobs |
| `fetch_eventbridge` | EventBridge rules & pipes |
| `fetch_kafkaconnect` | MSK Connect connectors |
| `fetch_codebuild` | CodeBuild projects |
| `fetch_batch` | Batch job definitions |
| `fetch_apprunner` | App Runner services |
| `fetch_bedrock_agent` | Bedrock agents |
| `fetch_iot` | IoT role aliases |
| `fetch_roles_anywhere` | IAM Roles Anywhere profiles |
| `fetch_eks` | EKS workloads (nodes, pods, Fargate) |
| `fetch_secrets_manager` | Secrets Manager secrets |
| `fetch_ssm` | SSM SecureString parameters |
| `fetch_last_activity` | Last-activity data for all of the above (the master switch — disabling this turns off last-activity everywhere, regardless of the per-resource toggles above) |
| `fetch_ecs_standalone_cloudtrail` | **Off by default** — enable with `--enable-ecs-standalone-cloudtrail`. Extends ECS standalone task visibility past AWS's ~1 hour retention window by using CloudTrail instead. Significantly slows down syncing — consult Lumos before enabling |
| `fetch_batch_last_activity_cloudtrail` | Falls back to CloudTrail for Batch job last-activity once it's aged out of `ListJobs` — costs extra CloudTrail `LookupEvents` calls per sync |

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
