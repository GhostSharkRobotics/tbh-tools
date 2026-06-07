"""OCRテキスト -> 価格エントリ(変種まとめ)。閉じた辞書への曖昧スナップ。stdlibのみ。"""
import json, re, unicodedata, os, difflib

_SMALL = str.maketrans("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ",
                       "あいうえおつやゆよわアイウエオツヤユヨワ")

def norm(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    s = s.translate(_SMALL)          # 小書きカナ→大書き（OCRのョ/ヨ等の誤読を吸収）
    s = re.sub(r"[\s　()\[\]（）【】・,.\-_/:：]+", "", s)
    return s

class Matcher:
    def __init__(self, path):
        d = json.load(open(path, encoding="utf-8"))
        self.entries = d["entries"]; self.index = d["index"]
        # 索引キーを長い順に（最長一致＝最も具体的＝名前＋等級 を優先）
        self.keys = sorted(self.index.keys(), key=len, reverse=True)
        self.marketUpdated = d.get("marketUpdated")

    def _collect(self, key, score):
        # 同一ベース名の全変種(A/B)を集約して返す
        idxs = self.index[key]
        bases = {norm(self.entries[i]["base_en"]) for i in idxs}
        out = [dict(self.entries[i]) for i in range(len(self.entries))
               if norm(self.entries[i]["base_en"]) in bases]
        out.sort(key=lambda e: (e["base_en"], e["variant"]))
        for e in out: e["score"] = round(score, 3)
        return out

    def match(self, ocr_text: str, min_score=0.6):
        q = norm(ocr_text)
        if not q: return []
        # 1) 既知名が読取テキストに含まれる → 最長一致を採用（横帯OCRのノイズに強い）
        for k in self.keys:                 # 長い順
            if len(k) >= 4 and k in q:
                return self._collect(k, 0.97)
        # 2) 含まれない（OCR崩れ）→ 行ごとに曖昧マッチ
        best = None
        for probe in re.split(r"[\r\n]+", ocr_text):
            nq = norm(probe)
            if len(nq) < 3: continue
            for k in difflib.get_close_matches(nq, list(self.index.keys()), n=1, cutoff=min_score):
                sc = difflib.SequenceMatcher(None, nq, k).ratio()
                if best is None or sc > best[0]: best = (sc, k)
        if best and best[0] >= min_score:
            return self._collect(best[1], best[0])
        return []

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
