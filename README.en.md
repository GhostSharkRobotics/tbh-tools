<!-- 言語 / Language -->
[日本語](README.md) · **English** · [中文](README.zh.md)

# TBH Tools — Unofficial Task Bar Hero tools

Free tools for **Task Bar Hero** players. Two kinds:
**Web tools** that run in your browser (nothing to install) and a Windows app, **MarketLens**, that shows item prices in‑game instantly.

---

## 🌐 Web tools — no install, just click a link

### ▶ Hub page: **https://ghostsharkrobotics.github.io/tbh-tools/**

No download needed. Bookmark it and use it on any device. Open any tool directly:

| Tool | What it does |
|---|---|
| [🏆 Best Build Maker](https://ghostsharkrobotics.github.io/tbh-tools/tbh-best-build.html) | Pick gear / gems / engravings / inscriptions per slot and it computes DPS. The **"Best"** button brute‑forces every class × every item to auto‑set the highest‑DPS build. |
| [🔍 Item Search](https://ghostsharkrobotics.github.io/tbh-tools/tbh-gem-search.html) | Search equipment, gems, engravings, inscriptions and unique stats **by effect or name**. With market prices, EN/JP, sortable. |
| [💰 Deals Finder](https://ghostsharkrobotics.github.io/tbh-tools/tbh-deals.html) | Ranks market gear by "power ÷ current lowest price" to surface underpriced listings. Direct links to the Steam Market. |
| [🧱 Crafting](https://ghostsharkrobotics.github.io/tbh-tools/tbh-crafting.html) | Crafting (cube) recipes and required materials, by tier and slot. Each material is price‑tagged and linked. |
| [📦 Stage Drops](https://ghostsharkrobotics.github.io/tbh-tools/tbh-stage-drops.html) | Which chest on which stage drops what, with probabilities. Reverse lookup: "where do I farm this?" |
| [⚡ EXP Farm](https://ghostsharkrobotics.github.io/tbh-tools/tbh-exp.html) | Ranks stages by over‑level‑adjusted EXP from your hero level. Enter a clear time to sort by EXP/hour. |
| [🛠 Build Simulator](https://ghostsharkrobotics.github.io/tbh-tools/tbh-build-simulator.html) | Compute DPS from gear, gems and buffs. |
| [📊 DPS Calculator](https://ghostsharkrobotics.github.io/tbh-tools/tbh-dps.html) | Simple DPS calculation. |
| [📖 Specs](https://ghostsharkrobotics.github.io/tbh-tools/tbh-info.html) | Synthesis/craft output types and odds, DLC conditions, chest drop rates. |

Price data is refreshed daily by GitHub Actions.

---

## 🖥 TBH MarketLens (Windows app)

In‑game, **hover an item and press a key** — a small card shows its Steam Market price (lowest + median). No name‑typing, no searching. UI in 日本語 / English / 中文.

### ⬇ How to download (for people new to GitHub)

1. Open the download page → **[📥 Releases](https://github.com/GhostSharkRobotics/tbh-marketlens/releases)**
2. Under the latest version's **"Assets"**, click the **`.zip`** file (it starts with `TBH-MarketLens`) to download
3. **Right‑click the zip → Extract All**
4. Double‑click **`TBH MarketLens.exe`** in the extracted folder

> 💡 If Windows shows **"Windows protected your PC,"** click **More info → Run anyway** (it appears because the app is unsigned — this is fine).

It lives in your system tray (near the clock). A how‑to shows on first run. Change the hotkey or language in **Tray → Settings** (default hotkey is the mouse **back/side** button).

### Is it safe? (anti‑cheat)

Yes. MarketLens **only reads what's already on your screen.** It takes an ordinary screenshot (the standard Windows screen capture — the same as any screenshot app), recognizes the item name with OCR, and looks its price up on Steam. It runs as a separate program and **never reads or modifies the game's memory**, so the game's anti-cheat does **not** flag it as a cheat. Details: [dist-README.md](dist-README.md).

---

## For developers

- Web tools are **self‑contained HTML** with data embedded (work offline); generated from `tbh-data.json` etc. by build scripts.
- MarketLens source is `tbh-price-ocr.py`; the distributed build lives in the separate [tbh-marketlens](https://github.com/GhostSharkRobotics/tbh-marketlens) repo's Releases.
- Prices auto‑update daily via GitHub Actions.

---

## Disclaimer

Unofficial, fan‑made tool — **not affiliated with, endorsed by, or connected to the game's developer or Valve/Steam.** Provided **"as is," without warranty of any kind.**

Prices come from the Steam Community Market and **may be inaccurate, delayed, or wrong** (non‑USD prices are currency‑converted estimates). They are **not trading or financial advice** — always confirm on the Steam Market before you buy or sell. **You use these tools entirely at your own risk; the author accepts no liability for any loss or damage (including from trades, purchases, or sales) arising from their use.**

*by **Ghost Shark Robotics** · optional tip: [☕ Ko-fi](https://ko-fi.com/ghostsharkrobotics)*
