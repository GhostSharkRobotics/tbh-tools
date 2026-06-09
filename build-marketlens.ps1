# TBH MarketLens - Windows build (PyInstaller / onedir / with icon)
# Run on the Windows box in the deploy dir (C:\Users\monoq\tbh-price-ocr\):
#   powershell -ExecutionPolicy Bypass -File build-marketlens.ps1
# Output: dist\TBH MarketLens\TBH MarketLens.exe  (distribute the whole folder as a zip)
# NOTE: keep this script ASCII-only. Japanese text breaks parsing on a CP932 Windows shell.
# NOTE: publishing (GitHub Releases) only after explicit user confirmation. Building is fine anytime.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Pass args as an array (backtick line-continuation can silently drop a line).
# Bundle the read-only assets the code reads from RES. (history/settings/log live next to the exe = HERE, not bundled)
$pyiArgs = @(
  '--noconfirm', '--clean', '--onedir', '--windowed',
  '--name', 'TBH MarketLens',
  '--icon', 'marketlens.ico',
  '--add-data', 'tbh-price-lookup.json;.',
  '--add-data', 'frame_tpl.png;.',
  '--add-data', 'marketlens.ico;.',
  '--add-data', 'marketlens.png;.',
  '--collect-all', 'winocr',
  '--collect-all', 'winsdk',
  'tbh-price-ocr.py'
)
pyinstaller @pyiArgs

Write-Host ""
Write-Host "Done -> dist\TBH MarketLens\  (TBH MarketLens.exe)"
Write-Host "Distribute: zip that folder. Unsigned, so SmartScreen needs 'More info -> Run anyway' (noted in README)."
