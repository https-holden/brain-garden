# Set up a Windows PC for a second brain: git, Python, Obsidian, and your vault.
# Safe to run as many times as you like: it skips whatever is already installed.
#
# In PowerShell (Start menu, type PowerShell), from this repo's folder:
#   powershell -ExecutionPolicy Bypass -File setup\windows.ps1
#   powershell -ExecutionPolicy Bypass -File setup\windows.ps1 -Name Sam -Preset personal
#
# Uses winget, which comes with Windows 10 and 11. No administrator password is
# needed for anything but the installers' own prompts.
param(
    [string]$Name = "",
    [ValidateSet("", "personal", "work")][string]$Preset = "",
    [string]$Dest = "",
    [switch]$Pdf
)
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $PSScriptRoot
$Seed = Join-Path $Here "setup\build_vault.py"
function Say($t) { Write-Host "`n==> $t" -ForegroundColor Cyan }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

if (-not (Have "winget")) {
    Write-Host "winget is missing. Install 'App Installer' from the Microsoft Store, then run this again."
    exit 1
}

Say "1. Git"
if (Have "git") { git --version } else {
    winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
    Refresh-Path
}

Say "2. Python"
$Py = $null
foreach ($c in @("py", "python")) {
    if (Have $c) {
        $v = & $c --version 2>&1
        if ($v -match "Python 3") { $Py = $c; break }
    }
}
if (-not $Py) {
    winget install --id Python.Python.3.12 -e --source winget --accept-source-agreements --accept-package-agreements
    Refresh-Path
    $Py = if (Have "py") { "py" } else { "python" }
}
& $Py --version
Write-Host "On Windows, type '$Py' wherever the vault's guides say 'python3'."

Say "3. Obsidian"
$obs = Join-Path $env:LOCALAPPDATA "Programs\Obsidian\Obsidian.exe"
if (Test-Path $obs) { Write-Host "installed" } else {
    winget install --id Obsidian.Obsidian -e --source winget --accept-source-agreements --accept-package-agreements
}

Say "4. Your vault"
if (-not $Name) { $Name = Read-Host "Your first name (it goes in the vault's name)" }
if (-not $Name) { $Name = "My" }
if (-not $Preset) {
    Write-Host "What is this second brain mostly for?"
    Write-Host "  1) My life: ideas, journal, things I read, people, projects (personal)"
    Write-Host "  2) My job: how things work, how to do things, colleagues, meetings (work)"
    $pick = Read-Host "Pick 1 or 2 [1]"
    $Preset = if ($pick -eq "2") { "work" } else { "personal" }
}
$slug = ($Name.ToLower() -replace "[^a-z0-9]+", "-").Trim("-")
$suffix = if ($Preset -eq "work") { "work-brain" } else { "brain" }
$title = if ($Preset -eq "work") { "$Name's Work Brain" } else { "$Name's Brain" }
if (-not $Dest) { $Dest = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Obsidian\$slug-$suffix" }
if (Test-Path (Join-Path $Dest "CLAUDE.md")) {
    Write-Host "A vault already exists at $Dest; leaving it as it is."
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dest) | Out-Null
    & $Py $Seed --preset $Preset --dest $Dest --name $title --owner $Name
    if (-not (Test-Path (Join-Path $Dest ".git"))) { git -C $Dest init -q }
}

Say "5. Reading PDFs (optional)"
& $Py -c "import pypdf" 2>$null
if ($LASTEXITCODE -eq 0) { Write-Host "installed" }
elseif ($Pdf -or ((Read-Host "Install the small PDF reader so imported PDFs get their text? [y/N]") -match "^y")) {
    & $Py -m pip install --user --quiet pypdf
} else { Write-Host "skipped" }

Write-Host ""
Write-Host "Done. Your vault is at:" -ForegroundColor Green
Write-Host "  $Dest"
Write-Host ""
Write-Host "Next:" -ForegroundColor Yellow
Write-Host "  1. Open Obsidian. Click 'Open folder as vault' and choose that folder."
Write-Host "  2. Read Home and Readme inside it."
Write-Host "  3. With Claude: desktop app, Code tab, open that folder, and say:"
Write-Host "     'Read CLAUDE.md and Me.md, then help me fill in Me.md.'"
Write-Host "     With ChatGPT: see guides\prompts-for-any-ai.md in this repo."
