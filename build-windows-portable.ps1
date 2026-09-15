$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python launcher 'py' is required." }
$Venv = Join-Path $Root ".venv-build"
if (Test-Path $Venv) { Remove-Item -Recurse -Force $Venv }
py -3 -m venv $Venv
$Python = Join-Path $Venv "Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install pyinstaller pillow
& $Python -m PyInstaller --noconfirm --clean --onefile --windowed --name "ImagePrivacyCleaner" --collect-all PIL windows_app.py
Write-Host "Built: $Root\dist\ImagePrivacyCleaner.exe"
Write-Host "Before sale: regression test, metadata verification, malware scan, Authenticode sign, and publish SHA256."
