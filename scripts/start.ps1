$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'tools.ps1')
$null = Get-LetterMakerTools
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython) -or -not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\index.html'))) {
    & (Join-Path $PSScriptRoot 'install.ps1')
}
$url = 'http://127.0.0.1:8000'
$health = $null
try { $health = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 2 } catch {}
if ($health -and $health.application -eq '3DAS Letter Maker') {
    Start-Process $url
    Write-Host '3DAS Letter Maker juz dziala.'
    exit 0
}
Write-Host '3DAS Letter Maker - uruchamianie lokalne (Ctrl+C zamyka serwer)' -ForegroundColor Cyan
Write-Host 'Frontend i API sa obslugiwane pod jednym adresem.'
$server = Start-Process -FilePath $venvPython -ArgumentList @('-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $projectRoot -PassThru -NoNewWindow
try {
    $ready = $false
    for ($i=0; $i -lt 60; $i++) {
        if ($server.HasExited) { throw 'Serwer zakonczyl prace. Sprawdz zaleznosci i czy port 8000 jest wolny.' }
        try {
            $health = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 2
            if ($health.application -eq '3DAS Letter Maker') { $ready = $true; break }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Nie otrzymano potwierdzenia gotowosci API.' }
    Start-Process $url
    $server.WaitForExit()
    if ($server.ExitCode -ne 0) { throw 'Serwer zakonczyl prace z bledem.' }
} finally {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id }
}
