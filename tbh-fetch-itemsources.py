#!/usr/bin/env python3
"""
tbh-fetch-itemsources.py
アイテム→全入手元の逆引きインデックスを生成して tbh-data.json の itemSources に書き込む。

なぜ必要か: tbh-data.json の craftResults/synthesisResults の集計「産出種別%」表は
ITEMGROUP形式のドロップを取りこぼし、ORB/弓/矢/杖等が一覧から消える。
そのため「このアイテムどこで入手?」が集計表からは追えない事故が起きる。
ここでは生テーブル(DropInfoData等)を直接歩いて、二度と「わからない」が起きない逆引きを作る。

チェーン:
  CraftingRecipeInfoData.DropKey ─┐
  SynthesisDropInfoData.DropKey  ─┼─> DropInfoData[DropKey] (Weight, REWARDTYPE, RewardKey)
  boxes(モンスター宝箱).dropKey   ─┘        └─ ITEMGROUP -> ItemGroupInfoData -> ItemKey[]
                                            └─ ITEM      -> ItemKey
"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
TBL = os.path.join(ROOT, "tools", "extracted", "tables")


def load(name):
    a = json.load(open(os.path.join(TBL, name + ".json"), encoding="utf-8"))
    return a if isinstance(a, list) else list(a.values())[0]


def main():
    item_info = {r["ItemKey"]: r for r in load("ItemInfoData")}
    # group -> [itemKey]
    groups = {}
    for r in load("ItemGroupInfoData"):
        groups.setdefault(r["ItemGroupKey"], []).append(r["ItemKey"])

    # DropInfoData: dropKey -> rows ; total weight per dropKey
    drop_rows = {}
    for r in load("DropInfoData"):
        drop_rows.setdefault(r["DropKey"], []).append(r)
    drop_total = {k: sum(int(r["Weight"]) for r in v) for k, v in drop_rows.items()}

    # classify dropKeys
    craft_dk = {}   # dropKey -> {type, tier}
    for r in load("CraftingRecipeInfoData"):
        craft_dk[r["DropKey"]] = {"craftType": r["ItemCraftingType"], "tier": int(r["RecipeTier"])}
    synth_dk = {}   # dropKey -> list of {synType, grade, level, tier}
    for r in load("SynthesisDropInfoData"):
        synth_dk.setdefault(r["DropKey"], []).append({
            "synType": r["ItemSynthesisType"], "grade": r["GRADE"],
            "level": int(r["ItemLevel"]), "tier": int(r["RecipeTier"])})
    # chests from existing tbh-data boxes
    data_path = os.path.join(ROOT, "tbh-data.json")
    data = json.load(open(data_path, encoding="utf-8"))
    chest_dk = {}
    for b in data.get("boxes", {}).get("items", []):
        dk = b.get("dropKey")
        if dk:
            chest_dk[dk] = {"source": b.get("source"), "color": b.get("color"),
                            "boxGrade": b.get("grade"), "boxType": b.get("type")}

    # expand each dropKey row into (itemKey, weight)
    def expand(r):
        rt = r["REWARDTYPE"]
        if rt == "ITEMGROUP":
            return [(ik, r) for ik in groups.get(r["RewardKey"], [])]
        if rt == "ITEM":
            return [(r["RewardKey"], r)]
        return []  # GOLD / MATERIAL_AMOUNT / etc. — gear sources only

    # build reverse index: itemKey -> [source records]
    sources = {}
    for dk, rows in drop_rows.items():
        tot = drop_total[dk] or 1
        for r in rows:
            w = int(r["Weight"])
            for ik, _ in expand(r):
                rec = {"dropKey": dk, "w": w, "tot": tot,
                       "pct": round(100.0 * w / tot, 4)}
                if dk in craft_dk:
                    rec["via"] = "cube"
                    rec.update(craft_dk[dk])
                elif dk in synth_dk:
                    rec["via"] = "synthesis"
                    rec["ctx"] = synth_dk[dk]
                elif dk in chest_dk:
                    rec["via"] = "chest"
                    rec.update(chest_dk[dk])
                else:
                    rec["via"] = "drop"
                sources.setdefault(ik, []).append(rec)

    # attach light item meta + sort sources (cube/synthesis first, then by pct)
    order = {"cube": 0, "synthesis": 1, "chest": 2, "drop": 3}
    out = {}
    for ik, recs in sources.items():
        info = item_info.get(ik, {})
        recs.sort(key=lambda x: (order.get(x["via"], 9), -x["pct"]))
        out[ik] = {
            "grade": info.get("GRADE"),
            "gear": info.get("GEARTYPE"),
            "parts": info.get("PARTS"),
            "lvl": int(info["Level"]) if info.get("Level") not in (None, "") else None,
            "via": sorted(set(r["via"] for r in recs)),
            "sources": recs,
        }

    data["itemSources"] = {
        "_note": ("アイテムID→全入手元の逆引き。生DropInfoDataを直接展開(ITEMGROUP対応)。"
                  "via: cube=キューブクラフト(スロット固定レシピ) / synthesis=合成(カテゴリ袋からランダム) "
                  "/ chest=モンスター宝箱 / drop=その他テーブル。"
                  "pct=そのテーブル内でこのアイテム(群)の重み割合。"
                  "ITEMGROUP+DLCVariantは職に応じ群内の1種が出る(オーブ枠=ソーサラー等)。"),
        "items": out,
    }
    json.dump(data, open(data_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("itemSources items:", len(out))
    # sanity: Frozen Orb arcana
    fo = out.get("425041")
    print("\n[verify] Frozen Orb Arcana 425041:")
    print("  meta:", {k: fo[k] for k in ("grade", "gear", "lvl", "via")})
    for r in fo["sources"]:
        print("  ", r["via"], r.get("craftType") or r.get("source") or r.get("ctx") or "", "| dropKey", r["dropKey"], "| pct", r["pct"])


if __name__ == "__main__":
    main()
