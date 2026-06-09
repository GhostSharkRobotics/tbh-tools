# TBH MarketLens

**Point at an item in _TBH: Task Bar Hero_, press a key, and see its Steam Community Market price instantly — no name‑typing, no searching.**

Made by **Ghost Shark Robotics**.

> ⚠️ **Unofficial, fan-made tool** — not affiliated with, endorsed by, or connected to the game's developer or Valve/Steam. Provided **"as is," without warranty.** Prices come from the Steam Community Market and **may be inaccurate, delayed, or wrong** (non-USD = currency-converted estimate); they are **not financial or trading advice** — confirm on the Steam Market before you buy or sell. **You use this entirely at your own risk; the author accepts no liability for any loss or damage (including from trades) arising from its use.**

---

## What it does

- **Hover an item in-game → press your hotkey → a small overlay shows its current Steam Market price** (lowest listing + median), fetched when you ask. Prices are from the Steam Community Market (USD; JPY/CNY are shown as a currency-converted estimate).
- Reads the item **right under your cursor** by looking at the screen (OCR) and matching it to the game's item database — equipment, gems, engravings, materials and more — with item names, rarity and type in **Japanese, English or Chinese (中文)**.
- **Price history** window you can toggle from the tray: favourite items, rename / fix mis-reads, change rarity, delete, and **update all prices** at once. History is saved between sessions.
- Fully configurable trigger: default is the **mouse side (back) button**, but you can bind **any key or combo** (e.g. `Ctrl+Shift+P`) in Settings.
- UI in **日本語 / English / 中文** (auto-detected from your PC language on first run, switchable in Settings).

## Is it safe? (anti-cheat)

Yes. MarketLens **only reads what's already on your screen.** It takes an ordinary screenshot (the standard Windows screen capture — the same as any screenshot app), recognizes the item name with OCR, and looks its price up on Steam. It runs as a separate program and **never reads or modifies the game's memory**, so the game's anti-cheat does **not** flag it as a cheat.

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

> **Reading non-English text:** the OCR uses Windows' built-in recognizer (bundled — nothing extra to install). It only needs the **Windows language pack for the text you're reading**, which you already have if your Windows / the game runs in that language. If a language is missing, MarketLens tells you and links to the setting to add it.

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

_TBH: Task Bar Hero_ のアイテムにカーソルを当てて**キーを押すと、Steamマーケットの現在価格がその場で表示**されます（名前を打って検索する手間なし）。

- **非公式のファン制作ツール**（ゲーム開発元・Valve/Steam とは無関係）。**現状のまま・無保証**で提供します。価格は不正確・遅延の可能性があり**取引助言ではありません**。**利用は自己責任**で、生じた損害について作者は責任を負いません。
- **ゲームには一切干渉しません**。Windows 標準の画面キャプチャ（スクショと同じ）で画面を読み、Steam で価格を調べるだけ。**ゲームのメモリを読み書きしない**ので、アンチチートに**チートとして検出されません**。
- **匿名の利用統計**を送ります（起動・参照したアイテム名・エラー報告。ランダムIDのみ）。**IP・Steam在庫・個人情報は一切送りません**。「設定 → 利用統計」でいつでもオフにできます。
- 価格履歴（お気に入り・名前/レア度修正・一括更新・永続保存）、発動キー自由割り当て、**日本語/英語/中国語UI**（初回はPCの言語を自動取得）。価格はSteamマーケット（USD基準。円・元は為替換算の概算）。

**導入**：zipを展開し、フォルダごと置いて `TBH MarketLens.exe` を実行（タスクトレイ常駐）。未署名のためSmartScreen警告は「詳細→実行」。

**更新**：起動時に新版を確認し、あれば**トレイ／設定に「⬆ 更新」**が出ます。**1クリックでDL→差し替え→自動再起動**（手動の再DL・再展開は不要）。

☕ 応援（任意）：[Ko-fi](https://ko-fi.com/ghostsharkrobotics)

---

### 中文（简介）

在 _TBH: Task Bar Hero_ 中把鼠标光标对准物品并**按下快捷键，即可当场显示该物品的 Steam 市场价格**（无需输入名称搜索）。

- **非官方粉丝制作工具**（与游戏开发商及 Valve/Steam 无关联）。按**「现状」提供、无任何担保**。价格可能不准确或有延迟，**不构成交易建议**。**使用风险自负**，作者对由此产生的损失概不负责。
- **完全不干预游戏**：用 Windows 标准截屏（和普通截图一样）读取画面，再到 Steam 查询价格。**不读取或修改游戏内存**，因此**不会被反作弊判定为作弊**。
- **匿名使用统计**（启动、查询的物品名、错误报告，仅关联随机ID）。**绝不发送 IP、Steam 库存或个人信息**。可在「设置 → 使用统计」随时关闭。
- 价格历史（收藏・名称/稀有度修正・一键全部更新・永久保存），触发键可自由设置，**中文/英文/日文界面**（首次按电脑语言自动选择）。价格来自 Steam 市场（以 USD 为准；人民币/日元为按汇率换算的估算值）。
- 文字识别用 Windows 自带 OCR（已内置，无需额外安装），只需系统装有所读语言的语言包（通常你的系统/游戏已是该语言）。若缺少，程序会提示并引导你去添加。

**安装**：解压后将整个文件夹放在任意位置，运行 `TBH MarketLens.exe`（常驻系统托盘）。未签名，故 SmartScreen 提示时点「更多信息 → 仍要运行」。

**更新**：启动时检查新版本，有则在**托盘／设置显示「⬆ 更新」**，**一键下载→替换→自动重启**（无需手动重新下载解压）。

☕ 赞助（可选）：[Ko-fi](https://ko-fi.com/ghostsharkrobotics)
