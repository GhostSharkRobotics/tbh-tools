# TBH MarketLens — Windows ビルド (PyInstaller / onedir / アイコン付き)
# 使い方: Windows実機の配備先 (C:\Users\monoq\tbh-price-ocr\) で  powershell -ExecutionPolicy Bypass -File build-marketlens.ps1
# 出力: dist\TBH MarketLens\TBH MarketLens.exe （配布はこのフォルダごとzip）
# 注意: 公開(GitHub Releases)はユーザーの明示確認後のみ。ビルド自体はいつでも可。
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 同梱が必要な読み取り専用アセット（コードが RES から読む。HERE側=履歴/設定/ログは書き込み用で同梱しない）
pyinstaller --noconfirm --clean --onedir --windowed `
  --name "TBH MarketLens" `
  --icon marketlens.ico `
  --add-data "tbh-price-lookup.json;." `
  --add-data "frame_tpl.png;." `
  --add-data "marketlens.ico;." `
  --add-data "marketlens.png;." `
  --collect-all winocr `
  --collect-all winsdk `
  tbh-price-ocr.py

Write-Host "`n完成 -> dist\TBH MarketLens\  (TBH MarketLens.exe)"
Write-Host "配布: このフォルダを zip。SmartScreenは未署名のため『詳細->実行』案内をREADMEに記載済み。"
