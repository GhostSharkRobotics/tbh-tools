#!/usr/bin/env python3
"""tbh-prices.json -> tbh-price-lookup.json
OCR名を「既知名」へ曖昧スナップする索引。EN/JA両対応。
変種A/B・レベルはベース名でグループ化し、該当変種を全部返せるようにする。
"""
import json, re, unicodedata, os

ROOT = os.path.dirname(os.path.abspath(__file__))

def norm(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    s = re.sub(r"[\s　()\[\]（）【】・,.\-_/:：]+", "", s)
    return s

def split_variant(en: str):
    """末尾の ' A'/' B'/' C' を変種として分離。base, variant を返す。"""
    m = re.match(r"^(.*?)[ 　]+([A-C])$", en.strip())
    if m: return m.group(1).strip(), m.group(2)
    return en.strip(), ""

def base_ja(ja: str):
    """JA名末尾の ' A'/' B' を除いたベース。"""
    return re.sub(r"[ 　]+[A-C]$", "", ja.strip()).strip()

def main():
    src = json.load(open(os.path.join(ROOT, "tbh-prices.json")))
    prices = src["prices"]
    entries = []
    for en, v in prices.items():
        b_en, variant = split_variant(en)
        entries.append({
            "en": en, "ja": v.get("name_ja", ""),
            "base_en": b_en, "base_ja": base_ja(v.get("name_ja", "")),
            "variant": variant,
            "sell": v.get("sell"), "median": v.get("median"),
            "listings": v.get("listings"), "volume": v.get("volume"),
            "type": v.get("type", ""),
        })

    # ベース正規化名 -> 同一ベースの全エントリindex（=変種A/Bまとめ）
    index = {}
    def add(key, i):
        if not key: return
        index.setdefault(key, [])
        if i not in index[key]: index[key].append(i)
    for i, r in enumerate(entries):
        add(norm(r["base_en"]), i)
        add(norm(r["base_ja"]), i)
        add(norm(r["en"]), i)   # フル名でも引けるように
        add(norm(r["ja"]), i)

    out = {
        "marketUpdated": src.get("marketUpdated"),
        "currency": src.get("currency"), "unit": src.get("unit"),
        "entries": entries, "index": index,
    }
    dst = os.path.join(ROOT, "tbh-price-lookup.json")
    json.dump(out, open(dst, "w"), ensure_ascii=False)
    print(f"entries={len(entries)} index_keys={len(index)} -> {dst}")

if __name__ == "__main__":
    main()
