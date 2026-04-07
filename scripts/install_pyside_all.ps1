<#
.SYNOPSIS
Installs PySide6 into all detected Python interpreters on PATH.

.DESCRIPTION
This script locates Python executables found by `where.exe python` and the
`py -0p` launcher, checks whether `PySide6` is installed, and offers to
install it for each interpreter. Use `-Yes` to skip prompts and install
non-interactively. Use `-User` to force `--user` installs.

USAGE
.
    .\install_pyside_all.ps1 [-Yes] [-User] [-Force]

Examples
    .\install_pyside_all.ps1 -Yes
    .\install_pyside_all.ps1 -User
#>

param(
    [switch]$Yes,
    [switch]$User,
    [switch]$Force
)

function Get-PythonPaths {
    $paths = [System.Collections.ArrayList]::new()
    try {
        $out = & where.exe python 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            foreach ($p in $out) {
                $pp = $p.Trim()
                if ($pp -and -not $paths.Contains($pp)) { $paths.Add($pp) | Out-Null }
            }
        }
    } catch {
    }

    try {
        $out = & py -0p 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            foreach ($p in $out) {
                $pp = $p.Trim()
                if ($pp -and -not $paths.Contains($pp)) { $paths.Add($pp) | Out-Null }
            }
        }
    } catch {
    }

    # ensure current interpreter is first
    try {
        $cur = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($cur -and -not $paths.Contains($cur)) { $paths.Insert(0,$cur) | Out-Null }
    } catch { }

    return ,$paths
}

function Test-PySideInstalled($python) {
    try {
        $out = & $python -c "import importlib.util,sys; spec = importlib.util.find_spec('PySide6'); sys.stdout.write('1' if spec else '0')" 2>$null
        return ($out -eq '1')
    } catch {
        return $false
    }
}

function Ensure-Pip($python) {
    try {
        $out = & $python -m pip --version 2>$null
        if ($LASTEXITCODE -eq 0) { return $true }
    } catch {}
    try {
        Write-Host "No pip detected for $python; attempting ensurepip..."
        & $python -m ensurepip --upgrade 2>&1 | Write-Host
        & $python -m pip install -U pip 2>&1 | Write-Host
        return $true
    } catch {
        Write-Host "Failed to ensure pip for $python: $_"
        return $false
    }
}

function Install-PySide($python, [switch]$useUser) {
    $args = @('-m','pip','install','-U','PySide6')
    if ($useUser) { $args += '--user' }
    try {
        Write-Host "Running: $python $($args -join ' ')"
        $proc = Start-Process -FilePath $python -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput tmp_out.txt -RedirectStandardError tmp_err.txt
        $out = Get-Content tmp_out.txt -Raw -ErrorAction SilentlyContinue
        $err = Get-Content tmp_err.txt -Raw -ErrorAction SilentlyContinue
        Remove-Item tmp_out.txt,tmp_err.txt -ErrorAction SilentlyContinue
        if ($proc.ExitCode -eq 0) {
            Write-Host "Installed PySide6 for $python"
            return $true
        } else {
            Write-Host "pip install returned exit code $($proc.ExitCode) for $python"
            if ($err) { Write-Host $err }
            return $false
        }
    } catch {
        Write-Host "Error while installing PySide6 for $python: $_"
        return $false
    }
}

Write-Host "Detecting Python interpreters on PATH..."
$pythons = Get-PythonPaths
if (-not $pythons) { Write-Host "No Python interpreters found on PATH."; exit 1 }

Write-Host "Found interpreters:`n" + ($pythons -join "`n")

$summary = @()
foreach ($py in $pythons) {
    if (-not (Test-Path $py)) {
        Write-Host "Skipping missing path: $py"; continue
    }
    if ($py -like '*WindowsApps*' -and -not $Force) {
        Write-Host "Skipping Microsoft Store stub: $py (use -Force to include)"; $summary += [pscustomobject]@{Python=$py; Status='Skipped (WindowsApps)'}; continue
    }

    Write-Host "\nInterpreter: $py"
    $installed = Test-PySideInstalled $py
    if ($installed) { Write-Host "  PySide6 already installed"; $summary += [pscustomobject]@{Python=$py; Status='Already installed'}; continue }

    Write-Host "  PySide6 not installed."
    if (-not $Yes) {
        $resp = Read-Host "  Install PySide6 for $py? (Y/N/A=Always skip/INSTALL ALL=all)"
        if ($resp -match '^[Nn]') { Write-Host '  Skipping'; $summary += [pscustomobject]@{Python=$py; Status='User skipped'}; continue }
        if ($resp -match '^[Aa]') { Write-Host '  Skipping all Microsoft Store/unsupported'; $summary += [pscustomobject]@{Python=$py; Status='Skipped (user)'}; continue }
        if ($resp -match '^(?:ALL|all|Install All|install all)$') { $Yes = $true }
    }

    # ensure pip
    $havePip = Ensure-Pip $py
    if (-not $havePip) { Write-Host "  Cannot install pip for $py; skipping"; $summary += [pscustomobject]@{Python=$py; Status='No pip'}; continue }

    $ok = Install-PySide $py (if ($User) { $true } else { $false })
    if ($ok) { $summary += [pscustomobject]@{Python=$py; Status='Installed'} } else { $summary += [pscustomobject]@{Python=$py; Status='Failed'} }
}

Write-Host "\nSummary:"; $summary | Format-Table -AutoSize

Write-Host "Done. To verify, re-run: scripts\find_pyside.py or run debug_run_gui_local.py with the chosen interpreter."
