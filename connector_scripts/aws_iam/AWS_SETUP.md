# AWS IAM Multi-Account Setup

This guide walks you through connecting Lumos to every AWS account in your
Organization via the AWS IAM connector. You'll do two things:

1. Deploy a cross-account IAM role to each account you want Lumos to manage.
2. Run a script that finds those accounts and connects them to Lumos.

Each connected account becomes a separate Lumos integration — Lumos manages the
local IAM users, groups, and policies within that account independently.

---

## Step 1 — Get your Lumos Service Account ARN and Service Role External ID

Open the AWS IAM connector setup page in the Lumos app and copy:
- **Lumos Service Account ARN** — you'll need this in Step 3. You can find this in the **Create the role (IAM -> Roles)** step in the last bullet point.
- **Service Role External ID** — you'll need this in Steps 3 and 5.

## Step 2 — Enable trusted access for CloudFormation StackSets

This is a one-time setting for your Organization:

1. Open the **AWS Organizations console** from your **management account**.
2. In the left sidebar, click **Services**.
3. Find **CloudFormation StackSets** in the list.
4. Click **Enable trusted access**.

## Step 3 — Deploy the cross-account role to your accounts

1. Download the `lumos-iam-role.yaml` template (see **Appendix A**).
2. In the **CloudFormation console**, go to **StackSets → Create StackSet**.
3. **Permissions**: choose **Service-managed permissions**.
4. **Specify template**: choose **Upload a template file** and upload
   `lumos-iam-role.yaml`.
5. Give the StackSet a name, for example `lumos-iam-cross-account-role`.
   You'll need this name in Step 5.
6. **Parameters**: enter your **Lumos Service Account ARN** and **Service Role External ID** from Step 1 when prompted.
7. On the **Configure StackSet options** screen, check the box acknowledging
   that CloudFormation may create IAM resources with custom names.
8. **Deployment targets**: choose the accounts or organizational units you
   want Lumos to manage. Only accounts you select here will be connected.
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
Description: Lumos AWS IAM cross-account role

Parameters:
  LumosServiceAccountArn:
    Type: String
    Description: "Lumos Service Account ARN from the connector setup page (AWS_SETUP.md Step 1)."
  ServiceRoleExternalId:
    Type: String
    Description: "Service Role External ID from the Lumos connector setup page (AWS_SETUP.md Step 1)."

Resources:
  LumosAwsIamCrossAccountRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: LumosAwsIamCrossAccountRole
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              AWS: {"Ref": "LumosServiceAccountArn"}
            Action: sts:AssumeRole
            Condition:
              StringEquals:
                sts:ExternalId: {"Ref": "ServiceRoleExternalId"}
      Policies:
        - PolicyName: LumosAwsIamAccess
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Sid: AllowAccessToIdentityCenter
                Effect: Allow
                Action:
                  - iam:ListUsers
                  - iam:GetUser
                  - iam:ListRoles
                  - iam:GetRole
                  - iam:ListGroups
                  - iam:ListGroupsForUser
                  - iam:SimulatePrincipalPolicy
                  - iam:ListPolicies
                  - iam:ListAttachedUserPolicies
                  - iam:ListAttachedRolePolicies
                  - iam:ListAttachedGroupPolicies
                  - iam:AttachUserPolicy
                  - iam:DetachUserPolicy
                  - iam:AddUserToGroup
                  - iam:RemoveUserFromGroup
                  - iam:PutUserPolicy
                  - iam:DeleteUserPolicy
                  - iam:CreateUser
                  - iam:CreateLoginProfile
                  - iam:DeleteUser
                  - iam:GetUserPolicy
                  - iam:GetLoginProfile
                  - iam:DeleteLoginProfile
                  - iam:ListAccessKeys
                  - iam:DeleteAccessKey
                  - iam:ListSigningCertificates
                  - iam:DeleteSigningCertificate
                  - iam:ListSSHPublicKeys
                  - iam:DeleteSSHPublicKey
                  - iam:ListServiceSpecificCredentials
                  - iam:DeleteServiceSpecificCredential
                  - iam:ListMFADevices
                  - iam:DeactivateMFADevice
                  - iam:ListVirtualMFADevices
                  - iam:DeleteVirtualMFADevice
                  - iam:ListUserPolicies
                  - sts:GetCallerIdentity
                  - cloudtrail:LookupEvents
                Resource: "*"
              - Sid: AccessToSSOProvisionedRoles
                Effect: Allow
                Action:
                  - iam:AttachRolePolicy
                  - iam:DeleteRolePolicy
                  - iam:DetachRolePolicy
                  - iam:ListAttachedRolePolicies
                  - iam:GetRole
                  - iam:CreateRole
                  - iam:DeleteRole
                  - iam:PutRolePolicy
                  - iam:UpdateRole
                  - iam:ListRolePolicies
                  - iam:UpdateRoleDescription
                Resource: "arn:aws:iam::*:role/aws-reserved/sso.amazonaws.com/*"
              - Sid: AccessToSCIMProvider
                Effect: Allow
                Action:
                  - iam:GetSAMLProvider
                Resource: "arn:aws:iam::*:saml-provider/AWSSSO_*_DO_NOT_DELETE"

Outputs:
  RoleArn:
    Value:
      Fn::GetAtt: [LumosAwsIamCrossAccountRole, Arn]
```
