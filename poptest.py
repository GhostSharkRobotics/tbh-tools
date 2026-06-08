# -*- coding: utf-8 -*-
# 本体をimportしてshow_popupだけ呼び、描画→スクショ→クリック送出→生死確認を自動で行う自己テスト。
# 対話デスクトップ(schtasks /it)で実行すること（session0では描画/撮影できない）。
import importlib.util, sys, os, time, ctypes, traceback
P = r'C:\Users\monoq\tbh-price-ocr'
sys.path.insert(0, P)
LOG = os.path.join(P, 'poptest-log.txt')
def w(msg):
    with open(LOG, 'a', encoding='utf-8') as f: f.write(str(msg) + '\n')
open(LOG, 'w', encoding='utf-8').close()
try:
    spec = importlib.util.spec_from_file_location('tbhpop', os.path.join(P, 'tbh-price-ocr.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    w('import OK')
    import tkinter as tk, mss
    root = tk.Tk(); root.withdraw()
    mod._ui_lang = 'ja'
    fake = [{'ja': 'エクリプスブレーサー', 'en': 'Eclipse Bracer', 'rarity_ja': 'レジェンダリー',
             'rarity_en': 'Legendary', 'type_ja': '小手 Lv.20', 'type_en': 'Bracer Lv.20', 'type': '小手',
             'hash': 'Eclipse Bracer (Legendary)', 'sell': 1234, 'median': 1500, 'listings': 5,
             'volume': 42, 'score': 1.0}]
    mod.show_popup(fake, (600, 400), 'エクリプスブレーサー レジェンダリー', root)
    for _ in range(40):
        root.update(); time.sleep(0.03)
    win = mod._open[-1] if mod._open else None
    w('popup_shown=%s exists=%s geo=%s' % (win is not None, win and win.winfo_exists(),
      win and (win.winfo_rootx(), win.winfo_rooty(), win.winfo_width(), win.winfo_height())))
    with mss.mss() as s: s.shot(output=os.path.join(P, 'poptest1.png'))
    # 中央を左クリック（閉じる紐付けがあるか実地確認）
    if win and win.winfo_exists():
        cx = win.winfo_rootx() + win.winfo_width() // 2
        cy = win.winfo_rooty() + win.winfo_height() // 2
        ctypes.windll.user32.SetCursorPos(int(cx), int(cy))
        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
        for _ in range(25):
            root.update(); time.sleep(0.03)
        alive = bool(mod._open) and mod._open[-1].winfo_exists()
        w('after_center_click_alive=%s' % alive)
    with mss.mss() as s: s.shot(output=os.path.join(P, 'poptest2.png'))
    w('DONE')
    root.destroy()
except Exception:
    w('ERR\n' + traceback.format_exc())
