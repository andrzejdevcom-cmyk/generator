$ErrorActionPreference = 'Stop'

function Invoke-LetterMakerProbe {
    param([string]$Command, [string[]]$Arguments)
    # PowerShell 5.1 can turn stderr into a terminating NativeCommandError
    # under Stop, even when redirected. Failed probes must allow fallback.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
        $PSNativeCommandUseErrorActionPreference = $false
    }
    try {
        $output = @(& $Command @Arguments 2>$null)
        $exitCode = $LASTEXITCODE
        return @{ ExitCode = $exitCode; Output = ($output -join [Environment]::NewLine) }
    } catch {
        return @{ ExitCode = -1; Output = '' }
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Get-LetterMakerPythonCandidates {
    $candidates = @()
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $paths = @((Join-Path $projectRoot '.venv\Scripts\python.exe'))
    # Find 3.12 even when a newer Python owns PATH.
    if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        foreach ($key in @(
            'HKCU:\Software\Python\PythonCore\3.12\InstallPath',
            'HKLM:\Software\Python\PythonCore\3.12\InstallPath',
            'HKLM:\Software\WOW6432Node\Python\PythonCore\3.12\InstallPath'
        )) {
            if (Test-Path -LiteralPath $key) {
                $folder = (Get-Item -LiteralPath $key).GetValue('')
                if ($folder) { $paths += Join-Path $folder 'python.exe' }
            }
        }
        if ($env:LOCALAPPDATA) {
            $paths += Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
            $managed = Join-Path $env:LOCALAPPDATA 'Python\pythoncore-3.12-*\python.exe'
            $paths += @(Get-ChildItem -Path $managed -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
        }
        if ($env:ProgramFiles) { $paths += Join-Path $env:ProgramFiles 'Python312\python.exe' }
    }
    foreach ($path in ($paths | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            $candidates += @{ Command = $path; Arguments = @() }
        }
    }
    $launcher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($launcher) {
        $candidates += @{ Command = $launcher.Source; Arguments = @('-3.12') }
        $candidates += @{ Command = $launcher.Source; Arguments = @() }
    }
    foreach ($name in @('python3.12', 'python', 'python3')) {
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command) { $candidates += @{ Command = $command.Source; Arguments = @() } }
    }
    return $candidates
}

function Find-LetterMakerPython {
    param([object[]]$Candidates)
    $detected = @()
    $code = "import json,struct,sys; print(json.dumps(dict(version=list(sys.version_info[:3]), bits=struct.calcsize('P')*8)))"
    foreach ($candidate in $Candidates) {
        $arguments = @($candidate.Arguments) + @('-c', $code)
        $probe = Invoke-LetterMakerProbe -Command $candidate.Command -Arguments $arguments
        if ($probe.ExitCode -ne 0) { continue }
        try { $info = $probe.Output | ConvertFrom-Json -ErrorAction Stop } catch { continue }
        if (-not $info.version -or $info.version.Count -lt 2) { continue }
        $version = $info.version -join '.'
        $detected += "Python $version ($($info.bits)-bit)"
        if ($info.version[0] -eq 3 -and $info.version[1] -eq 12 -and $info.bits -eq 64) {
            return @{ Python = $candidate.Command; Arguments = @($candidate.Arguments); Version = $version }
        }
    }
    $found = if ($detected.Count) { 'Wykryto: ' + (($detected | Select-Object -Unique) -join ', ') + '.' } else { 'Nie znaleziono uruchamialnego Pythona.' }
    throw @"
$found
Ten projekt wymaga Python 3.12 (64-bit). Python 3.15 ani inna nowsza wersja nie zastepuje 3.12 dla tej instalacji.
Mozesz zachowac obecnego Pythona i doinstalowac 3.12 obok niego.
W terminalu Windows wykonaj: winget install --id Python.Python.3.12 --exact
Jesli uzywasz nowego Python Install Manager, alternatywnie: py install 3.12
Otworz nowy terminal i sprawdz: py -3.12 --version
Nastepnie uruchom ponownie install.bat. Instrukcja: docs/INSTALLATION.md
"@
}

function Get-LetterMakerNode {
    param([string]$Command, [string[]]$Arguments = @())
    # Read the version instead of running inline JavaScript through
    # Windows' native command-line quoting rules.
    $probe = Invoke-LetterMakerProbe -Command $Command -Arguments (@($Arguments) + @('--version'))
    if ($probe.ExitCode -ne 0) {
        throw "Nie udalo sie odczytac wersji Node.js z: $Command. Sprawdz polecenie node --version."
    }
    $version = $probe.Output.Trim()
    $match = [regex]::Match($version, '^v?(\d+)\.(\d+)\.(\d+)$')
    if (-not $match.Success) {
        throw "Nie rozpoznano numeru wersji Node.js z: $Command. Sprawdz polecenie node --version."
    }
    $major = [int]$match.Groups[1].Value
    $minor = [int]$match.Groups[2].Value
    if ($major -lt 22 -or ($major -eq 22 -and $minor -lt 12)) {
        throw "Wykryto Node.js $version. Wymagany Node.js 22.12 lub nowszy; zalecane 24 lub 26 LTS z nodejs.org. Uzywany plik: $Command"
    }
    return @{ Node = $Command; Version = $version }
}

function Get-LetterMakerTools {
    $python = Find-LetterMakerPython -Candidates @(Get-LetterMakerPythonCandidates)
    Write-Host "Python $($python.Version) (64-bit): OK" -ForegroundColor Green
    $nodeCommand = Get-Command node -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $nodeCommand) { throw 'Zainstaluj Node.js 22.12 lub nowszy; zalecane 24 lub 26 LTS z nodejs.org.' }
    $node = Get-LetterMakerNode -Command $nodeCommand.Source
    Write-Host "Node.js $($node.Version): OK ($($node.Node))" -ForegroundColor Green
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'Brak npm.cmd. Zainstaluj ponownie Node.js wraz z npm.' }
    $python.Node = $node.Node
    $python.NodeVersion = $node.Version
    return $python
}
