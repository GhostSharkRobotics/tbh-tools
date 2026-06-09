# 仮説検証：小倍率でOCRが空になるのは crop をベース文字サイズへ正規化していないため。
# 既存 cap0.png で「そのまま」vs「1/f 拡大」のOCR結果を比べる。
import importlib.util, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ml_diag", os.path.join(HERE, "tbh-price-ocr.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

img = Image.open(os.path.join(HERE, "cap0.png")).convert("RGB")
boxes, f = m.detect_boxes(img)
print(f"detected f={f:.3f} boxes={len(boxes)} imgWH={img.width}x{img.height}")

# detect_boxes内と同じ crop を再現して比較
S = lambda v: int(round(v * f))
import numpy as np, cv2
arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR); arr_e = m._edges(arr)
res = m._match_at(arr, arr_e, f)
ys, xs = np.where(res >= 0.55)
peaks = sorted(zip(xs.tolist(), ys.tolist(), res[ys, xs].tolist()), key=lambda p: -p[2])
dx, dy = S(420), S(36); picked = []
for x, y, s in peaks:
    if all(abs(x-px) > dx or abs(y-py) > dy for px, py, _ in picked): picked.append((x, y, s))
    if len(picked) >= 10: break

for x, y, s in picked:
    crop = img.crop((max(0, x-S(90)), y+S(6), x+S(560), y+S(56)))
    raw = m._ocr(crop)
    up = crop.resize((max(1, int(crop.width/f)), max(1, int(crop.height/f))), Image.LANCZOS)
    upr = m._ocr(up)
    print(f"\n枠@({x},{y}) cropWH={crop.width}x{crop.height} -> upWH={up.width}x{up.height}")
    print(f"  そのまま : [{raw.strip()[:40]!r}]")
    print(f"  1/f拡大  : [{upr.strip()[:40]!r}]")
