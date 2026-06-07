# TBH 相場OCR — Windowsブートストラップ（自己更新）
# 使い方（PowerShellに貼るだけ。初回も2回目以降も同じ）:
#   irm https://raw.githubusercontent.com/monocro/tbh-tools/main/tbh-price-ocr.ps1 | iex
# 実行中: Ctrl+Shift+P で価格表示 / Ctrl+Shift+Q で終了
$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/monocro/tbh-tools/main"
$dir  = Join-Path $env:LOCALAPPDATA "tbh-price-ocr"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

# --- Python を探す ---
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) {
  Write-Host "Python が見つかりません。https://www.python.org/downloads/ から入れてください（インストール時『Add python.exe to PATH』にチェック）。" -ForegroundColor Yellow
  return
}
$python = $py.Source

# --- 依存（不足時のみ入れる） ---
& $python -c "import mss,PIL,winocr,keyboard" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "初回セットアップ: 依存ライブラリをインストール中…" -ForegroundColor Cyan
  & $python -m pip install --quiet --disable-pip-version-check mss pillow winocr keyboard
}

# --- 最新ファイルを取得（毎回＝自己更新） ---
$files = @{
  "tbh-price-ocr.py"      = "tbh-price-ocr.py"
  "tbh_price_match.py"    = "tbh_price_match.py"
  "tbh-price-lookup.json" = "tbh-price-lookup.json"
}
foreach ($src in $files.Keys) {
  Invoke-WebRequest -Uri "$base/$src" -OutFile (Join-Path $dir $files[$src]) -UseBasicParsing
}

# --- 起動 ---
Write-Host "TBH 相場OCR 起動。ゲームでアイテムにカーソル→ Ctrl+Shift+P。終了は Ctrl+Shift+Q。" -ForegroundColor Green
& $python (Join-Path $dir "tbh-price-ocr.py")
