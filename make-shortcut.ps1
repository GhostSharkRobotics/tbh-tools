$desktop = [Environment]::GetFolderPath('Desktop')
$dir = Join-Path $env:USERPROFILE 'tbh-price-ocr'
$lnk = Join-Path $desktop 'TBH-Price.lnk'
$sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$sc.TargetPath = Join-Path $dir 'start-tbh-price.bat'
$sc.WorkingDirectory = $dir
$sc.IconLocation = 'shell32.dll,77'
$sc.Save()
Write-Host ("SHORTCUT_OK=" + (Test-Path $lnk))
