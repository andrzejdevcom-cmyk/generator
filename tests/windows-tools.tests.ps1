param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $projectRoot 'scripts/tools.ps1')
$PSNativeCommandUseErrorActionPreference = $true
$temp = Join-Path ([IO.Path]::GetTempPath()) ('3das tools with spaces ' + [guid]::NewGuid())
New-Item -Path $temp -ItemType Directory | Out-Null
$stub = Join-Path $temp 'python runtime probe.py'
@'
import json, sys
mode = sys.argv[1]
if mode == 'missing':
    sys.stderr.write('No suitable Python runtime found\n')
    sys.exit(103)
if mode == 'broken':
    print('not a Python version')
    sys.exit(0)
version = [3, 15, 0] if mode == 'new' else [3, 12, 10]
print(json.dumps(dict(version=version, bits=32 if mode == '32' else 64)))
'@ | Set-Content -LiteralPath $stub -Encoding UTF8
$passed = 0
function Assert-True([bool]$condition, [string]$message) {
    if (-not $condition) { throw $message }
}
function Candidate([string]$mode) {
    return @{ Command = $Python; Arguments = @($stub, $mode) }
}
function Test-Case([string]$name, [scriptblock]$body) {
    & $body
    $script:passed++
    Write-Host "PASS $name"
}
try {
    Test-Case 'missing launcher runtime does not terminate fallback' {
        $probe = Invoke-LetterMakerProbe -Command $Python -Arguments @($stub, 'missing')
        Assert-True ($probe.ExitCode -eq 103) 'The native exit code was lost.'
        $selected = Find-LetterMakerPython -Candidates @((Candidate 'missing'), (Candidate 'valid'))
        Assert-True ($selected.Version -eq '3.12.10') 'Fallback did not select the compatible runtime.'
        Assert-True ($ErrorActionPreference -eq 'Stop') 'The caller error preference changed.'
    }
    Test-Case 'newer Python does not hide compatible 3.12' {
        $selected = Find-LetterMakerPython -Candidates @((Candidate 'new'), (Candidate 'valid'))
        Assert-True ($selected.Arguments[1] -eq 'valid') 'Selected an unsupported newer Python.'
    }
    Test-Case 'only 3.15 reports detected version and installation steps' {
        $message = ''
        try { $null = Find-LetterMakerPython -Candidates @((Candidate 'new')) } catch { $message = $_.Exception.Message }
        Assert-True ($message -match '3\.15\.0' -and $message -match '3\.12' -and $message -match 'winget install') 'Missing actionable version diagnostic.'
    }
    Test-Case '32-bit Python is skipped in favor of 64-bit' {
        $selected = Find-LetterMakerPython -Candidates @((Candidate '32'), (Candidate 'valid'))
        Assert-True ($selected.Arguments[1] -eq 'valid') 'Selected 32-bit Python.'
    }
    Test-Case 'missing command and invalid output do not stop discovery' {
        $selected = Find-LetterMakerPython -Candidates @(@{ Command = (Join-Path $temp 'absent-python'); Arguments = @() }, (Candidate 'broken'), (Candidate 'valid'))
        Assert-True ($selected.Version -eq '3.12.10') 'Failed to continue after an unusable command.'
    }
    Test-Case 'paths and native arguments with spaces reach the process intact' {
        $selected = Find-LetterMakerPython -Candidates @((Candidate 'valid'))
        Assert-True ($selected.Arguments[0] -eq $stub) 'The path containing spaces changed.'
    }
    Test-Case 'actual installed Python is probed as a 64-bit 3.12 runtime' {
        $selected = Find-LetterMakerPython -Candidates @(@{ Command = $Python; Arguments = @() })
        Assert-True ($selected.Version -like '3.12.*') 'The real Python probe failed.'
    }
    Test-Case 'empty discovery returns a readable installation error' {
        $message = ''
        try { $null = Find-LetterMakerPython -Candidates @() } catch { $message = $_.Exception.Message }
        Assert-True ($message -match 'Nie znaleziono' -and $message -match 'py -3\.12 --version') 'Missing installation guidance.'
    }
    Test-Case 'discovery finds the compatible interpreter on this host' {
        $selected = Find-LetterMakerPython -Candidates @(Get-LetterMakerPythonCandidates)
        Assert-True ($selected.Version -like '3.12.*') 'Discovery did not locate the installed interpreter.'
    }
    Test-Case 'all installer entry scripts parse without syntax errors' {
        foreach ($file in (Get-ChildItem -Path (Join-Path $projectRoot 'scripts/*.ps1'))) {
            $tokens = $null
            $parseErrors = $null
            $null = [Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$parseErrors)
            Assert-True ($parseErrors.Count -eq 0) "Syntax error in $($file.Name)."
        }
    }
    Write-Host "$passed installer tests passed."
} finally {
    Remove-Item -LiteralPath $temp -Recurse -Force
}
