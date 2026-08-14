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
9. **Specify regions**: pick one region, for example `us-east-1`.
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
              - Sid: IdentityCenterAndOrg
                Effect: Allow
                Action:
                  - sso:ListInstances
                  - sso:DescribeInstance
                  - sso:ListPermissionSets
                  - sso:DescribePermissionSet
                  - sso:ListManagedPoliciesInPermissionSet
                  - sso:GetInlinePolicyForPermissionSet
                  - sso:ListCustomerManagedPolicyReferencesInPermissionSet
                  - sso:GetPermissionsBoundaryForPermissionSet
                  - sso:ListAccountAssignments
                  - sso:ListAccountAssignmentsForPrincipal
                  - sso:ListAccountsForProvisionedPermissionSet
                  - sso:ListApplications
                  - sso:DescribeApplication
                  - sso:ListApplicationAssignments
                  - sso:ListApplicationGrants
                  - sso:ListApplicationAccessScopes
                  - sso:ListApplicationAuthenticationMethods
                  - sso:GetApplicationAuthenticationMethod
                  - sso:GetApplicationGrant
                  - sso:ListTrustedTokenIssuers
                  - sso:DescribeTrustedTokenIssuer
                  - sso:DescribeInstanceAccessControlAttributeConfiguration
                  - identitystore:ListUsers
                  - identitystore:DescribeUser
                  - identitystore:ListGroups
                  - identitystore:DescribeGroup
                  - identitystore:ListGroupMemberships
                  - organizations:ListAccounts
                  - organizations:DescribeOrganization
                  - kms:ListKeys
                  - sts:GetCallerIdentity
                Resource: "*"
              - Sid: IamReadAccess
                Effect: Allow
                Action:
                  - iam:ListRoles
                  - iam:GetRole
                  - iam:ListUsers
                  - iam:GetLoginProfile
                  - iam:ListMFADevices
                  - iam:ListInstanceProfiles
                  - iam:ListAccessKeys
                  - iam:GetAccessKeyLastUsed
                  - iam:ListAttachedRolePolicies
                  - iam:GetPolicy
                  - iam:GetPolicyVersion
                  - iam:ListRolePolicies
                  - iam:GetRolePolicy
                  - iam:ListAttachedUserPolicies
                  - iam:ListUserPolicies
                  - iam:GetUserPolicy
                  - iam:ListOpenIDConnectProviders
                  - iam:GetOpenIDConnectProvider
                  - iam:ListSAMLProviders
                  - iam:GetSAMLProvider
                Resource: "*"
              - Sid: WorkloadResourceRead
                Effect: Allow
                Action:
                  - lambda:ListFunctions
                  - ecs:ListClusters
                  - ecs:ListServices
                  - ecs:DescribeServices
                  - ecs:DescribeTaskDefinition
                  - ecs:ListTasks
                  - ecs:DescribeTasks
                  - glue:GetJobs
                  - glue:GetCrawlers
                  - states:ListStateMachines
                  - states:DescribeStateMachine
                  - firehose:ListDeliveryStreams
                  - firehose:DescribeDeliveryStream
                  - codepipeline:ListPipelines
                  - codepipeline:GetPipeline
                  - sagemaker:ListNotebookInstances
                  - sagemaker:DescribeNotebookInstance
                  - sagemaker:ListEndpoints
                  - sagemaker:DescribeEndpoint
                  - sagemaker:DescribeEndpointConfig
                  - events:ListRules
                  - events:ListTargetsByRule
                  - pipes:ListPipes
                  - pipes:DescribePipe
                  - kafkaconnect:ListConnectors
                  - codebuild:ListProjects
                  - codebuild:BatchGetProjects
                  - batch:DescribeJobDefinitions
                  - apprunner:ListServices
                  - apprunner:DescribeService
                  - bedrock:ListFoundationModels
                  - bedrock:ListAgents
                  - bedrock:GetAgent
                  - iot:ListRoleAliases
                  - iot:DescribeRoleAlias
                  - rolesanywhere:ListProfiles
                  - eks:ListClusters
                  - eks:ListNodegroups
                  - eks:DescribeNodegroup
                  - eks:ListPodIdentityAssociations
                  - eks:DescribePodIdentityAssociation
                  - eks:ListFargateProfiles
                  - eks:DescribeFargateProfile
                  - secretsmanager:ListSecrets
                  - ssm:DescribeParameters
                Resource: "*"

Outputs:
  RoleArn:
    Value:
      Fn::GetAtt: [LumosNhiCrossAccountRole, Arn]
```
