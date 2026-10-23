$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$preview = [IO.Path]::GetFullPath((Join-Path $repo '../local-preview'))
$stateFile = Join-Path $preview 'processes.json'
if (!(Test-Path -LiteralPath $stateFile)) { Write-Output 'No recorded preview processes.'; exit 0 }
$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
foreach ($record in @($state.web, $state.api)) {
    $proc = Get-Process -Id $record.id -ErrorAction SilentlyContinue
    if (!$proc) { continue }
    if ($proc.Path -ne $record.path -or $proc.StartTime.ToUniversalTime().Ticks.ToString() -ne $record.started) {
        throw 'Recorded PID belongs to a different process. It was not stopped.'
    }
    Stop-Process -Id $proc.Id
    Wait-Process -Id $proc.Id -Timeout 10 -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath $stateFile
Write-Output 'Local preview stopped. Synthetic data is preserved.'
