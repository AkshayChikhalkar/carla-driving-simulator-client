# PowerShell script for publishing package

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "[INFO] Starting release process..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if version argument is provided
if ($args.Count -eq 0) {
    Write-Host "[ERROR] Please provide a version number (e.g., .\publish.ps1 1.0.1)" -ForegroundColor Red
    exit 1
}

$NEW_VERSION = $args[0]
Write-Host "[INFO] Version to release: $NEW_VERSION" -ForegroundColor Cyan
Write-Host ""

# Validate version format (x.y.z)
if (-not ($NEW_VERSION -match '^\d+\.\d+\.\d+$')) {
    Write-Host "[ERROR] Invalid version format. Please use x.y.z format (e.g., 1.0.1)" -ForegroundColor Red
    exit 1
}
Write-Host "[INFO] Version format is valid" -ForegroundColor Green
Write-Host ""

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Host "[INFO] Git is installed: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] git is not installed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check if twine is installed
try {
    $twineVersion = pip show twine
    Write-Host "[INFO] Twine is installed:" -ForegroundColor Green
    Write-Host $twineVersion
} catch {
    Write-Host "[WARNING] twine is not installed. Installing..." -ForegroundColor Yellow
    pip install twine
    Write-Host "[INFO] Twine installation completed" -ForegroundColor Green
}
Write-Host ""

# Check if build is installed
try {
    $buildVersion = pip show build
    Write-Host "[INFO] Build is installed:" -ForegroundColor Green
    Write-Host $buildVersion
} catch {
    Write-Host "[WARNING] build is not installed. Installing..." -ForegroundColor Yellow
    pip install build
    Write-Host "[INFO] Build installation completed" -ForegroundColor Green
}
Write-Host ""

# Check if we're in a git repository
try {
    $gitStatus = git status
    Write-Host "[INFO] Git repository status:" -ForegroundColor Green
    Write-Host $gitStatus
} catch {
    Write-Host "[ERROR] Not a git repository" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check for uncommitted changes
$gitDiff = git diff --name-only
if ($gitDiff) {
    Write-Host "[WARNING] You have uncommitted changes:" -ForegroundColor Yellow
    Write-Host $gitDiff
    Write-Host "Please commit or stash them first." -ForegroundColor Yellow
    exit 1
}
Write-Host "[INFO] No uncommitted changes found" -ForegroundColor Green
Write-Host ""

# Update VERSION file
Write-Host "[INFO] Updating VERSION file to $NEW_VERSION" -ForegroundColor Cyan
Set-Content -Path "VERSION" -Value $NEW_VERSION
Write-Host "[INFO] VERSION file contents:" -ForegroundColor Green
Get-Content "VERSION"
Write-Host ""

# Commit version change
Write-Host "[INFO] Committing version change..." -ForegroundColor Cyan
git add VERSION
git commit -m "Bump version to $NEW_VERSION"
Write-Host "[INFO] Version change committed" -ForegroundColor Green
Write-Host ""

# Create git tag
Write-Host "[INFO] Creating git tag v$NEW_VERSION..." -ForegroundColor Cyan
git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"
Write-Host "[INFO] Git tag created:" -ForegroundColor Green
git tag -l "v$NEW_VERSION"
Write-Host ""

# Build package
Write-Host "[INFO] Building package..." -ForegroundColor Cyan
python -m build
Write-Host "[INFO] Package build completed. Contents of dist directory:" -ForegroundColor Green
Get-ChildItem -Path "dist"
Write-Host ""

# Upload to PyPI
Write-Host "[INFO] Uploading to PyPI..." -ForegroundColor Cyan
twine upload dist/*
Write-Host "[INFO] Upload to PyPI completed" -ForegroundColor Green
Write-Host ""

# Push changes and tag to remote
Write-Host "[INFO] Pushing changes and tag to remote..." -ForegroundColor Cyan
git push origin master
git push origin "v$NEW_VERSION"
Write-Host "[INFO] Changes and tag pushed to remote" -ForegroundColor Green
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "[INFO] Release $NEW_VERSION completed successfully!" -ForegroundColor Green
Write-Host "[INFO] Don't forget to create a release on GitHub with release notes." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 