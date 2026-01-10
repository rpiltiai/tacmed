
# Configuration
$configFile = "setup_config.txt"
if (Test-Path $configFile) {
    $suffix = (Get-Content $configFile | Select-Object -First 1)
}
else {
    $suffix = Get-Random -Minimum 1000 -Maximum 9999
    Set-Content -Path $configFile -Value $suffix
}

$s3WebBucket = "tacmed-web-$suffix"
$s3KbBucket = "tacmed-kb-$suffix"
$region = aws configure get region
if (-not $region) { $region = "us-east-1" }

Write-Host "Setting up TCCC Tutor Infrastructure in $region with suffix $suffix..."

# 1. Verify AWS CLI
aws --version
if ($LASTEXITCODE -ne 0) { Write-Error "AWS CLI not found."; exit 1 }

# Get Account ID
$accountId = aws sts get-caller-identity --query 'Account' --output text
Write-Host "AWS Account ID: $accountId"

# 2. S3 Buckets
Write-Host "Creating S3 Buckets..."
# Check if exists (simple check: try to list, if fails, create)
if (!(aws s3 ls "s3://$s3WebBucket" 2>$null)) {
    aws s3 mb "s3://$s3WebBucket" --region $region
}
else {
    Write-Host "Bucket $s3WebBucket already exists."
}

if (!(aws s3 ls "s3://$s3KbBucket" 2>$null)) {
    aws s3 mb "s3://$s3KbBucket" --region $region
}
else {
    Write-Host "Bucket $s3KbBucket already exists."
}

# Enable static hosting for web bucket
aws s3 website "s3://$s3WebBucket" --index-document index.html --error-document index.html

# 3. DynamoDB Tables
Write-Host "Creating DynamoDB Tables..."
# TacMed_Users
aws dynamodb describe-table --table-name TacMed_Users --region $region >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    aws dynamodb create-table `
        --table-name TacMed_Users `
        --attribute-definitions AttributeName=UserId, AttributeType=S AttributeName=TotalScore, AttributeType=N `
        --key-schema AttributeName=UserId, KeyType=HASH `
        --global-secondary-indexes 'IndexName=TotalScoreIndex,KeySchema=[{AttributeName=TotalScore,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}' `
        --provisioned-throughput ReadCapacityUnits=5, WriteCapacityUnits=5 `
        --region $region | Out-Null
}
else {
    Write-Host "Table TacMed_Users already exists."
}

