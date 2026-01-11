
$name = "tacmed-rag-v2"
$region = "eu-central-1"
$accountId = "168705873426"
$role = "arn:aws:iam::$accountId:role/TacMed_KB_Role"
$user = "arn:aws:iam::$accountId:user/roman-dev"

Write-Host "Creating policies and collection for $name..."

# 1. Encryption
$enc = @{ Rules = @(@{ ResourceType = "collection"; Resource = @("collection/$name") }); AWSOwnedKey = $true } | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText("$pwd/enc.json", $enc)
aws opensearchserverless create-security-policy --name "$name-enc" --type encryption --policy file://enc.json --region $region

# 2. Network
$net = @(@{ Rules = @(@{ ResourceType = "collection"; Resource = @("collection/$name") }, @{ ResourceType = "dashboard"; Resource = @("collection/$name") }); AllowFromPublic = $true }) | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText("$pwd/net.json", $net)
aws opensearchserverless create-security-policy --name "$name-net" --type network --policy file://net.json --region $region

# 3. Access
$acc = @(@{ Rules = @(@{ ResourceType = "collection"; Resource = @("collection/$name"); Permission = @("aoss:*") }, @{ ResourceType = "index"; Resource = @("index/$name/*"); Permission = @("aoss:*") }); Principal = @($role, $user) }) | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText("$pwd/acc.json", $acc)
aws opensearchserverless create-access-policy --name "$name-access" --type data --policy file://acc.json --region $region

# 4. Collection
aws opensearchserverless create-collection --name $name --type VECTORSEARCH --region $region
