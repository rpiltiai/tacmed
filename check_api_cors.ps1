
# Get Config
$json = Get-Content "infrastructure_outputs.json" | ConvertFrom-Json
$apiEndpoint = $json.ApiEndpoint
$apiId = $apiEndpoint.Split('.')[0].Split('//')[1]

Write-Host "Checking API: $apiId"
aws apigatewayv2 get-api --api-id $apiId.Trim()
