$ErrorActionPreference = 'Stop'
function Get-LetterMakerTools {
    $pythonCommand = $null
    $pythonArguments = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -c "import sys; raise SystemExit(sys.version_info[:2] != (3,12))" 2>$null
        if ($LASTEXITCODE -eq 0) { $pythonCommand = 'py'; $pythonArguments = @('-3.12') }
    }
    if (-not $pythonCommand -and (Get-Command python -ErrorAction SilentlyContinue)) {
        & python -c "import sys; raise SystemExit(sys.version_info[:2] != (3,12))" 2>$null
        if ($LASTEXITCODE -eq 0) { $pythonCommand = 'python' }
    }
    if (-not $pythonCommand) { throw 'Zainstaluj Python 3.12 (64-bit) z python.org i zaznacz Add Python to PATH.' }
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Zainstaluj Node.js 22 lub 24 LTS z nodejs.org.' }
    & node -e "const v=+process.versions.node.split('.')[0];process.exit(v>=22&&v<25?0:1)"
    if ($LASTEXITCODE -ne 0) { throw 'Wymagany Node.js w wersji 22–24 (zalecana wersja LTS).' }
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'Brak npm.cmd. Zainstaluj ponownie Node.js wraz z npm.' }
    return @{ Python = $pythonCommand; Arguments = $pythonArguments }
}
