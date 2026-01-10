# setup_oidc.ps1
# This script sets up the AWS IAM OIDC provider and a role for GitHub Actions to deploy to your AWS account.

$repoName = "rpiltiai/tacmed" # Your GitHub repository
$roleName = "TacMed_GitHub_Deploy_Role"

# 1. Get AWS Account ID
$accountId = aws sts get-caller-identity --query "Account" --output text
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to get AWS Account ID. Make sure AWS CLI is configured."; exit 1 }

Write-Host "Setting up OIDC for repository: $repoName in account: $accountId"

# 2. Check/Create OIDC Provider
$providerArn = "arn:aws:iam::$accountId:oidc-provider/token.actions.githubusercontent.com"
Write-Host "Checking for OIDC Provider..."
$existingProvider = aws iam get-open-id-connect-provider --open-id-connect-provider-arn $providerArn 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating IAM OIDC Provider..."
    aws iam create-open-id-connect-provider `
        --url "https://token.actions.githubusercontent.com" `
        --client-id-list "sts.amazonaws.com" `
        --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" # Standard GitHub thumbprint
}
else {
    Write-Host "OIDC Provider already exists."
}

# 3. Create IAM Role with Trust Policy
Write-Host "Creating IAM Role: $roleName..."

$trustPolicy = @{
    Version   = "2012-10-17"
    Statement = @(
        @{
            Effect    = "Allow"
            Principal = @{
                Federated = $providerArn
            }
            Action    = "sts:AssumeRoleWithWebIdentity"
            Condition = @{
                StringLike = @{
                    'token.actions.githubusercontent.com:sub' = "repo:${repoName}:*"
                    'token.actions.githubusercontent.com:aud' = "sts.amazonaws.com"
                }
            }
        }
    )
} | ConvertTo-Json -Depth 5

Set-Content -Path "oidc-trust-policy.json" -Value $trustPolicy

$roleArn = ""
try {
    $roleArn = aws iam get-role --role-name $roleName --query "Role.Arn" --output text 2>$null
}
catch {}

if (-not $roleArn) {
    $roleArn = aws iam create-role --role-name $roleName --assume-role-policy-document file://oidc-trust-policy.json --query "Role.Arn" --output text
    Write-Host "Role created: $roleArn"
}
else {
    Write-Host "Role already exists: $roleArn"
    aws iam update-assume-role-policy --role-name $roleName --policy-document file://oidc-trust-policy.json
}

Remove-Item "oidc-trust-policy.json"

# 4. Attach Permissions Policy
Write-Host "Attaching permissions to role..."
$permissionsPolicy = @{
    Version   = "2012-10-17"
    Statement = @(
        @{
            Effect   = "Allow"
            Action   = @(
                "lambda:UpdateFunctionCode",
                "lambda:GetFunction"
            )
            Resource = "arn:aws:lambda:*:*:function:TacMed_Backend"
        }
    )
} | ConvertTo-Json -Depth 5

Set-Content -Path "oidc-permissions-policy.json" -Value $permissionsPolicy
aws iam put-role-policy --role-name $roleName --policy-name TacMed_GitHub_Deploy_Permissions --policy-document file://oidc-permissions-policy.json
Remove-Item "oidc-permissions-policy.json"

Write-Host "`nOIDC Setup Complete!"
Write-Host "Role ARN: $roleArn"
Write-Host "You can now update your GitHub Actions workflow to use this Role ARN."
