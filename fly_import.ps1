# fly_import.ps1 — Import local DB accounts + scenario files to Fly.io
$app = "orcanos-performance"
$python = "C:\AI Projects\orcanos-performance\.venv\Scripts\python.exe"
$scenariosDir = "C:\AI Projects\orcanos-performance\backend\scenarios"

function Invoke-Fly($cmd) {
    $result = flyctl ssh console --app $app --command $cmd 2>&1
    if ($LASTEXITCODE -ne 0 -and $result -notmatch "handle is invalid") {
        Write-Host "  WARN: $result"
    }
}

function Keep-Alive {
    try { Invoke-WebRequest -Uri "https://$app.fly.dev/health" -UseBasicParsing -TimeoutSec 5 | Out-Null } catch {}
}

# 1. Start machine
Write-Host "Starting machine..."
flyctl machine start d8dd330b71d198 --app $app 2>&1 | Out-Null
Start-Sleep -Seconds 8

# 2. Ensure /data/scenarios exists
Write-Host "Creating /data/scenarios..."
Invoke-Fly "mkdir -p /data/scenarios"
Keep-Alive

# 3. Insert accounts
Write-Host "`nInserting accounts..."
$accounts = & $python -c @"
import sqlite3
conn = sqlite3.connect(r'C:\AI Projects\orcanos-performance\orcanos_performance.db')
cur = conn.cursor()
cur.execute('SELECT id, name, url, encrypted_password, enabled, created_at, version FROM accounts')
rows = cur.fetchall()
for r in rows:
    ep = r[3].replace("'", "''")
    print(f"INSERT OR REPLACE INTO accounts (id, name, url, encrypted_password, enabled, created_at, version) VALUES ({r[0]}, '{r[1]}', '{r[2]}', '{ep}', {r[4]}, '{r[5]}', '{r[6]}');")
"@

foreach ($sql in $accounts) {
    $name = if ($sql -match "VALUES \(\d+, '([^']+)'") { $matches[1] } else { "?" }
    $pycmd = "import sqlite3; c=sqlite3.connect('/data/orcanos_performance.db'); c.execute(`"$sql`"); c.commit(); print('ok')"
    Write-Host "  Account: $name"
    Invoke-Fly "python3 -c `"$pycmd`""
    Keep-Alive
}

# 4. Upload scenario JSON files
Write-Host "`nUploading scenario files..."
Get-ChildItem "$scenariosDir\*.json" | ForEach-Object {
    $file = $_
    $safeName = $file.Name -replace "'", "''"
    Write-Host "  $($file.Name) ($($file.Length) bytes)"

    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($file.FullName))
    $pycmd = "import base64,os; os.makedirs('/data/scenarios', exist_ok=True); open('/data/scenarios/$safeName','wb').write(base64.b64decode('$b64')); print('ok')"

    Invoke-Fly "python3 -c `"$pycmd`""
    Keep-Alive
}

# 5. Verify
Write-Host "`nVerifying..."
Invoke-Fly "python3 -c `"import sqlite3; c=sqlite3.connect('/data/orcanos_performance.db'); print('Accounts:', c.execute('SELECT COUNT(*) FROM accounts').fetchone()[0])`""
Invoke-Fly "ls /data/scenarios/"
Write-Host "`nDone!"
