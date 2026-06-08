#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tbh-price-ocr.py — ゲーム内アイテムの相場をホットキーで表示する常駐ヘルパー

★チート検出されない設計（毎回維持すること）:
  - ゲームプロセスに一切触れない。メモリ読み書き/DLL注入/速度・時計操作を行わない。
  - やるのは「自分の画面の小領域スクショ」+「OCR」+「ホットキー待ち」だけ＝別プロセスで完結。
  - TBHのACTk検出器(ObscuredCheating/SpeedHack/TimeCheat)はどれもゲーム内部の事象しか見ない。
    本ツールはその検出面に一切触れないため、原理的に検出対象外。
  - 軽量・ホットキー押下時のみ稼働＝ゲームをフレーム飢餓させずスピードハック誤検出も誘発しない。

見た目: コンソール無し(pythonw)・タスクトレイ常駐・カード型ポップ。
操作  : アイテムにカーソル→ マウスの「戻る」サイドボタン で価格ポップ / 終了はトレイから
        ※TaskBarHero.exe が前面の時だけ反応。ブラウザ等での「戻る」は普通に効く。
"""
import os, sys, json, threading, queue, traceback, time, webbrowser, urllib.parse
import tkinter as tk
from tkinter import font as tkfont

# ---- 設定 ----------------------------------------------------------------
SIDE_BUTTON   = "x"                # マウスの「戻る」(XBUTTON1)。効かなければ "x2" に変更
GAME_EXE      = "taskbarhero.exe"  # この実行ファイルが前面の時だけ反応
APPID         = "3678970"          # TBH の Steam appid（マーケットURL用）
# 名前枠は位置が毎回変わる→上部ウィンドウ全体を撮り、OCRを行単位＋隣接行ペアで照合して
# どこにあっても名前＋等級を拾う。(左, 上, 右, 下) のゲームウィンドウ比率。
NAME_REGIONS = [
    (0.0, 0.0, 1.0, 0.62),
]
OCR_LANGS     = ["ja", "en"]
POPUP_SECONDS = 6
CALIBRATE     = True               # Trueで撮影画像を tbh-ocr-capture.png に保存（調整用・一時ON）
# 配色
C_CARD, C_ACCENT = "#1a1d24", "#2dd4bf"
C_NAME, C_JA, C_PRICE, C_META, C_ERR = "#ffffff", "#8ab4f8", "#34d399", "#8b909a", "#f87171"
# -------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LOG = os.path.join(HERE, "error.log")


def log_fatal(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


# ---- 依存 ----------------------------------------------------------------
try:
    import mss
    from PIL import Image, ImageDraw
    from PIL import ImageOps
    import winocr
    import mouse
    import pystray
    from tbh_price_match import Matcher
except Exception as e:
    log_fatal("import error:\n" + traceback.format_exc())
    try:
        import tkinter.messagebox as mb
        r = tk.Tk(); r.withdraw()
        mb.showerror("TBH相場OCR", f"必要なライブラリが不足:\n{e}\n\npip install mss pillow winocr mouse pystray")
    except Exception:
        pass
    sys.exit(1)

matcher = Matcher(os.path.join(HERE, "tbh-price-lookup.json"))
PQ = queue.Queue()          # ポップ要求キュー（別スレッド→メインスレッド）


JPY_RATE = 155.0     # USD→JPY。起動時に最新レートへ更新（失敗時はこの値）

def fetch_rate():
    global JPY_RATE
    try:
        import urllib.request
        with urllib.request.urlopen("https://open.er-api.com/v6/latest/USD", timeout=5) as r:
            JPY_RATE = float(json.load(r)["rates"]["JPY"])
    except Exception:
        pass

def yen(c):
    return "—" if c is None else f"¥{round(c / 100 * JPY_RATE):,}"


# ---- 前面ウィンドウ判定（ゲームが前面の時だけ反応） ----------------------
def foreground_exe():
    import ctypes
    from ctypes import wintypes
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not h:
            return ""
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        ctypes.windll.kernel32.CloseHandle(h)
        return os.path.basename(buf.value).lower()
    except Exception:
        return ""


# ---- 撮影 & OCR ----------------------------------------------------------
def cursor_pos():
    import ctypes
    from ctypes import wintypes
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def grab(frac):
    """ゲームウィンドウ基準で frac=(左,上,右,下)比率の領域を撮る。戻り: (画像, (画面左, 画面上))。"""
    import ctypes
    from ctypes import wintypes
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    r = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
    W, H = r.right - r.left, r.bottom - r.top
    x0, y0, x1, y1 = frac
    left, top = r.left + int(W * x0), r.top + int(H * y0)
    region = {"left": left, "top": top,
              "width": max(1, int(W * (x1 - x0))), "height": max(1, int(H * (y1 - y0)))}
    with mss.mss() as sct:
        raw = sct.grab(region)
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX"), (left, top)


def preprocess(img):
    """色付き文字対策: 明度(V=max(R,G,B))チャンネル＋コントラスト強調。
    マゼンタ/オレンジ等のレア色名でも白黒高コントラストになりOCRが安定。小領域のみ拡大。"""
    v = img.convert("HSV").split()[2]
    w, h = v.size
    if w < 700:                      # 小さい領域だけ拡大（大きい全体撮影は等倍で速度維持）
        v = v.resize((w * 3, h * 3), Image.LANCZOS)
    v = ImageOps.autocontrast(v)
    return v.convert("RGB")


def ocr_lines(img):
    """各行の (テキスト, 中心x, 中心y) を返す。座標は撮影画像(=領域)のピクセル。"""
    proc = preprocess(img)
    fx = proc.width / max(1, img.width)      # 拡大率（座標を元画像へ戻す用）
    if CALIBRATE:
        try: proc.save(os.path.join(HERE, "tbh-ocr-proc.png"))
        except Exception: pass
    best = []
    for lang in OCR_LANGS:
        try:
            r = winocr.recognize_pil_sync(proc, lang)
            lines = []
            for ln in (r.get("lines") if isinstance(r, dict) else []) or []:
                ws = ln.get("words") or []
                if not ws:
                    continue
                xs = [w["bounding_rect"]["x"] for w in ws]
                rs = [w["bounding_rect"]["x"] + w["bounding_rect"]["width"] for w in ws]
                ys = [w["bounding_rect"]["y"] for w in ws]
                bs = [w["bounding_rect"]["y"] + w["bounding_rect"]["height"] for w in ws]
                cx = (min(xs) + max(rs)) / 2 / fx
                cy = (min(ys) + max(bs)) / 2 / fx
                lines.append((ln.get("text", ""), cx, cy))
            if len(lines) > len(best):
                best = lines
        except Exception:
            pass
    return best


WORKQ = queue.Queue()    # 戻るボタン押下シグナル（常駐ワーカーが処理）

def ocr_worker():
    """常駐1本のワーカー: OCRエンジンを一度だけ初期化(COM/winrtのスレッド親和性対策)し、
    押下シグナルごとに 撮影→OCR→照合 を直列実行する。"""
    try:
        winocr.recognize_pil_sync(Image.new("RGB", (48, 48)), "ja")   # ウォームアップ
    except Exception:
        pass
    while True:
        WORKQ.get()
        try:
            while True: WORKQ.get_nowait()      # 連打はまとめて1回に
        except queue.Empty:
            pass
        try:
            if foreground_exe() != GAME_EXE:
                continue                        # 他アプリでは何もしない＝「戻る」は普通に効く
            xy = cursor_pos()
            PQ.put(("__close__", None, None))   # ① 古いポップを消す（前の結果を撮らない＝stale防止）
            time.sleep(0.12)
            img, (ox, oy) = grab(NAME_REGIONS[0])   # ② ポップ無しで先に撮影（上部ウィンドウ全体）
            PQ.put(("__processing__", xy, None))    # ③ 撮影後に「読み取り中」
            if CALIBRATE:
                try: img.save(os.path.join(HERE, "cap0.png"))
                except Exception: pass
            lines = ocr_lines(img)
            texts = [t for t, _, _ in lines]
            # 照合プローブ: 各行単独＋「真下にある行」を空間的に結合（名前＋等級）。
            # winocrの行順は画面順でないので、座標で“直下の行”を探して結合する。
            probes = []
            for (t, cx, cy) in lines:
                probes.append((t, cx, cy))
                for (tt, xx, yy) in lines:
                    if 6 < yy - cy < 90 and abs(xx - cx) < 240:   # 直下＆横位置が近い＝等級行
                        probes.append((t + tt, cx, cy))
            cands = []
            for (text, cx, cy) in probes:
                r = matcher.match(text)
                if r:
                    sx, sy = ox + cx, oy + cy
                    d2 = (sx - xy[0]) ** 2 + (sy - xy[1]) ** 2
                    cands.append((r[0]["score"], d2, sx, sy, r))
            found = []
            conf = [c for c in cands if c[0] >= 0.85]   # 確信できる一致のみ
            if conf:
                found = min(conf, key=lambda c: c[1])[4]   # その中でカーソル最近を最優先
            elif cands:
                found = max(cands, key=lambda c: c[0])[4]  # 確信無ければ最高スコア
            if CALIBRATE:
                try:
                    with open(os.path.join(HERE, "ocr-text.txt"), "w", encoding="utf-8") as f:
                        f.write(f"cursor={xy}  win_off=({ox},{oy})\n--CANDIDATES--\n")
                        for sc, d2, sx, sy, r in sorted(cands, key=lambda c: c[1]):
                            f.write(f"{r[0]['base_ja']}  score={sc} dist={int(d2**0.5)} @({int(sx)},{int(sy)})\n")
                        f.write("--LINES--\n")
                        for t, cx, cy in lines:
                            f.write(f"({int(ox+cx)},{int(oy+cy)}) {t}\n")
                except Exception:
                    pass
            PQ.put((found, xy, "\n".join(texts)))
        except Exception:
            log_fatal("worker error:\n" + traceback.format_exc())


# ---- ポップ表示（メインスレッドで） --------------------------------------
_open = []
def show_popup(results, xy, text, root):
    for w in _open[:]:
        try: w.destroy()
        except Exception: pass
        _open.remove(w)

    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    try: win.attributes("-alpha", 0.97)
    except Exception: pass

    border = tk.Frame(win, bg=C_ACCENT)
    border.pack()
    card = tk.Frame(border, bg=C_CARD)
    card.pack(padx=(6, 2), pady=2)   # 左に太めのアクセント帯

    f_name  = tkfont.Font(family="Yu Gothic UI", size=20, weight="bold")
    f_price = tkfont.Font(family="Yu Gothic UI", size=26, weight="bold")
    f_sub   = tkfont.Font(family="Yu Gothic UI", size=15)
    f_meta  = tkfont.Font(family="Yu Gothic UI", size=12)

    def row(txt, color, fnt, pady=(2, 2)):
        tk.Label(card, text=txt, bg=C_CARD, fg=color, font=fnt,
                 anchor="w", justify="left").pack(fill="x", padx=20, pady=pady)

    url = None
    if results == "__processing__":
        row("🔍 読み取り中…", C_ACCENT, f_name, (16, 16))
    elif not results:
        row("該当なし", C_ERR, f_name, (16, 4))
        snip = (text or "").strip().replace("\n", " ")[:36] or "(読取なし)"
        row(f"読取: {snip}", C_META, f_meta, (0, 16))
    else:
        e = results[0]
        jp = e.get("base_ja") or e.get("ja") or e["base_en"]   # 日本語名＋等級を大きく
        row(jp, C_NAME, f_name, (16, 0))
        row(e["base_en"], C_JA, f_sub, (0, 4))                  # 英語名は小さく
        row(f"最安 {yen(e['sell'])}    中央値 {yen(e['median'])}", C_PRICE, f_price, (4, 4))
        row(f"{e.get('type','')}   出品 {e.get('listings','—')} / 売買 {e.get('volume','—')}",
            C_META, f_meta, (0, 2))
        row("クリックでSteamマーケットを開く", C_ACCENT, f_meta, (0, 2))
        row(f"相場 {matcher.marketUpdated or '—'}", C_META, f_meta, (0, 16))
        url = f"https://steamcommunity.com/market/listings/{APPID}/" + urllib.parse.quote(e["en"])

    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    pw, ph = win.winfo_width(), win.winfo_height()
    x = min(max(8, xy[0] + 26), sw - pw - 8)     # カーソル近くに表示
    y = min(max(8, xy[1] + 26), sh - ph - 8)
    win.geometry(f"+{x}+{y}")

    def on_click(ev):
        if url:
            try: webbrowser.open(url)
            except Exception: pass
        win.destroy()
    for w in [win, border, card] + list(card.winfo_children()):
        w.bind("<Button-1>", on_click)
    win.after(int(POPUP_SECONDS * 1000), lambda: (win.winfo_exists() and win.destroy()))
    _open.append(win)


def poll(root):
    try:
        while True:
            results, xy, text = PQ.get_nowait()
            if results == "__close__":
                for w in _open[:]:
                    try: w.destroy()
                    except Exception: pass
                    _open.remove(w)
                continue
            show_popup(results, xy, text, root)
    except queue.Empty:
        pass
    root.after(80, lambda: poll(root))


# ---- タスクトレイ --------------------------------------------------------
def tray_image():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, 60, 60], radius=14, fill=(26, 29, 36, 255),
                        outline=(45, 212, 191, 255), width=3)
    d.ellipse([20, 20, 44, 44], outline=(52, 211, 153, 255), width=4)
    d.line([32, 16, 32, 48], fill=(52, 211, 153, 255), width=3)
    return img


def run_tray(root):
    def _quit(icon, item):
        icon.stop()
        root.after(0, root.destroy)
    menu = pystray.Menu(
        pystray.MenuItem("TBH 相場OCR  ( ゲーム前面で戻るボタン )", None, enabled=False),
        pystray.MenuItem("終了", _quit),
    )
    pystray.Icon("tbh_price_ocr", tray_image(), "TBH 相場OCR", menu).run()


# ---- main ----------------------------------------------------------------
def main():
    threading.Thread(target=fetch_rate, daemon=True).start()   # 円レート取得（非同期）
    root = tk.Tk()
    root.withdraw()
    threading.Thread(target=ocr_worker, daemon=True).start()    # OCR常駐ワーカー（初期化1回）
    # マウスの「戻る」サイドボタンで発動（押下シグナルをワーカーへ。前面判定はワーカー内）
    mouse.on_button(lambda: WORKQ.put(1), buttons=(SIDE_BUTTON,), types=("down",))
    threading.Thread(target=run_tray, args=(root,), daemon=True).start()
    poll(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_fatal("fatal:\n" + traceback.format_exc())
        try:
            import tkinter.messagebox as mb
            r = tk.Tk(); r.withdraw()
            mb.showerror("TBH相場OCR", "起動に失敗しました。error.log を確認してください。")
        except Exception:
            pass
