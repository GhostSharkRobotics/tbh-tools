"""OCRテキスト -> 価格エントリ(変種まとめ)。閉じた辞書への曖昧スナップ。stdlibのみ。"""
import json, re, unicodedata, os, difflib

def norm(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    s = re.sub(r"[\s　()\[\]（）【】・,.\-_/:：]+", "", s)
    return s

class Matcher:
    def __init__(self, path):
        d = json.load(open(path, encoding="utf-8"))
        self.entries = d["entries"]; self.index = d["index"]
        self.keys = list(self.index.keys()); self.marketUpdated = d.get("marketUpdated")

    def _best_key(self, ocr_text):
        cands = []
        lines = [l for l in re.split(r"[\r\n]+", ocr_text) if l.strip()]
        for probe in lines + [ocr_text]:
            q = norm(probe)
            if not q: continue
            if q in self.index: cands.append((1.0, q)); continue
            for k in self.keys:
                if len(k) >= 3 and (k in q or q in k):
                    r = min(len(k), len(q)) / max(len(k), len(q))
                    cands.append((0.9 * r, k))
            for k in difflib.get_close_matches(q, self.keys, n=3, cutoff=0.55):
                cands.append((difflib.SequenceMatcher(None, q, k).ratio(), k))
        return max(cands, key=lambda x: x[0]) if cands else None

    def match(self, ocr_text: str, min_score=0.55):
        bk = self._best_key(ocr_text)
        if not bk or bk[0] < min_score: return []
        score, key = bk
        # マッチしたエントリ群の base_en で同一ベース全変種を集約
        idxs = self.index[key]
        bases = {norm(self.entries[i]["base_en"]) for i in idxs}
        out = [self.entries[i] for i in range(len(self.entries))
               if norm(self.entries[i]["base_en"]) in bases]
        # 変種A,B... の順
        out.sort(key=lambda e: (e["base_en"], e["variant"]))
        for e in out: e["score"] = round(score, 3)
        return out

if __name__ == "__main__":
    ROOT = os.path.dirname(os.path.abspath(__file__))
    m = Matcher(os.path.join(ROOT, "tbh-price-lookup.json"))
    tests = ["War Bow (Legendary) A", "ウォーボウ（レジェンダリー）", "Wood",
             "癒しの薬草", "War  Bow  (Legendary)  Lv.20", "lron lngot",
             "スパイダ-シルク", "ゴブリンの皮   x12"]
    for t in tests:
        r = m.match(t)
        print(f"\nIN : {t!r}")
        for e in r:
            v = f" [{e['variant']}]" if e["variant"] else ""
            print(f"  -> {e['base_en']}{v} / {e['ja']}  売値={e['sell']} 中央={e['median']}  ({e['type']})  s={e['score']}")
        if not r: print("  (no match)")
