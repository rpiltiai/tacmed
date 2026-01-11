
# Configuration
$outputsFile = "infrastructure_outputs.json"
$outputs = Get-Content $outputsFile | ConvertFrom-Json
$region = "eu-central-1"
$accountId = $outputs.AccountId
$kbBucket = $outputs.KbBucket
$kbName = "TacMed_KB"
$roleName = "TacMed_KB_Role"

Write-Host "Creating Bedrock KB: $kbName in $region..."

# 1. IAM Role for KB (Already have kb-trust-policy.json and kb-policy.json)
# Check if role exists
$roleArn = ""
try {
    $roleArn = aws iam get-role --role-name $roleName --query 'Role.Arn' --output text 2>$null
}
catch {}

if (-not $roleArn) {
    # Ensure trust policy exists (Trusting bedrock.amazonaws.com)
    $trustPolicy = @{
        Version   = "2012-10-17"
        Statement = @(@{
                Effect    = "Allow"
                Principal = @{ Service = "bedrock.amazonaws.com" }
                Action    = "sts:AssumeRole"
                Condition = @{
                    StringEquals = @{ "aws:SourceAccount" = $accountId }
                    ArnLike      = @{ "aws:SourceArn" = "arn:aws:bedrock:$region`:$accountId`:knowledge-base/*" }
                }
            })
    } | ConvertTo-Json -Depth 5
    Set-Content -Path "kb-trust-policy.json" -Value $trustPolicy -Encoding utf8

    $roleArn = aws iam create-role --role-name $roleName --assume-role-policy-document file://kb-trust-policy.json --query 'Role.Arn' --output text
    Write-Host "KB Role created: $roleArn"
    Start-Sleep -Seconds 10
}

# Attach permissions
# We'll use the existing kb-policy.json (assuming it covers S3 and Bedrock models)
aws iam put-role-policy --role-name $roleName --policy-name BedrockKBPolicy --policy-document file://kb-policy.json

# 2. Create Knowledge Base
# We'll use the quick create method (Titan embedding, default vector store)
$kbId = aws bedrock-agent create-knowledge-base `
    --name $kbName `
    --role-arn $roleArn `
    --knowledge-base-configuration '{"type": "VECTOR", "vectorKnowledgeBaseConfiguration": {"embeddingModelArn": "arn:aws:bedrock:' + $region + '::foundation-model/amazon.titan-embed-text-v2:0"}}' `
    --storage-configuration '{"type": "QUICK_CREATE", "quickCreateConfiguration": {"storageType": "OPENSEARCH_SERVERLESS"}}' `
    --region $region `
    --query 'knowledgeBase.knowledgeBaseId' --output text

if ($LASTEXITCODE -ne 0 -or -not $kbId) {
    Write-Error "Failed to create Knowledge Base."
    exit 1
}

Write-Host "Created KB: $kbId. Waiting for setup..."
Start-Sleep -Seconds 30

# 3. Create Data Source (S3)
$dsId = aws bedrock-agent create-data-source `
    --knowledge-base-id $kbId `
    --name "TacMed_S3_Source" `
    --data-source-configuration '{"type": "S3", "s3Configuration": {"bucketArn": "arn:aws:s3:::' + $kbBucket + '"}}' `
    --region $region `
    --query 'dataSource.dataSourceId' --output text

Write-Host "Created Data Source: $dsId"

# 4. Start Ingestion Job
$jobId = aws bedrock-agent start-ingestion-job `
    --knowledge-base-id $kbId `
    --data-source-id $dsId `
    --region $region `
    --query 'ingestionJob.ingestionJobId' --output text

Write-Host "Ingestion Job Started: $jobId"

# Update outputs
$outputs | Add-Member -MemberType NoteProperty -Name KnowledgeBaseId -Value $kbId -Force
$outputs | ConvertTo-Json | Set-Content -Path $outputsFile -Encoding utf8

Write-Host "Setup Complete. KnowledgeBaseId saved."
