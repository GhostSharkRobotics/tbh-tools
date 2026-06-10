# 一時検証用: cap0.png の検出枠(219,675,f=1.0)から名前/等級OCR→マッチまで通るか実機確認
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageFilter
import numpy as np
import winocr
from tbh_price_match import Matcher, RARITIES, extract_rarity

HERE = os.path.dirname(os.path.abspath(__file__))

def _adapt(c, invert=False):
    v = c.convert("HSV").split()[2]
    mean = v.filter(ImageFilter.BoxBlur(14))
    a = np.asarray(v, dtype=np.int16); m = np.asarray(mean, dtype=np.int16)
    cond = (a < m - 8) if invert else (a > m + 8)
    return Image.fromarray((cond * 255).astype("uint8"), "L").convert("RGB")

def _ocr(c):
    out = []
    for proc in (_adapt(c), _adapt(c, invert=True)):
        for lang in ("ja", "en"):
            try:
                r = winocr.recognize_pil_sync(proc, lang)
                out.append(" ".join(l.get("text", "") for l in (r.get("lines") if isinstance(r, dict) else []) or []))
            except Exception as e:
                out.append(f"<ERR {e}>")
    return "\n".join(out)

img = Image.open(os.path.join(HERE, "cap0.png"))
x, y = 219, 675
name_c = img.crop((max(0, x - 90), y + 6, x + 560, y + 56))
rank_c = img.crop((max(0, x - 90), y + 56, x + 560, y + 122))
name = _ocr(name_c); rank = _ocr(rank_c)

m = Matcher(os.path.join(HERE, "tbh-price-lookup.json"))
best = m.match_item(name, rank)
with open(os.path.join(HERE, "ocrtest-out.txt"), "w", encoding="utf-8") as f:
    f.write(f"名[{name}]\n級[{rank}]\n等級抽出={extract_rarity(rank)}\n")
    if best:
        f.write(f"マッチ: {best[0].get('en')} / {best[0].get('ja')} ({best[0].get('rarity_ja')}) score={best[0].get('score')}\n")
    else:
        f.write("マッチ: なし\n")
