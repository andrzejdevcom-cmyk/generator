$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'tools.ps1')
$tools = Get-LetterMakerTools
Push-Location -LiteralPath $projectRoot
try {
    Write-Host '3DAS Letter Maker - instalacja zaleznosci' -ForegroundColor Cyan
    $venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $pythonCommand = $tools.Python
        $pythonArguments = $tools.Arguments
        & $pythonCommand @pythonArguments -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Nie udalo sie utworzyc srodowiska Python.' }
    }
    & $venvPython -c "import sys; raise SystemExit(sys.version_info[:2] != (3,12))"
    if ($LASTEXITCODE -ne 0) { throw 'Istniejacy .venv wymaga Python 3.12. Zachowaj swoje dane i odtworz .venv.' }
    & $venvPython -m pip install --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Instalacja bibliotek Python nie powiodla sie. Sprawdz log powyzej i dostep do Internetu.' }
    Push-Location -LiteralPath (Join-Path $projectRoot 'frontend')
    try {
        & npm.cmd ci --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw 'Instalacja npm nie powiodla sie.' }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Budowanie interfejsu nie powiodlo sie.' }
    } finally { Pop-Location }
    & $venvPython -c "from backend.geometry.engine import generate; from backend.models import Project; r=generate(Project()); assert r.valid and all(p.mesh.is_volume for p in r.parts); print('Geometria A: OK')"
    if ($LASTEXITCODE -ne 0) { throw 'Test geometrii nie powiodl sie.' }
    Write-Host 'Instalacja gotowa. Uruchom start.bat.' -ForegroundColor Green
} finally { Pop-Location }
