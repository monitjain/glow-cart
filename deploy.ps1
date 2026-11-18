
$ErrorActionPreference = "Stop"

Write-Host "`n===== GLOW CART DEPLOYMENT =====" -ForegroundColor Cyan

# Confirm this is the project folder
if (-not (Test-Path "manage.py")) {
    Write-Host "ERROR: Open the terminal in your Glow Cart project folder." -ForegroundColor Red
    exit 1
}

# Confirm the current branch
$branch = git branch --show-current
if ($LASTEXITCODE -ne 0 -or $branch -ne "main") {
    Write-Host "ERROR: You must be on the main branch." -ForegroundColor Red
    exit 1
}

# Check Django before deployment
Write-Host "`nChecking Django project..." -ForegroundColor Yellow
python manage.py check
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Django check failed. Deployment cancelled." -ForegroundColor Red
    exit 1
}

# Stage only the intended project files
Write-Host "`nPreparing project files..." -ForegroundColor Yellow
git add -A -- .gitignore requirements.txt manage.py mysite store deploy.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Could not stage project files." -ForegroundColor Red
    exit 1
}

# Check staged changes
git diff --cached --check
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Please fix the reported formatting issues." -ForegroundColor Red
    exit 1
}

git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nNo new changes to deploy." -ForegroundColor Green
    exit 0
}

Write-Host "`nChanges ready for deployment:" -ForegroundColor Cyan
git diff --cached --stat

# Ask for confirmation
$confirmation = Read-Host "`nPush these changes to GitHub and trigger Render deployment? (Y/N)"
if ($confirmation -notmatch "^(Y|YES)$") {
    Write-Host "Deployment cancelled. Your changes remain local." -ForegroundColor Yellow
    exit 0
}

# Ask for commit message
$message = Read-Host "Enter a commit message (press Enter for default)"
if ([string]::IsNullOrWhiteSpace($message)) {
    $message = "Update Glow Cart website"
}

# Commit changes
git commit -m $message
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Commit failed." -ForegroundColor Red
    exit 1
}

# Push to GitHub
Write-Host "`nPushing to GitHub..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Push failed. Check your Git connection." -ForegroundColor Red
    exit 1
}

Write-Host "`nSUCCESS! Changes pushed to GitHub." -ForegroundColor Green
Write-Host "Render should now start its automatic deployment." -ForegroundColor Green
