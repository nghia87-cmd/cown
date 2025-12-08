# ClamAV Setup Script for Windows
# Run as Administrator

Write-Host "Setting up ClamAV for Windows..." -ForegroundColor Green

# 1. Remove "Example" line from freshclam.conf
$freshclamConfig = "C:\Program Files\ClamAV\freshclam.conf"
if (Test-Path $freshclamConfig) {
    Write-Host "Configuring freshclam.conf..." -ForegroundColor Yellow
    (Get-Content $freshclamConfig) | Where-Object { $_ -notmatch '^Example' } | Set-Content $freshclamConfig
    
    # Add database directory if not exists
    if (-not (Select-String -Path $freshclamConfig -Pattern "^DatabaseDirectory" -Quiet)) {
        Add-Content $freshclamConfig "`nDatabaseDirectory C:\ProgramData\ClamAV\db"
    }
    
    Write-Host "✓ freshclam.conf configured" -ForegroundColor Green
}

# 2. Create database directory
$dbDir = "C:\ProgramData\ClamAV\db"
if (-not (Test-Path $dbDir)) {
    New-Item -ItemType Directory -Path $dbDir -Force | Out-Null
    Write-Host "✓ Created database directory: $dbDir" -ForegroundColor Green
}

# 3. Create clamd.conf (for daemon mode)
$clamdConfig = "C:\Program Files\ClamAV\clamd.conf"
if (Test-Path "C:\Program Files\ClamAV\conf_examples\clamd.conf.sample") {
    Copy-Item "C:\Program Files\ClamAV\conf_examples\clamd.conf.sample" $clamdConfig -Force
    (Get-Content $clamdConfig) | Where-Object { $_ -notmatch '^Example' } | Set-Content $clamdConfig
    
    # Configure for Windows
    $clamdSettings = @"

# Windows-specific settings
TCPSocket 3310
TCPAddr 127.0.0.1
DatabaseDirectory C:\ProgramData\ClamAV\db
LogFile C:\ProgramData\ClamAV\clamd.log
PidFile C:\ProgramData\ClamAV\clamd.pid
"@
    Add-Content $clamdConfig $clamdSettings
    Write-Host "✓ clamd.conf configured" -ForegroundColor Green
}

# 4. Update virus database
Write-Host "`nUpdating virus database (this may take a few minutes)..." -ForegroundColor Yellow
$env:Path += ";C:\Program Files\ClamAV"
& "C:\Program Files\ClamAV\freshclam.exe"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Virus database updated successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠ Database update had issues, but might still work" -ForegroundColor Yellow
}

# 5. Test ClamAV
Write-Host "`nTesting ClamAV installation..." -ForegroundColor Yellow
$testFile = [System.IO.Path]::GetTempFileName()
"X5O!P%@AP[4\PZX54(P^)7CC)7}`$"+"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!`$H+H*" | Out-File -FilePath $testFile -Encoding ASCII

& "C:\Program Files\ClamAV\clamscan.exe" $testFile

Remove-Item $testFile -Force

Write-Host "`n" -NoNewline
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ClamAV Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Install Python package: pip install pyclamd" -ForegroundColor White
Write-Host "2. Start ClamAV daemon: clamd.exe (in separate terminal)" -ForegroundColor White
Write-Host "3. Test with Django: FileSecurityScanner will auto-detect ClamAV" -ForegroundColor White
Write-Host "`nNote: For production, install ClamAV as Windows Service" -ForegroundColor Cyan
