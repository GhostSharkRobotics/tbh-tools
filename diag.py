# -*- coding: utf-8 -*-
# ポップが本当にTOPMOSTになっているかを数値で確認（GA_ROOT解決前後のexstyleとSetWindowPos戻り値）。
import importlib.util, sys, os, time, ctypes, traceback
P = r'C:\Users\monoq\tbh-price-ocr'
sys.path.insert(0, P)
LOG = os.path.join(P, 'diag-log.txt')
def w(m):
    with open(LOG, 'a', encoding='utf-8') as f: f.write(str(m) + '\n')
open(LOG, 'w', encoding='utf-8').close()
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000
u = ctypes.windll.user32
try:
    spec = importlib.util.spec_from_file_location('tbhpop', os.path.join(P, 'tbh-price-ocr.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    import tkinter as tk
    root = tk.Tk(); root.withdraw(); mod._ui_lang = 'ja'
    fake = [{'ja': 'エクリプスブレーサー', 'en': 'Eclipse Bracer', 'rarity_ja': 'レジェンダリー',
             'rarity_en': 'Legendary', 'type_ja': '小手 Lv.20', 'type_en': 'Bracer Lv.20', 'type': '小手',
             'hash': 'Eclipse Bracer (Legendary)', 'sell': 1234, 'median': 1500, 'volume': 42, 'score': 1.0}]
    mod.show_popup(fake, (600, 400), 'エクリプスブレーサー レジェンダリー', root)
    for _ in range(40): root.update(); time.sleep(0.03)
    win = mod._open[-1]
    h = win.winfo_id()
    ga = u.GetAncestor(h, 2)
    gp = u.GetParent(h)
    w('winfo_id=%s GA_ROOT=%s GetParent=%s' % (h, ga, gp))
    for label, hh in (('winfo_id', h), ('GA_ROOT', ga)):
        if not hh: continue
        ex = u.GetWindowLongW(hh, GWL_EXSTYLE)
        w('%s exstyle=0x%08x TOPMOST=%s NOACTIVATE=%s' % (label, ex & 0xffffffff,
          bool(ex & WS_EX_TOPMOST), bool(ex & WS_EX_NOACTIVATE)))
    # 明示的にトップHWNDへtopmostを打ってみる
    th = mod._top_hwnd(win)
    r = u.SetWindowPos(th, -1, 0, 0, 0, 0, 0x0013)  # NOSIZE|NOMOVE|NOACTIVATE
    ex2 = u.GetWindowLongW(th, GWL_EXSTYLE)
    w('after SetWindowPos top_hwnd=%s ret=%s exstyle TOPMOST=%s' % (th, r, bool(ex2 & WS_EX_TOPMOST)))
    w('DONE')
    root.destroy()
except Exception:
    w('ERR\n' + traceback.format_exc())
