#!/usr/bin/env python3
"""tbh-uniquemods-fetched.json (Steam市場で確認した実効果) を tbh-data.json に反映し、
HTMLツール(build-simulator / gem-search) のDATAブロックを再注入する。

反映内容:
 1. uniqueMods.definitions[*].descEn/descJa を実テキストで上書き、descConfirmed=true(確認済みのみ)。
 2. uniqueMods.items[*].uniqueMod を検証済み(ベース|グレード)対応で訂正し、modConfirmed を付与。
 3. uniqueMods.definitions の grades/gearTypes/itemCount を訂正後のitemsから再集計。
 4. _meta/source 注記を更新。
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
fetched = json.load(open(os.path.join(HERE, "tbh-uniquemods-fetched.json"), encoding="utf-8"))
dj = os.path.join(HERE, "tbh-data.json")
d = json.load(open(dj, encoding="utf-8"))
um = d["uniqueMods"]

cdef = fetched["confirmedDefs"]
vmap = fetched["verifiedItemMods"]

# 1) definitions のテキスト更新
confirmed_keys = set(cdef.keys())
for de in um["definitions"]:
    k = de["key"]
    if k in cdef:
        de["descEn"] = cdef[k]["en"]
        de["descJa"] = cdef[k]["ja"]
        de["descConfirmed"] = True
        de["descSource"] = "Steam Market"
    else:
        de["descConfirmed"] = False

# 2) items の mod 訂正 + modConfirmed
changed = 0
for it in um["items"]:
    key = it["nameEn"] + "|" + it["gradeEn"]
    if key in vmap:
        if it["uniqueMod"] != vmap[key]:
            it["uniqueMod"] = vmap[key]
            changed += 1
        it["modConfirmed"] = True
    else:
        it["modConfirmed"] = False

# 3) definitions 集計を訂正後 items から再計算
from collections import defaultdict
agg = defaultdict(lambda: {"grades": set(), "gears": set(), "n": 0})
for it in um["items"]:
    a = agg[it["uniqueMod"]]
    a["grades"].add(it["gradeEn"]); a["gears"].add(it["gear"]); a["n"] += 1
for de in um["definitions"]:
    a = agg.get(de["key"])
    if a:
        de["grades"] = sorted(a["grades"])
        de["gearTypes"] = sorted(a["gears"])
        de["itemCount"] = a["n"]
    else:
        de["itemCount"] = 0

# 4) 注記
um["_note"] = ("特殊ステータス(固有効果/UniqueMod)。効果テキストは Steam Community Market のリスティング "
               "ツールチップ 'Unique Stats' で確認(descConfirmed=true)。固有効果は (ベース装備×グレード) で固定。"
               "低グレードは汎用スキルmod、高グレードでスキル固有mod。descConfirmed=false は内部キー名からの推定で未確認"
               "(該当グレードの市場出品が無く検証不可)。items.modConfirmed=true は市場で対応を直接確認した装備。")
um["source"] = "Steam Community Market (appid 3678970) + probonk.com (内部キー)"
um["confirmedDefCount"] = len(confirmed_keys)
um["confirmedItemCount"] = sum(1 for it in um["items"] if it.get("modConfirmed"))

json.dump(d, open(dj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"updated tbh-data.json | defs confirmed={len(confirmed_keys)} | item mod changed={changed} | item confirmed={um['confirmedItemCount']}")

# 5) HTMLツールに DATA を再注入
dcompact = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
for fn in ("tbh-gem-search.html", "tbh-build-simulator.html", "tbh-best-build.html"):
    fp = os.path.join(HERE, fn)
    if not os.path.exists(fp):
        continue
    h = open(fp, encoding="utf-8").read()
    if "/*DATA_START*/" not in h:
        print("  no DATA block in", fn); continue
    h = re.sub(r"/\*DATA_START\*/.*?/\*DATA_END\*/", "/*DATA_START*/" + dcompact + "/*DATA_END*/", h, flags=re.S)
    open(fp, "w", encoding="utf-8").write(h)
    print("injected ->", fn)
