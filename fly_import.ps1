# fly_import.ps1 — Upload local scenario files to Fly.io
$app = "orcanos-performance"
$scenariosDir = "C:\AI Projects\orcanos-performance\backend\scenarios"

# 1. Wake the machine
Write-Host "Waking machine..."
try { Invoke-WebRequest -Uri "https://$app.fly.dev/healthz" -UseBasicParsing -TimeoutSec 10 | Out-Null } catch {}
Start-Sleep -Seconds 3

# 2. Ensure /data/scenarios exists
Write-Host "Creating /data/scenarios..."
flyctl ssh console --app $app -C "mkdir -p /data/scenarios"

# 3. Upload scenario JSON files via SFTP
Write-Host "`nUploading scenario files..."
$files = Get-ChildItem "$scenariosDir\*.json"
if ($files.Count -eq 0) {
    Write-Host "  No scenario files found in $scenariosDir"
} else {
    foreach ($file in $files) {
        $remotePath = "/data/scenarios/$($file.Name)"
        Write-Host "  $($file.Name) ($($file.Length) bytes)"
        flyctl sftp put --app $app "$($file.FullName)" "$remotePath"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ERROR uploading $($file.Name)"
        } else {
            Write-Host "  OK"
        }
    }
}

# 4. Verify
Write-Host "`nVerifying /data/scenarios/..."
flyctl ssh console --app $app -C "ls -la /data/scenarios/"
Write-Host "`nDone!"
