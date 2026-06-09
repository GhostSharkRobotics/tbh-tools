# TBH MarketLens

**Point at an item in _TBH: Task Bar Hero_, press a key, and see its Steam Community Market price instantly — no typing, no alt-tab.**

Made by **Ghost Shark Robotics**.

> ⚠️ **Unofficial fan-made tool.** Not affiliated with, endorsed by, or connected to Nugem Studio or Valve. Use at your own discretion.

---

## What it does

- **Hover an item in-game → press your hotkey → a small overlay shows its current Steam Market price** (lowest listing + median), pulled live when you ask.
- Reads the item **right under your cursor** by looking at the screen (OCR) and matching it to the game's item database — equipment, gems, engravings, materials and more, in **Japanese or English**.
- **Price history** window you can toggle from the tray: favourite items, rename / fix mis-reads, change rarity, delete, and **update all prices** at once. History is saved between sessions.
- Fully configurable trigger: default is the **mouse side (back) button**, but you can bind **any key or combo** (e.g. `Ctrl+Shift+P`) in Settings.
- UI in **日本語 / English** (auto-detected from your PC language on first run, switchable in Settings).

## Is it safe? (anti-cheat)

Yes. MarketLens runs as a **completely separate program**. It only:
- takes a screenshot of **its own / the desktop screen** and reads text from it,
- listens for **your chosen hotkey**, and
- asks **Steam's public price API** for the price.

It **never reads or writes the game's memory, never injects anything, and never touches the game process.** There is no speed/time manipulation. It does not interact with the game at all, so it does not trigger the game's cheat detection.

### Privacy

To help improve the tool, MarketLens sends **anonymous usage stats**: app launches, the names of items you look up, and error reports — tied only to a random ID, not to you. **It never sends your IP, your Steam inventory, or any personal data.** You can turn this off anytime in **Settings → Usage stats**.

## Install

1. Download `TBH-MarketLens-vX.Y.zip` from the [Releases](https://github.com/GhostSharkRobotics/tbh-marketlens/releases) page.
2. **Extract the whole folder** anywhere (e.g. your Desktop). Keep the files together.
3. Run **`TBH MarketLens.exe`**. It lives in the **system tray** (no window until you trigger it).

**Windows SmartScreen** may show "Windows protected your PC" because the app is unsigned → click **More info → Run anyway**. Some antivirus may flag it (a false positive common to keyboard-hotkey apps built with PyInstaller); allow it if you trust the source.

## How to use

- Make sure **TBH: Task Bar Hero is the focused window**, hover an item, and press your trigger (default: **mouse side/back button**).
- The price popup appears next to your cursor. It closes when you click elsewhere, move away, or press **Esc**.
- **🕘 History** button on the popup, or **tray → History**, opens the list. Right-click any row for **Favourite / Rename / Rarity / Delete**.
- **Tray → Settings**: change language, rebind the trigger, set the history limit.

## Updates

MarketLens checks for a newer version on startup. When one is available, a **"⬆ Update"** entry appears in the tray menu (and Settings) — **one click downloads it, swaps the files, and restarts itself.** No manual re-download or re-extract.

## Support

If it saves you time, you can leave a small tip — entirely optional, no nagging:

☕ **[Support on Ko-fi](https://ko-fi.com/ghostsharkrobotics)**

## Credits & licence

- Item data is extracted from the game for matching purposes only.
- © Ghost Shark Robotics. Free to use. Provided "as is", without warranty.

---

### 日本語（概要）

_TBH: Task Bar Hero_ のアイテムにカーソルを当てて**キーを押すと、Steamマーケットの現在価格がその場で表示**されます（タイピング・Alt+Tab不要）。

- **非公式のファンメイドツール**（Nugem Studio / Valve とは無関係）。
- **ゲームには一切干渉しません**（自分の画面OCR＋ホットキー＋Steamの公開価格APIのみ）。メモリ改変・注入・速度操作なし＝**アンチチート非検出**。
- **匿名の利用統計**を送ります（起動・参照したアイテム名・エラー報告。ランダムIDのみ）。**IP・Steam在庫・個人情報は一切送りません**。「設定 → 利用統計」でいつでもオフにできます。
- 価格履歴（お気に入り・名前/レア度修正・一括更新・永続保存）、発動キー自由割り当て、日本語/英語UI（初回はPCの言語を自動取得）。

**導入**：zipを展開し、フォルダごと置いて `TBH MarketLens.exe` を実行（タスクトレイ常駐）。未署名のためSmartScreen警告は「詳細→実行」。

**更新**：起動時に新版を確認し、あれば**トレイ／設定に「⬆ 更新」**が出ます。**1クリックでDL→差し替え→自動再起動**（手動の再DL・再展開は不要）。

☕ 応援（任意）：[Ko-fi](https://ko-fi.com/ghostsharkrobotics)
