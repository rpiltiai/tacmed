
# Configuration
$collectionName = "tacmed-kb-4850"
$region = "eu-central-1"
$accountId = "168705873426"
$kbRoleArn = "arn:aws:iam::168705873426:role/TacMed_KB_Role"
$userArn = "arn:aws:iam::168705873426:user/roman-dev"

Write-Host "Setting up OpenSearch Serverless for $collectionName..."

# Function to write JSON without BOM
function Write-JsonWithoutBOM($path, $content) {
    $utf8NoBOM = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($path, $content, $utf8NoBOM)
}

# 1. Encryption Policy
$encryptionPolicyName = "$collectionName-enc"
$encryptionPolicy = @{
    Rules       = @(@{
            ResourceType = "collection"
            Resource     = @("collection/$collectionName")
        })
    AWSOwnedKey = $true
} | ConvertTo-Json -Depth 5
Write-JsonWithoutBOM "oss-encryption-policy.json" $encryptionPolicy

try {
    aws opensearchserverless create-security-policy `
        --name $encryptionPolicyName `
        --type encryption `
        --policy "file://oss-encryption-policy.json" `
        --region $region
}
catch {
    Write-Host "Encryption policy might already exist."
}

# 2. Network Policy
$networkPolicyName = "$collectionName-net"
$networkPolicy = @(@{
        Rules           = @(
            @{ ResourceType = "collection"; Resource = @("collection/$collectionName") },
            @{ ResourceType = "dashboard"; Resource = @("collection/$collectionName") }
        )
        AllowFromPublic = $true
    }) | ConvertTo-Json -Depth 5
Write-JsonWithoutBOM "oss-network-policy.json" $networkPolicy

try {
    aws opensearchserverless create-security-policy `
        --name $networkPolicyName `
        --type network `
        --policy "file://oss-network-policy.json" `
        --region $region
}
catch {
    Write-Host "Network policy might already exist."
}

# 3. Data Access Policy
$accessPolicyName = "$collectionName-access"
$accessPolicy = @(@{
        Rules     = @(
            @{
                ResourceType = "collection"
                Resource     = @("collection/$collectionName")
                Permission   = @(
                    "aoss:CreateCollectionItems",
                    "aoss:DeleteCollectionItems",
                    "aoss:UpdateCollectionItems",
                    "aoss:DescribeCollectionItems"
                )
            },
            @{
                ResourceType = "index"
                Resource     = @("index/$collectionName/*")
                Permission   = @(
                    "aoss:CreateIndex",
                    "aoss:DeleteIndex",
                    "aoss:UpdateIndex",
                    "aoss:DescribeIndex",
                    "aoss:ReadDocument",
                    "aoss:WriteDocument"
                )
            }
        )
        Principal = @($kbRoleArn, $userArn)
    }) | ConvertTo-Json -Depth 5
Write-JsonWithoutBOM "oss-access-policy.json" $accessPolicy

try {
    aws opensearchserverless create-access-policy `
        --name $accessPolicyName `
        --type data `
        --policy "file://oss-access-policy.json" `
        --region $region
}
catch {
    Write-Host "Access policy might already exist."
}

# 4. Create Collection
Write-Host "Creating collection $collectionName..."
# Check if exists first
$existing = aws opensearchserverless list-collections --region $region | ConvertFrom-Json
$collection = $existing.collectionSummaries | Where-Object { $_.name -eq $collectionName }

if ($null -eq $collection) {
    $createOutput = aws opensearchserverless create-collection `
        --name $collectionName `
        --type VECTORSEARCH `
        --region $region | ConvertFrom-Json
    $collectionId = $createOutput.createCollectionDetail.id
}
else {
    $collectionId = $collection.id
    Write-Host "Using existing collection: $collectionId"
}

Write-Host "Collection ID: $collectionId. Waiting for ACTIVE status..."

while ($true) {
    $status = aws opensearchserverless batch-get-collection --ids $collectionId --region $region | ConvertFrom-Json
    $currentStatus = $status.collectionDetails[0].status
    Write-Host "Current Status: $currentStatus"
    if ($currentStatus -eq "ACTIVE") { break }
    if ($currentStatus -eq "FAILED") { Write-Error "Collection creation failed."; exit 1 }
    Start-Sleep -Seconds 10
}

Write-Host "Collection is ACTIVE."
$collectionArn = $status.collectionDetails[0].arn
Write-Host "Collection ARN: $collectionArn"

# Update infrastructure_outputs.json
$outputs = Get-Content "infrastructure_outputs.json" | ConvertFrom-Json
if (-not $outputs.CollectionArn) {
    $outputs | Add-Member -MemberType NoteProperty -Name CollectionArn -Value $collectionArn -Force
}
else {
    $outputs.CollectionArn = $collectionArn
}
$outputs | ConvertTo-Json | Set-Content -Path "infrastructure_outputs.json"

Write-Host "OpenSearch Serverless setup complete."
