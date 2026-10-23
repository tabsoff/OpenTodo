$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$preview = [IO.Path]::GetFullPath((Join-Path $repo '../local-preview'))
$stateFile = Join-Path $preview 'processes.json'
$apiBinary = Join-Path $preview 'opentodo.exe'
$node = (Get-Command node.exe -ErrorAction Stop).Source

function Own-Process($record) {
    $proc = Get-Process -Id $record.id -ErrorAction SilentlyContinue
    return $proc -and $proc.Path -eq $record.path -and $proc.StartTime.ToUniversalTime().Ticks.ToString() -eq $record.started
}
if (Test-Path -LiteralPath $stateFile) {
    $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    if ((Own-Process $state.api) -and (Own-Process $state.web)) {
        Write-Output 'Preview is already running: http://localhost:5173'
        exit 0
    }
    throw 'A previous preview did not stop completely. Run stop-preview.ps1 first.'
}
$listeners = [Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
if ($listeners | Where-Object { $_.Port -in @(8080, 5173) }) {
    throw 'Port 8080 or 5173 is already in use. Existing processes were not stopped.'
}
New-Item -ItemType Directory -Force -Path $preview | Out-Null
if (!(Test-Path (Join-Path $repo 'web/node_modules/vite/bin/vite.js'))) {
    Push-Location (Join-Path $repo 'web')
    try {
        & npm.cmd ci --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependencies failed to install.' }
    } finally { Pop-Location }
}
$sourceDates = @(Get-ChildItem (Join-Path $repo 'cmd'),(Join-Path $repo 'internal') -File -Recurse |
    Where-Object { $_.FullName -notlike '*\internal\web\dist\*' } | ForEach-Object LastWriteTimeUtc)
$sourceDates += (Get-Item (Join-Path $repo 'go.mod'),(Join-Path $repo 'go.sum')).LastWriteTimeUtc
$latest = ($sourceDates | Sort-Object -Descending | Select-Object -First 1)
if (!(Test-Path -LiteralPath $apiBinary) -or (Get-Item -LiteralPath $apiBinary).LastWriteTimeUtc -lt $latest) {
    $version = ([regex]::Match((Get-Content (Join-Path $repo 'go.mod') -Raw), '(?m)^toolchain go([^\r\n]+)')).Groups[1].Value
    $go = [IO.Path]::GetFullPath((Join-Path $repo "../runtimes/go$version/go/bin/go.exe"))
    if (!(Test-Path -LiteralPath $go)) { $go = (Get-Command go.exe -ErrorAction Stop).Source }
    $goEnv = @{}
    foreach ($name in @('GOTOOLCHAIN', 'GOPATH', 'GOCACHE')) { $goEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
    Push-Location $repo
    try {
        $env:GOTOOLCHAIN = 'local'
        $env:GOPATH = [IO.Path]::GetFullPath((Join-Path $repo '../go-cache'))
        $env:GOCACHE = [IO.Path]::GetFullPath((Join-Path $repo '../go-build-cache'))
        & $go build -o $apiBinary ./cmd/opentodo
        if ($LASTEXITCODE -ne 0) { throw 'Local API build failed.' }
    } finally {
        Pop-Location
        foreach ($name in $goEnv.Keys) { [Environment]::SetEnvironmentVariable($name, $goEnv[$name], 'Process') }
    }
}

function Record-Process($proc) {
    return @{ id = $proc.Id; path = $proc.Path; started = $proc.StartTime.ToUniversalTime().Ticks.ToString() }
}
function Wait-URL($url, $proc) {
    for ($i = 0; $i -lt 120; $i++) {
        if ($proc.HasExited) { throw "Preview process exited. Inspect logs in $preview" }
        try { return Invoke-RestMethod $url -TimeoutSec 1 } catch { Start-Sleep -Milliseconds 250 }
    }
    throw "Preview did not become ready: $url"
}
$names = @('OPENTODO_ADDR', 'OPENTODO_DATA_DIR', 'OPENTODO_BASE_URL', 'OPENTODO_SETUP_TOKEN', 'OPENTODO_PUSH')
$saved = @{}
foreach ($name in $names) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$api = $null
$web = $null
try {
    $env:OPENTODO_ADDR = '127.0.0.1:8080'
    $env:OPENTODO_DATA_DIR = Join-Path $preview 'data'
    $env:OPENTODO_BASE_URL = 'http://localhost:5173'
    $env:OPENTODO_SETUP_TOKEN = [guid]::NewGuid().ToString('N')
    $env:OPENTODO_PUSH = 'off'
    $api = Start-Process -FilePath $apiBinary -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $preview 'api.log') -RedirectStandardError (Join-Path $preview 'api-error.log')
    $null = Wait-URL 'http://127.0.0.1:8080/healthz' $api
    $auth = Invoke-RestMethod 'http://127.0.0.1:8080/api/v1/auth/status'
    if ($auth.setupRequired) {
        $credentials = @{ email = 'preview@example.test'; password = ('Preview-' + [guid]::NewGuid().ToString('N')); name = 'Local preview' }
        $body = $credentials.Clone()
        $body.setupToken = $env:OPENTODO_SETUP_TOKEN
        $null = Invoke-RestMethod 'http://127.0.0.1:8080/api/v1/auth/register' -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json)
        $credentials | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $preview 'credentials.json') -Encoding utf8
    }
    $vite = Join-Path $repo 'web/node_modules/vite/bin/vite.js'
    $web = Start-Process -FilePath $node -ArgumentList @(('"' + $vite + '"'), '--host', 'localhost', '--port', '5173', '--strictPort') -WorkingDirectory (Join-Path $repo 'web') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $preview 'web.log') -RedirectStandardError (Join-Path $preview 'web-error.log')
    $null = Wait-URL 'http://localhost:5173/healthz' $web
    @{ api = (Record-Process $api); web = (Record-Process $web) } | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding utf8
    Write-Output 'Preview ready: http://localhost:5173'
    Write-Output "Synthetic account: $preview/credentials.json"
} catch {
    foreach ($proc in @($web, $api)) { if ($proc -and !$proc.HasExited) { Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue } }
    throw
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
}
