# AWS IAM Identity Center (NHI) Setup — Multi-Account Onboarding

This guide walks you through connecting Lumos to every AWS account in your
Organization. You'll do two things:

1. Deploy a read-only IAM role to each account you want Lumos to monitor.
2. Run a script that finds those accounts and connects them to Lumos.

---

## Step 1 — Get your Lumos Customer Integrator Role ARN and Service Role External ID

Open the connector's setup page in the Lumos app and copy:
- **Lumos Customer Integrator Role ARN** — you'll need this in Steps 3 and 5.
- **Service Role External ID** — you'll need this in Steps 3 and 5.

## Step 2 — Enable trusted access for CloudFormation StackSets

This is a one-time setting for your Organization:

1. Open the **AWS Organizations console** from your **management account**.
2. In the left sidebar, click **Services**.
3. Find **CloudFormation StackSets** in the list.
4. Click **Enable trusted access**.

## Step 3 — Deploy the read-only role to your accounts

1. Download the `lumos-nhi-role.yaml` template (see **Appendix A**).
2. In the **CloudFormation console**, go to **StackSets → Create StackSet**.
3. **Permissions**: choose **Service-managed permissions**.
4. **Specify template**: choose **Upload a template file** and upload
   `lumos-nhi-role.yaml`.
5. Give the StackSet a name, for example `lumos-nhi-cross-account-role`.
   You'll need this name in Step 5.
6. **Parameters**: enter your **Lumos Customer Integrator Role ARN** and **Service Role External ID** from Step 1 when prompted.
7. On the **Configure StackSet options** screen, check the box acknowledging
   that CloudFormation may create IAM resources with custom names.
8. **Deployment targets**: choose the accounts or organizational units you
   want Lumos to read. Only accounts you select here will be connected.
9. **Specify regions**: pick one region, for example `us-east-1`. Remember which one —
   you'll pass it as `--stackset-region` in Step 5 if it isn't `us-east-1` (the script's
   default), since StackSet lookups only work from the region the StackSet was created in.
10. Submit. Deployment takes a few minutes. Check progress under the
    StackSet's **Stack instances** tab — every target account should show
    **SUCCEEDED**.

## Step 4 — Get a Lumos API key

In your Lumos settings → API Tokens, generate an API key. This is what
lets the script create integrations in your Lumos account.

## Step 5 — Run the onboarding script

Follow the instructions in [`README.md`](./README.md) to install and run
`orchestrate.py`. You'll need:

- Your **Lumos Customer Integrator Role ARN** from Step 1.
- Your **Service Role External ID** from Step 1.
- The **StackSet name** you chose in Step 3.
- The **Lumos API key** from Step 4.
- Your own AWS login, with access to the accounts you're onboarding.

The script finds every account that has the role deployed and connects it to
Lumos automatically. Accounts you didn't target in Step 3 are skipped.

---

## Appendix A — CloudFormation template

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: Lumos NHI cross-account read role

Parameters:
  CustomerIntegratorRoleArn:
    Type: String
    Description: "Lumos Customer Integrator Role ARN from the connector setup page (AWS_SETUP.md Step 1)."
  ServiceRoleExternalId:
    Type: String
    Description: "Service Role External ID from the Lumos connector setup page (AWS_SETUP.md Step 1)."

