#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tbh-price-ocr.py  —  ゲーム内アイテムの相場を「ホットキー1発」で表示する常駐ヘルパー
（ゲームには一切触れない＝メモリ読み/注入なし＝アンチチート監視外。Claude/API/課金も不使用）

しくみ:
  ホットキー → カーソル周辺の小ボックスだけスクショ → Windows内蔵OCR
  → 既知名へ曖昧スナップ(tbh_price_match) → カーソル横に価格をポップ表示

★ Windows専用（ゲームが動くPCで実行）。全画面は撮らずカーソル周辺の小領域のみ。

セットアップ（ゲームPC側 / 1回だけ）:
  1) Python 3.10+ を入れる
  2) pip install mss pillow winocr keyboard
  3) 日本語表示で遊ぶなら Windows設定 > 時刻と言語 > 言語 で「日本語」のOCRが入っていること
     （日本語版Windowsなら通常入っている）
  4) tbh-price-lookup.json をこのスクリプトと同じ場所に置く
     （Mac側で `python3 tools/tbh-build-price-lookup.py` を実行すると最新版が生成される）

使い方:
  python tbh-price-ocr.py
  → ゲームでアイテムにカーソルを合わせ、Ctrl+Shift+P を押す → 価格がポップ
  → 撮影範囲がズレてたら CALIBRATE（下の設定）で確認・調整
  終了: Ctrl+Shift+Q
"""
import os, sys, json, threading, tkinter as tk

# ---- 設定 -------------------------------------------------------------
HOTKEY        = "ctrl+shift+p"     # 価格を出すキー
QUIT_KEY      = "ctrl+shift+q"     # 終了キー
# カーソルを基準にした撮影ボックス(px)。全画面は撮らない。ツールチップが収まるよう少し広め。
BOX_LEFT      = -60                # カーソルから左へ
BOX_RIGHT     = 460               # 右へ
BOX_UP        = -40                # 上へ
BOX_DOWN      = 300               # 下へ
OCR_LANGS     = ["ja", "en"]      # 試すOCR言語（上から順に良い方を採用）
POPUP_SECONDS = 6                  # ポップの表示秒数
CALIBRATE     = False              # Trueにすると撮影画像を tbh-ocr-capture.png に保存（範囲確認用）
# ---------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tbh_price_match import Matcher  # noqa

try:
    import mss
    from PIL import Image
    import winocr
    import keyboard
except ImportError as e:
    print("依存が不足:", e)
    print("→ pip install mss pillow winocr keyboard を実行してください")
    sys.exit(1)

LOOKUP = os.path.join(HERE, "tbh-price-lookup.json")
if not os.path.exists(LOOKUP):
    print("tbh-price-lookup.json が見つかりません。Mac側で tools/tbh-build-price-lookup.py を実行して生成し、ここに置いてください。")
    sys.exit(1)
matcher = Matcher(LOOKUP)


def cents(c):
    return "-" if c is None else f"${c/100:.2f}"


def grab_box():
    """カーソル周辺の小領域をPIL画像で返す。"""
    import ctypes
    from ctypes import wintypes
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    cx, cy = pt.x, pt.y
    region = {"left": cx + BOX_LEFT, "top": cy + BOX_UP,
              "width": BOX_RIGHT - BOX_LEFT, "height": BOX_DOWN - BOX_UP}
    with mss.mss() as sct:
        raw = sct.grab(region)
    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    if CALIBRATE:
        img.save(os.path.join(HERE, "tbh-ocr-capture.png"))
        print("撮影範囲を tbh-ocr-capture.png に保存しました（範囲確認用）")
    return img, (cx, cy)


def ocr(img):
    """複数言語でOCRし、最も文字数の多い結果を返す。"""
    best = ""
    for lang in OCR_LANGS:
        try:
            r = winocr.recognize_pil(img, lang)
            t = r.text if hasattr(r, "text") else str(r)
        except Exception:
            t = ""
        if len(t) > len(best):
            best = t
    return best


# ---- ポップ表示（tkinter, 最前面・枠なし） ----------------------------
_root = None
def _ensure_root():
    global _root
    if _root is None:
        _root = tk.Tk(); _root.withdraw()
    return _root

def show_popup(lines, xy):
    root = _ensure_root()
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    try: win.attributes("-alpha", 0.95)
    except Exception: pass
    frame = tk.Frame(win, bg="#1b1b1f", bd=1, relief="solid")
    frame.pack()
    for i, (txt, color, big) in enumerate(lines):
        tk.Label(frame, text=txt, bg="#1b1b1f", fg=color,
                 font=("Yu Gothic UI", 13 if big else 10, "bold" if big else "normal"),
                 anchor="w", justify="left", padx=10, pady=(6 if i == 0 else 1)).pack(fill="x")
    x = min(xy[0] + 24, win.winfo_screenwidth() - 360)
    y = min(xy[1] + 24, win.winfo_screenheight() - 160)
    win.geometry(f"+{x}+{y}")
    win.after(int(POPUP_SECONDS * 1000), win.destroy)


def handle():
    try:
        img, xy = grab_box()
        text = ocr(img)
        results = matcher.match(text)
        if not results:
            snippet = (text or "").strip().replace("\n", " ")[:30]
            show_popup([("該当なし", "#ff6b6b", True),
                        (f"読取: {snippet or '(空)'}", "#aaaaaa", False)], xy)
            return
        e = results[0]
        name = e["base_en"] + (f" [{e['variant']}]" if e["variant"] else "")
        lines = [(name, "#ffffff", True)]
        if e.get("ja"): lines.append((e["ja"], "#9ecbff", False))
        lines.append((f"最安 {cents(e['sell'])}   中央値 {cents(e['median'])}", "#7CFC7C", True))
        lines.append((f"{e.get('type','')}   出品{e.get('listings','-')} / 売買{e.get('volume','-')}",
                      "#aaaaaa", False))
        lines.append((f"相場: {matcher.marketUpdated or '-'}", "#777777", False))
        show_popup(lines, xy)
    except Exception as ex:
        print("エラー:", ex)


def main():
    print(f"TBH 相場OCR 起動。{HOTKEY} で価格表示 / {QUIT_KEY} で終了。")
    print(f"相場データ: {matcher.marketUpdated}")
    keyboard.add_hotkey(HOTKEY, lambda: threading.Thread(target=handle, daemon=True).start())
    keyboard.add_hotkey(QUIT_KEY, lambda: (print("終了"), os._exit(0)))
    # tkはメインスレッドで回す
    root = _ensure_root()
    root.mainloop()


if __name__ == "__main__":
    main()
