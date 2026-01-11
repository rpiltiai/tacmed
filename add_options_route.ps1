
# Get Config
$json = Get-Content "infrastructure_outputs.json" | ConvertFrom-Json
$apiEndpoint = $json.ApiEndpoint
$apiId = $apiEndpoint.Split('.')[0].Split('//')[1]

# Get Integration
$integrations = aws apigatewayv2 get-integrations --api-id $apiId --output json | ConvertFrom-Json
$integrationId = $integrations.Items[0].IntegrationId

Write-Host "API: $apiId, Integration: $integrationId"

# Create Route
$routeKey = "OPTIONS /score"
Write-Host "Creating Route $routeKey..."

$routes = aws apigatewayv2 get-routes --api-id $apiId --output json | ConvertFrom-Json
if (-not ($routes.Items | Where-Object { $_.RouteKey -eq $routeKey })) {
    aws apigatewayv2 create-route --api-id $apiId --route-key $routeKey --target "integrations/$integrationId"
    Write-Host "Route created."
}
else {
    Write-Host "Route already exists."
}