Resources:
  LumosNhiCrossAccountRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: LumosNhiCrossAccountRole
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              AWS: {"Ref": "CustomerIntegratorRoleArn"}
            Action: sts:AssumeRole
            Condition:
              StringEquals:
                sts:ExternalId: {"Ref": "ServiceRoleExternalId"}
      Policies:
        - PolicyName: LumosNhiReadAccess
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              # Always required, regardless of which fetch_* toggles are enabled.
              - Sid: AlwaysRequired
                Effect: Allow
                Action:
                  - sts:GetCallerIdentity
                  - account:ListRegions
                Resource: "*"
              # settings.fetch_iam_users
              - Sid: FetchIamUsers
                Effect: Allow
                Action:
                  - iam:ListUsers
                  - iam:GetUser
                  - iam:ListUserPolicies
                  - iam:GetUserPolicy
                  - iam:ListAttachedUserPolicies
                  - iam:ListGroupsForUser
                  - iam:ListAccessKeys
                  - iam:GetAccessKeyLastUsed
                  - iam:GetLoginProfile
                  - iam:ListMFADevices
                  - iam:GetPolicy
                  - iam:GetPolicyVersion
                Resource: "*"
              # settings.fetch_federated_principals
              - Sid: FetchFederatedPrincipals
                Effect: Allow
                Action:
                  - iam:ListOpenIDConnectProviders
                  - iam:GetOpenIDConnectProvider
                  - iam:ListSAMLProviders
                  - iam:GetSAMLProvider
                  - iam:ListRoles
                Resource: "*"
              # settings.fetch_iam_roles
              - Sid: FetchIamRoleEntitlements
                Effect: Allow
                Action:
                  - iam:ListRoles
                  - iam:GetRole
                  - iam:ListRolePolicies
                  - iam:GetRolePolicy
                  - iam:ListAttachedRolePolicies
                  - iam:GetPolicy
                  - iam:GetPolicyVersion
                Resource: "*"
              # settings.fetch_iam_groups
              - Sid: FetchIamGroupEntitlements
                Effect: Allow
                Action:
                  - iam:ListGroups
                  - iam:GetGroup
                  - iam:ListGroupPolicies
                  - iam:GetGroupPolicy
                  - iam:ListAttachedGroupPolicies
                  - iam:GetPolicy
                  - iam:GetPolicyVersion
                Resource: "*"
              # settings.fetch_iam_policies
              - Sid: FetchIamPolicyTerminalResources
                Effect: Allow
                Action:
                  - iam:ListPolicies
                  - iam:GetPolicy
                  - iam:ListPolicyVersions
                  - iam:GetPolicyVersion
                Resource: "*"
              # settings.fetch_lambda
              - Sid: FetchLambdaFunctions
                Effect: Allow
                Action:
                  - lambda:ListFunctions
                  - lambda:GetFunctionConfiguration
                  - lambda:ListFunctionUrlConfigs
                  - lambda:GetPolicy
                Resource: "*"
              # settings.fetch_ecs
              - Sid: FetchEcsTasksAndServices
                Effect: Allow
                Action:
                  - ecs:List*
                  - ecs:Describe*
                Resource: "*"
              # settings.fetch_ec2
              - Sid: FetchEc2InstanceProfiles
                Effect: Allow
                Action:
                  - ec2:DescribeInstances
                  - ec2:DescribeSecurityGroups
                  - autoscaling:Describe*
                  - iam:ListInstanceProfiles
                Resource: "*"
              # settings.fetch_eks
              - Sid: FetchEksWorkloads
                Effect: Allow
                Action:
                  - eks:List*
                  - eks:Describe*
                  - iam:ListRoles
                Resource: "*"
              # settings.fetch_glue
              - Sid: FetchGlueJobs
                Effect: Allow
                Action:
                  - glue:GetJobs
                  - glue:GetCrawlers
                  - glue:GetJobRuns
                Resource: "*"
              # settings.fetch_step_functions
              - Sid: FetchStepFunctions
                Effect: Allow
                Action:
                  - states:List*
                  - states:Describe*
                Resource: "*"
              # settings.fetch_firehose
              - Sid: FetchKinesisFirehoseStreams
                Effect: Allow
                Action:
                  - firehose:List*
                  - firehose:Describe*
                Resource: "*"
              # settings.fetch_codepipeline
              - Sid: FetchCodePipelinePipelines
                Effect: Allow
                Action:
                  - codepipeline:List*
                  - codepipeline:Get*
                Resource: "*"
              # settings.fetch_sagemaker
              - Sid: FetchSageMakerJobs
                Effect: Allow
                Action:
                  - sagemaker:List*
                  - sagemaker:Describe*
                Resource: "*"
              # settings.fetch_eventbridge
              - Sid: FetchEventBridgeRulesAndPipes
                Effect: Allow
                Action:
                  - events:ListRules
                  - events:ListTargetsByRule
                  - pipes:ListPipes
                  - pipes:DescribePipe
                Resource: "*"
              # settings.fetch_kafkaconnect
              - Sid: FetchMskConnectConnectors
                Effect: Allow
                Action:
                  - kafkaconnect:ListConnectors
                Resource: "*"
              # settings.fetch_codebuild
              - Sid: FetchCodeBuildProjects
                Effect: Allow
                Action:
                  - codebuild:List*
                  - codebuild:BatchGet*
                Resource: "*"
              # settings.fetch_batch
              - Sid: FetchBatchJobDefinitions
                Effect: Allow
                Action:
                  - batch:Describe*
                  - batch:List*
                Resource: "*"
              # settings.fetch_apprunner
              - Sid: FetchAppRunnerServices
                Effect: Allow
                Action:
                  - apprunner:List*
                  - apprunner:Describe*
                Resource: "*"
              # settings.fetch_bedrock_agent
              - Sid: FetchBedrockAgents
                Effect: Allow
                Action:
                  - bedrock:List*
                  - bedrock:Get*
                  - bedrock-agentcore:ListAgentRuntimes
                  - bedrock-agentcore:GetAgentRuntime
                Resource: "*"
              # settings.fetch_iot
              - Sid: FetchIotRoleAliases
                Effect: Allow
                Action:
                  - iot:List*
                  - iot:Describe*
                Resource: "*"
              # settings.fetch_roles_anywhere
              - Sid: FetchIamRolesAnywhereProfiles
                Effect: Allow
                Action:
                  - rolesanywhere:ListProfiles
                Resource: "*"
              # settings.fetch_secrets_manager
              - Sid: FetchSecretsManagerSecrets
                Effect: Allow
                Action:
                  - secretsmanager:ListSecrets
                Resource: "*"
              # settings.fetch_ssm
              - Sid: FetchSsmSecureStringParameters
                Effect: Allow
                Action:
                  - ssm:DescribeParameters
                Resource: "*"
              # settings.fetch_last_activity
              - Sid: FetchNhaLastActivity
                Effect: Allow
                Action:
                  - cloudwatch:GetMetricData
                  - cloudwatch:ListMetrics
                Resource: "*"
              # settings.fetch_batch_last_activity_cloudtrail / settings.fetch_ecs_standalone_cloudtrail
              - Sid: FetchLastActivityViaCloudTrail
                Effect: Allow
                Action:
                  - cloudtrail:LookupEvents
                Resource: "*"
              # Not gated by a settings toggle today — granted ahead of the NHI Agent
              # feature that will consume them.
              - Sid: NHIAgentIamAuthorizationGraph
                Effect: Allow
                Action:
                  - iam:GetAccountAuthorizationDetails
                Resource: "*"
              - Sid: NHIAgentAccessAnalyzerFindings
                Effect: Allow
                Action:
                  - access-analyzer:ListAnalyzers
                  - access-analyzer:ListFindings
                  - access-analyzer:GetFinding
                Resource: "*"
              - Sid: NHIAgentGuardDutyFindings
                Effect: Allow
                Action:
                  - guardduty:ListDetectors
                  - guardduty:ListFindings
                  - guardduty:GetFindings
                Resource: "*"
              - Sid: NHIAgentBucketExposure
                Effect: Allow
                Action:
                  - s3:ListAllMyBuckets
                  - s3:GetBucketLocation
                  - s3:GetBucketPolicy
                  - s3:GetBucketPolicyStatus
                  - s3:GetBucketAcl
                  - s3:GetBucketPublicAccessBlock
                  - s3:GetAccountPublicAccessBlock
                Resource: "*"
              - Sid: NHIAgentKeyPolicyExposure
                Effect: Allow
                Action:
                  - kms:ListKeys
                  - kms:DescribeKey
                  - kms:GetKeyPolicy
                Resource: "*"
              - Sid: NHIAgentIdentityCenter
                Effect: Allow
                Action:
                  - sso:List*
                  - sso:Describe*
                  - sso:Get*
                  - identitystore:List*
                  - identitystore:Describe*
                  - organizations:ListAccounts
                  - organizations:DescribeOrganization
                Resource: "*"
              # Defense in depth: even though every action above is read-only/metadata,
              # explicitly deny the data-plane read APIs that could expose secret values.
              - Sid: DenyDataPlaneReads
                Effect: Deny
                Action:
                  - s3:GetObject
                  - s3:GetObjectVersion
                  - s3:GetObjectAttributes
                  - s3:ListBucket
                  - s3:ListBucketVersions
                  - secretsmanager:GetSecretValue
                  - ssm:GetParameter
                  - ssm:GetParameters
                  - ssm:GetParametersByPath
                  - kms:Decrypt
                  - dynamodb:GetItem
                  - dynamodb:Query
                  - dynamodb:Scan
                  - logs:GetLogEvents
                  - logs:FilterLogEvents
                Resource: "*"

Outputs:
  RoleArn:
    Value:
      Fn::GetAtt: [LumosNhiCrossAccountRole, Arn]
```
