$ErrorActionPreference = "Stop"

# Configuration
if (Test-Path "infrastructure_outputs.json") {
    $outputs = Get-Content "infrastructure_outputs.json" | ConvertFrom-Json
    $webBucket = $outputs.WebBucket
}
else {
    Write-Error "Infrastructure outputs not found. Run setup.ps1 first."
    exit 1
}

$region = aws configure get region
if (-not $region) { $region = "eu-central-1" }
$originDomain = "${webBucket}.s3-website.${region}.amazonaws.com"

Write-Host "Creating CloudFront Distribution for Origin: $originDomain"

# Create config JSON
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$distConfig = @{
    CallerReference      = "tacmed-https-$timestamp"
    Aliases              = @{ Quantity = 0 }
    DefaultRootObject    = "index.html"
    Origins              = @{
        Quantity = 1
        Items    = @(
            @{
                Id                 = "S3-Website"
                DomainName         = $originDomain
                CustomOriginConfig = @{
                    HTTPPort               = 80
                    HTTPSPort              = 443
                    OriginProtocolPolicy   = "http-only"
                    OriginSslProtocols     = @{ Quantity = 1; Items = @("TLSv1.2") }
                    OriginReadTimeout      = 30
                    OriginKeepaliveTimeout = 5
                }
            }
        )
    }
    DefaultCacheBehavior = @{
        TargetOriginId       = "S3-Website"
        ViewerProtocolPolicy = "redirect-to-https"
        AllowedMethods       = @{
            Quantity      = 2
            Items         = @("HEAD", "GET")
            CachedMethods = @{ Quantity = 2; Items = @("HEAD", "GET") }
        }
        ForwardedValues      = @{
            QueryString = $false
            Cookies     = @{ Forward = "none" }
            Headers     = @{ Quantity = 0 }
        }
        TrustedSigners       = @{ Enabled = $false; Quantity = 0 }
        MinTTL               = 0
        DefaultTTL           = 3600
        MaxTTL               = 86400
    }
    CacheBehaviors       = @{ Quantity = 0 }
    Comment              = "TacMed HTTPS Proxy ($webBucket)"
    Enabled              = $true
} | ConvertTo-Json -Depth 10

Set-Content -Path "cloudfront_config.json" -Value $distConfig

# Create Distribution
Write-Host "Submitting CloudFront request..."
$dist = aws cloudfront create-distribution --distribution-config file://cloudfront_config.json --output json | ConvertFrom-Json

$distId = $dist.Distribution.Id
$domainName = $dist.Distribution.DomainName

Write-Host "CloudFront Distribution Created!"
Write-Host "ID: $distId"
Write-Host "Domain: https://$domainName"
Write-Host "NOTE: It may take 15 minutes for the domain to become active."

# Cleanup
Remove-Item cloudfront_config.json

# Update outputs
$outputs | Add-Member -MemberType NoteProperty -Name "CloudFrontDomain" -Value "https://$domainName" -Force
$outputs | Add-Member -MemberType NoteProperty -Name "CloudFrontId" -Value $distId -Force
$outputs | ConvertTo-Json | Set-Content "infrastructure_outputs.json"
