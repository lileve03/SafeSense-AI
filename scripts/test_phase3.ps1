$base = 'http://127.0.0.1:8000'
function Send-Event($zone, $type, $source) {
    $body = @{zone=$zone;type=$type;confidence=0.95;source=$source} | ConvertTo-Json
    $result = Invoke-RestMethod -Uri "$base/event" -Method POST -ContentType 'application/json' -Body $body
    Write-Host "$zone | $type | $source => $($result.event.level)"
    return $result
}
Invoke-RestMethod -Uri "$base/reset" -Method POST | Out-Null
Write-Host '--- Private: Fall + Scream ---'
$null = Send-Event 'Demo-Private-A' 'fall' 'radar'
$null = Send-Event 'Demo-Private-A' 'scream' 'yamnet'
Write-Host '--- Open Hidden: Rapid Motion + Impact ---'
$null = Send-Event 'Corridor A' 'rapid_motion' 'vision'
$null = Send-Event 'Corridor A' 'impact' 'yamnet'
Write-Host '--- SOS ---'
$null = Send-Event 'Demo-Private-A' 'sos' 'simulation'
Write-Host '--- Expected: OBSERVE, HIGH, OBSERVE, HIGH, CRITICAL ---'
$state = Invoke-RestMethod -Uri "$base/state"
$state.incidents | Select-Object zone, zone_type, level, status | Format-Table -AutoSize
Write-Host '--- Privacy rejection test (expect 422) ---'
try {
    $null = Send-Event 'Demo-Private-A' 'rapid_motion' 'vision'
    Write-Error 'FAIL: private vision event unexpectedly accepted'
} catch {
    Write-Host 'PASS: CCTV/vision event rejected for private zone'
}
