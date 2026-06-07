"""OCRテキスト -> 価格エントリ(変種まとめ)。閉じた辞書への曖昧スナップ。stdlibのみ。"""
import json, re, unicodedata, os, difflib

_SMALL = str.maketrans("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ",
                       "あいうえおつやゆよわアイウエオツヤユヨワ")
# 漢字↔カナの定番OCR誤読を寄せる（力→カ, 口→ロ 等）
_LOOK = str.maketrans({"力": "カ", "口": "ロ", "工": "エ", "二": "ニ", "八": "ハ",
                       "夕": "タ", "卜": "ト", "0": "o", "1": "l", "|": "l"})

def _h2k(s):   # ひらがな→カタカナ統一
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)

def norm(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s).lower()
    s = _h2k(s)                       # ひら→カタ統一
    s = s.translate(_SMALL)           # 小書き→大書き
    s = unicodedata.normalize("NFD", s).replace("゙", "").replace("゚", "")  # 濁点/半濁点除去
    s = s.translate(_LOOK)            # 漢字/類似字→カナ
    s = re.sub(r"[\s　ー\-ｰ~一()\[\]（）【】・,._/:：]+", "", s)   # 記号・長音・空白除去
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

    def match(self, ocr_text: str, min_score=0.7):
        # OCRの各行＋全体を候補に。部分一致(カバー率)と曖昧一致を総合スコアで比較し最良を採る。
        # これで「サンダーストーン」が少し崩れても短い「ストーン」に化けない（長い正式名を優先）。
        cands = []
        parts = [p for p in re.split(r"[\r\n]+", ocr_text) if norm(p)]
        # 各行＋隣接行ペア（名前と等級が別行でも結合して判定）＋全体
        probes = parts + [parts[i] + parts[i + 1] for i in range(len(parts) - 1)] + [ocr_text]
        for probe in probes:
            q = norm(probe)
            if len(q) < 2: continue
            if q in self.index:
                cands.append((1.0, q, len(q))); continue
            for k in self.keys:
                if len(k) >= 2 and k in q:            # 既知名が読取に含まれる
                    cov = len(k) / max(len(k), len(q))   # 読取のうち名前が占める割合
                    cands.append((0.6 + 0.4 * cov, k, len(k)))
            for k in difflib.get_close_matches(q, self.keys, n=3, cutoff=min_score):
                cands.append((difflib.SequenceMatcher(None, q, k).ratio(), k, len(k)))
        if not cands: return []
        score, key, _ = max(cands, key=lambda c: (round(c[0], 3), c[2]))   # 同点なら長い名前
        if score < min_score: return []
        return self._collect(key, score)

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
