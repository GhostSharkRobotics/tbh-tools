#!/usr/bin/env python3
"""tbh-data.json(全アイテム) + tbh-prices.json(価格) -> tbh-price-lookup.json
全アイテム(装備/宝石/素材/彫刻/アイテム)を名前＋等級で索引化し、市場価格があれば付与する。
価格が無ければ sell=None（=「市場価格なし」）。OCR名→既知名へ曖昧スナップ用。EN/JA両対応。
"""
import json, re, unicodedata, os

ROOT = os.path.dirname(os.path.abspath(__file__))

_SMALL = str.maketrans("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ",
                       "あいうえおつやゆよわアイウエオツヤユヨワ")
_LOOK = str.maketrans({"力": "カ", "口": "ロ", "工": "エ", "二": "ニ", "八": "ハ",
                       "夕": "タ", "卜": "ト", "0": "o", "1": "l", "|": "l"})

def _h2k(s):
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)

def norm(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s).lower()
    s = _h2k(s)
    s = s.translate(_SMALL)
    s = unicodedata.normalize("NFD", s).replace("゙", "").replace("゚", "")
    s = s.translate(_LOOK)
    s = s.replace("等級", "")                       # 「○○等級」の等級は除去
    s = re.sub(r"[\s　ー\-ｰ~一'’!?;()\[\]（）【】・,._/:：]+", "", s)
    return s


def main():
    data = json.load(open(os.path.join(ROOT, "tbh-data.json"), encoding="utf-8"))
    prices = json.load(open(os.path.join(ROOT, "tbh-prices.json"), encoding="utf-8"))["prices"]

    # レアリティ en->ja（rarityOrder と equipRarities が同順）
    rorder = data.get("rarityOrder", [])
    rja = [r["name"] for r in data.get("equipRarities", [])]
    RMAP = dict(zip(rorder, rja))

    def price_of(hashkey):
        return prices.get(hashkey)

    entries = {}   # キー(ja, rarity_ja) -> entry。A/Bは価格ある方を採用してまとめる
    def put(ja, en, rarity_en, hashkey, gtype, variant=""):
        if not ja and not en: return
        rja_ = RMAP.get(rarity_en, "")
        k = (ja, rja_, en)
        e = entries.get(k)
        if e is None:
            e = {"ja": ja, "en": en, "rarity_ja": rja_, "rarity_en": rarity_en or "",
                 "type": gtype or "", "hash": hashkey, "variant": variant,
                 "sell": None, "median": None, "listings": None, "volume": None}
            entries[k] = e
        pr = price_of(hashkey)
        if pr and e["sell"] is None:
            e.update(sell=pr.get("sell"), median=pr.get("median"),
                     listings=pr.get("listings"), volume=pr.get("volume"),
                     hash=hashkey, type=pr.get("type", e["type"]))

    # 装備: nameEn (rarity) variant
    for x in data.get("equipment", []):
        var = x.get("variant", "") or ""
        hk = f"{x['nameEn']} ({x['rarity']})" + (f" {var}" if var else "")
        put(x.get("name", ""), x.get("nameEn", ""), x.get("rarity"), hk, x.get("gearJa", ""), var)

    # 宝石・彫刻: nameEn（市場は素名）
    for x in data.get("gems", []):
        put(x.get("name", ""), x.get("nameEn", ""), x.get("rarity"), x.get("nameEn", ""), "宝石")
    for x in data.get("engravings", []):
        put(x.get("name", ""), x.get("nameEn", ""), x.get("rarity"), x.get("nameEn", ""), "彫刻素材")
    # 素材: name.{ja,en}
    for x in data.get("materials", []):
        nm = x.get("name", {})
        put(nm.get("ja", ""), nm.get("en", ""), None, nm.get("en", ""), x.get("materialType", "素材"))
    # アイテム類: name.{ja,en}
    for x in data.get("items", []):
        nm = x.get("name", {})
        put(nm.get("ja", ""), nm.get("en", ""), None, nm.get("en", ""), x.get("type", "アイテム"))

    # 価格にあってDBで拾えなかったキーはそのまま追加（取りこぼし防止）
    seen_hash = {e["hash"] for e in entries.values()}
    for hk, pr in prices.items():
        if hk in seen_hash: continue
        m = re.match(r"^(.*?) \(([^)]+)\)(?: ([A-C]))?$", hk)
        if m:
            en_base, rar, var = m.group(1), m.group(2), m.group(3) or ""
        else:
            en_base, rar, var = hk, None, ""
        k = (pr.get("name_ja", ""), RMAP.get(rar, ""), en_base)
        if k in entries: continue
        entries[k] = {"ja": pr.get("name_ja", ""), "en": en_base, "rarity_ja": RMAP.get(rar, ""),
                      "rarity_en": rar or "", "type": pr.get("type", ""), "hash": hk, "variant": var,
                      "sell": pr.get("sell"), "median": pr.get("median"),
                      "listings": pr.get("listings"), "volume": pr.get("volume")}

    entries = list(entries.values())

    # 索引: 名前＋等級 / 名前 / 英名＋等級 / 英名（normで）
    index = {}
    def add(key, i):
        if not key: return
        index.setdefault(key, [])
        if i not in index[key]: index[key].append(i)
    for i, e in enumerate(entries):
        ja, en, rj, re_ = e["ja"], e["en"], e["rarity_ja"], e["rarity_en"]
        add(norm(ja + rj), i)
        add(norm(ja), i)
        add(norm(en + re_), i)
        add(norm(en), i)

    out = {"marketUpdated": json.load(open(os.path.join(ROOT, "tbh-prices.json"), encoding="utf-8")).get("marketUpdated"),
           "entries": entries, "index": index}
    json.dump(out, open(os.path.join(ROOT, "tbh-price-lookup.json"), "w", encoding="utf-8"), ensure_ascii=False)
    priced = sum(1 for e in entries if e["sell"] is not None)
    print(f"entries={len(entries)} (price有={priced}) index_keys={len(index)}")


if __name__ == "__main__":
    main()