# TacMed_History
aws dynamodb describe-table --table-name TacMed_History --region $region >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    aws dynamodb create-table `
        --table-name TacMed_History `
        --attribute-definitions AttributeName=UserId, AttributeType=S AttributeName=Timestamp, AttributeType=S `
        --key-schema AttributeName=UserId, KeyType=HASH AttributeName=Timestamp, KeyType=RANGE `
        --provisioned-throughput ReadCapacityUnits=5, WriteCapacityUnits=5 `
        --region $region | Out-Null
}
else {
    Write-Host "Table TacMed_History already exists."
}

# 4. Cognito
Write-Host "Creating Cognito User Pool..."
# Check if exists by name? Hard to filter by name reliably without jq/pagination.
# We will create if config is missing, BUT we probably should store PoolID in config too.
# For now, let's list and grep (Select-String).
$pools = aws cognito-idp list-user-pools --max-results 20 --output json | ConvertFrom-Json
$existingPool = $pools.UserPools | Where-Object { $_.Name -eq "TacMed_UserPool" }

if ($existingPool) {
    $poolId = $existingPool.Id
    Write-Host "Using existing User Pool: $poolId"
}
else {
    $poolId = aws cognito-idp create-user-pool --pool-name TacMed_UserPool --auto-verified-attributes email --query 'UserPool.Id' --output text
    Write-Host "Created User Pool: $poolId"
}

# App Client
$clients = aws cognito-idp list-user-pool-clients --user-pool-id $poolId --output json | ConvertFrom-Json
$existingClient = $clients.UserPoolClients | Where-Object { $_.ClientName -eq "TacMed_WebClient" }

if ($existingClient) {
    $clientId = $existingClient.ClientId
    Write-Host "Using existing App Client: $clientId"
}
else {
    $clientId = aws cognito-idp create-user-pool-client --user-pool-id $poolId --client-name TacMed_WebClient --explicit-auth-flows USER_PASSWORD_AUTH --query 'UserPoolClient.ClientId' --output text
    Write-Host "Created App Client: $clientId"
}

# 5. IAM Role for Lambda
Write-Host "Creating IAM Role..."
$roleName = "TacMed_Lambda_Role"
$trustPolicy = @{
    Version   = "2012-10-17"
    Statement = @(
        @{
            Effect    = "Allow"
            Principal = @{ Service = "lambda.amazonaws.com" }
            Action    = "sts:AssumeRole"
        }
    )
} | ConvertTo-Json -Depth 5
Set-Content -Path trust-policy.json -Value $trustPolicy

$roleArn = ""
try {
    $roleArn = aws iam get-role --role-name $roleName --query 'Role.Arn' --output text 2>$null
}
catch {}

if (-not $roleArn) {
    $roleArn = aws iam create-role --role-name $roleName --assume-role-policy-document file://trust-policy.json --query 'Role.Arn' --output text
    Write-Host "Role created: $roleArn"
    Write-Host "Waiting for propagation..."
    Start-Sleep -Seconds 15 # Wait for role creation before attach
}
else {
    Write-Host "Role exists: $roleArn"
}
Remove-Item trust-policy.json

# Attach policies
aws iam attach-role-policy --role-name $roleName --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole >$null 2>&1
# Inline policy
$inlinePolicy = @{
    Version   = "2012-10-17"
    Statement = @(
        @{
            Effect   = "Allow"
            Action   = @(
                "bedrock:RetrieveAndGenerate",
                "bedrock:InvokeModel",
                "transcribe:StartTranscriptionJob",
                "transcribe:GetTranscriptionJob",
                "dynamodb:*"
            )
            Resource = "*"
        }
    )
} | ConvertTo-Json -Depth 5
Set-Content -Path policy.json -Value $inlinePolicy
aws iam put-role-policy --role-name $roleName --policy-name TacMed_Permissions --policy-document file://policy.json
Remove-Item policy.json

# 6. Lambda Placeholder
Write-Host "Deploying Placeholder Lambda..."
$lambdaCode = "def lambda_handler(event, context): return {'statusCode': 200, 'body': 'Hello from TacMed'}"
Set-Content -Path lambda_function.py -Value $lambdaCode
Compress-Archive -Path lambda_function.py -DestinationPath function.zip -Force

# Check if exist
$funcExists = aws lambda get-function --function-name TacMed_Backend --query 'Configuration.FunctionArn' --output text 2>$null

if ($LASTEXITCODE -eq 0 -and $funcExists) {
    Write-Host "Function exists. Updating code..."
    aws lambda update-function-code --function-name TacMed_Backend --zip-file fileb://function.zip --region $region | Out-Null
}
else {
    Write-Host "Creating function..."
    # Retry loop for role propagation
    for ($i = 0; $i -lt 3; $i++) {
        try {
            aws lambda create-function `
                --function-name TacMed_Backend `
                --runtime python3.12 `
                --role $roleArn `
                --handler lambda_function.lambda_handler `
                --zip-file fileb://function.zip `
                --region $region `
                --timeout 60 | Out-Null
            break
        }
        catch {
            Write-Host "Failed to create function, retrying in 5s... ($($i+1)/3)"
            Start-Sleep -Seconds 5
        }
    }
}

Remove-Item lambda_function.py
Remove-Item function.zip

# 7. API Gateway
Write-Host "Creating API Gateway..."
$apiName = "TacMed_API"
# Check if exists
$apis = aws apigatewayv2 get-apis --output json | ConvertFrom-Json
$existingApi = $apis.Items | Where-Object { $_.Name -eq $apiName }

if ($existingApi) {
    $apiId = $existingApi.ApiId
    Write-Host "Using existing API: $apiId"
}
else {
    $apiId = aws apigatewayv2 create-api --name $apiName --protocol-type HTTP --cors-configuration AllowOrigins="*", AllowMethods="POST,GET,OPTIONS", AllowHeaders="*" --query 'ApiId' --output text
}

$lambdaArn = "arn:aws:lambda:${region}:${accountId}:function:TacMed_Backend"

# Integration
$integrations = aws apigatewayv2 get-integrations --api-id $apiId --output json | ConvertFrom-Json
$existingIntegration = $integrations.Items | Where-Object { $_.IntegrationUri -eq $lambdaArn }

if ($existingIntegration) {
    $integrationId = $existingIntegration.IntegrationId
}
else {
    $integrationId = aws apigatewayv2 create-integration --api-id $apiId --integration-type AWS_PROXY --integration-uri $lambdaArn --payload-format-version 2.0 --query 'IntegrationId' --output text
}

# Routes
foreach ($routeKey in @("POST /ask", "POST /quiz", "GET /leaderboard")) {
    $routes = aws apigatewayv2 get-routes --api-id $apiId --output json | ConvertFrom-Json
    if (-not ($routes.Items | Where-Object { $_.RouteKey -eq $routeKey })) {
        aws apigatewayv2 create-route --api-id $apiId --route-key $routeKey --target "integrations/$integrationId" | Out-Null
    }
}

# Permission
try {
    aws lambda add-permission --function-name TacMed_Backend --statement-id apigateway --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:${region}:${accountId}:${apiId}/*/*" 2>$null
}
catch {}

Write-Host "Setup Complete!"
Write-Host "Web Bucket: $s3WebBucket"
Write-Host "KB Bucket: $s3KbBucket"
Write-Host "User Pool ID: $poolId"
Write-Host "Client ID: $clientId"
Write-Host "API Endpoint: https://${apiId}.execute-api.${region}.amazonaws.com"

# Save outputs to file for later use
$outputs = @{
    WebBucket   = $s3WebBucket
    KbBucket    = $s3KbBucket
    UserPoolId  = $poolId
    ClientId    = $clientId
    ApiEndpoint = "https://${apiId}.execute-api.${region}.amazonaws.com"
} | ConvertTo-Json
Set-Content -Path "infrastructure_outputs.json" -Value $outputs
