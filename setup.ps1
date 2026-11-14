# One-time local setup for Windows. Run from the repo root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# VS Code and GitHub config ship in _setup/ and are moved into place here.
if (Test-Path "$root\_setup") {
    Write-Host "==> Moving VS Code and GitHub Actions config into place"
    New-Item -ItemType Directory -Force "$root\.vscode", "$root\.github\workflows" | Out-Null
    Copy-Item "$root\_setup\vscode\*" "$root\.vscode\" -Force
    Copy-Item "$root\_setup\github\workflows\*" "$root\.github\workflows\" -Force
    Remove-Item "$root\_setup" -Recurse -Force
}

Write-Host "==> API: creating virtual environment and installing dependencies"
Push-Location "$root\apps\api"
if (-not (Test-Path ".venv")) { python -m venv .venv }
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
if (-not (Test-Path ".env")) { Copy-Item .env.example .env }
.\.venv\Scripts\python -m pytest -q
Pop-Location

Write-Host "==> Web: installing npm packages"
Push-Location "$root\apps\web"
npm install
if (-not (Test-Path ".env.local")) { Copy-Item .env.example .env.local }
Pop-Location

Write-Host "==> Git: initialising repository"
Push-Location $root
if (-not (Test-Path ".git")) {
    git init -b main
    git add .
    git commit -m "Initial scaffold: Next.js web, FastAPI api, Supabase schema, tax profiles"
} else {
    Write-Host "Git repo already exists, skipping."
}
Pop-Location

Write-Host ""
Write-Host "Done. Open the folder in VS Code with:  code ."
Write-Host "Then run the 'Full stack' launch config (F5) to start both servers."
