# PowerShell script to get your local IP address
# This is needed to connect your mobile device to the backend running on your computer

Write-Host "Finding your local IP address..." -ForegroundColor Cyan
Write-Host ""

# Get all network adapters with IPv4 addresses
# Exclude loopback, link-local, and virtual adapters (WSL, Hyper-V, etc.)
$adapters = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -notlike "127.*" -and 
    $_.IPAddress -notlike "169.254.*" -and
    $_.InterfaceAlias -notlike "*Loopback*" -and
    $_.InterfaceAlias -notlike "*vEthernet*" -and
    $_.InterfaceAlias -notlike "*WSL*" -and
    $_.InterfaceAlias -notlike "*Hyper-V*" -and
    $_.InterfaceAlias -notlike "*Virtual*"
} | Sort-Object InterfaceAlias

if ($adapters.Count -eq 0) {
    Write-Host "No network adapters found!" -ForegroundColor Red
    exit 1
}

Write-Host "Available network interfaces:" -ForegroundColor Yellow
Write-Host ""

$index = 1
$adapterList = @()

foreach ($adapter in $adapters) {
    $info = [PSCustomObject]@{
        Index = $index
        Interface = $adapter.InterfaceAlias
        IP = $adapter.IPAddress
    }
    $adapterList += $info
    Write-Host "$index. $($adapter.InterfaceAlias)" -ForegroundColor White
    Write-Host "   IP: $($adapter.IPAddress)" -ForegroundColor Gray
    Write-Host ""
    $index++
}

# Try to find the most likely adapter (prioritize Wi-Fi, then Ethernet)
# Exclude virtual adapters
$primaryAdapter = $adapters | Where-Object {
    ($_.InterfaceAlias -like "*Wi-Fi*" -or 
     $_.InterfaceAlias -like "*Ethernet*" -or
     $_.InterfaceAlias -like "*WLAN*") -and
    $_.InterfaceAlias -notlike "*vEthernet*" -and
    $_.InterfaceAlias -notlike "*WSL*" -and
    $_.InterfaceAlias -notlike "*Hyper-V*"
} | Sort-Object @{
    Expression = {
        if ($_.InterfaceAlias -like "*Wi-Fi*") { 1 }
        elseif ($_.InterfaceAlias -like "*WLAN*") { 2 }
        else { 3 }
    }
} | Select-Object -First 1

if ($primaryAdapter) {
    $primaryIP = $primaryAdapter.IPAddress
    Write-Host "Primary network interface detected: $($primaryAdapter.InterfaceAlias)" -ForegroundColor Green
    Write-Host "IP Address: $primaryIP" -ForegroundColor Green
    Write-Host ""
    Write-Host "Use this URL in your mobile app:" -ForegroundColor Cyan
    Write-Host "  http://$primaryIP:8000" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To set it in app.json, update the 'extra.apiUrl' field:" -ForegroundColor Cyan
    Write-Host '  "extra": {' -ForegroundColor Gray
    Write-Host "    `"apiUrl`": `"http://$primaryIP:8000`"" -ForegroundColor Yellow
    Write-Host '  }' -ForegroundColor Gray
} else {
    Write-Host "Could not auto-detect primary adapter." -ForegroundColor Yellow
    Write-Host "Please select the correct interface from the list above." -ForegroundColor Yellow
}

