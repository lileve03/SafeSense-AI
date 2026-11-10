$base = 'http://127.0.0.1:8000'
Write-Host '1) Resetting prototype data'
Invoke-RestMethod -Uri "$base/reset" -Method Post | ConvertTo-Json
Write-Host '2) Fall only => OBSERVE'
Invoke-RestMethod -Uri "$base/event" -Method Post -ContentType 'application/json' -Body '{"zone":"Demo-Private-A","type":"fall","confidence":0.96,"source":"simulation"}' | ConvertTo-Json -Depth 5
Write-Host '3) Scream in same zone within 5 seconds => HIGH'
Invoke-RestMethod -Uri "$base/event" -Method Post -ContentType 'application/json' -Body '{"zone":"Demo-Private-A","type":"scream","confidence":0.94,"source":"simulation"}' | ConvertTo-Json -Depth 5
Write-Host '4) SOS => CRITICAL'
Invoke-RestMethod -Uri "$base/event" -Method Post -ContentType 'application/json' -Body '{"zone":"Demo-Private-A","type":"sos","confidence":1.0,"source":"simulation"}' | ConvertTo-Json -Depth 5
Write-Host '5) Current state'
Invoke-RestMethod -Uri "$base/state" | ConvertTo-Json -Depth 6
