#!/usr/bin/env python3
"""TBH スキルDB生成スクリプト（probonk.com のゲーム内部データから）

全6クラスのアクティブスキル(106)とパッシブスキル(108)を抽出し、tbh-data.json に
skills(アクティブ) / passiveSkills を作り直す。各キャラのスキル詳細パラメーター
（倍率・射程・属性・配信タイプ・Lv1〜10スケーリング・効果説明文）を実機データから取得する。
推測しない（メモリ tbh-research-before-build 方針）＝probonk由来の生データのみ収録。

データ源: probonk.com の Next.js RSC ペイロード（実機データマイン。equipment/enemies と同じ正の情報源）
  - /skills … activeSkills[] (SkillKey,名前/説明i18n,ACTIVATIONTYPE,Param1-5,Range,DamageType,
                              DamageDeliveryType,Value,levels[]) + passiveSkills[] (STATTYPE/MODTYPE/Value)

SkillKey の第1桁 = クラス: 1=ナイト 2=レンジャー 3=ソーサラー 4=プリースト 5=ハンター 6=スレイヤー
使い方: python3 tbh-fetch-skills.py
"""
import json, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://probonk.com/tbh-task-bar-hero/"

# SkillKey / PassiveSkillKey の第1桁 → クラス（probonkの並びがメモリのロスターと一致）
CLASS_BY_DIGIT = {
    "1": "ナイト", "2": "レンジャー", "3": "ソーサラー",
    "4": "プリースト", "5": "ハンター", "6": "スレイヤー",
}
ELEM = {"Physical": "physical", "Fire": "fire", "Cold": "cold",
        "Lightning": "lightning", "Chaos": "chaos"}


def fetch(slug):
    req = urllib.request.Request(BASE + slug, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")


def unescape(s):
    return s.replace('\\"', '"').replace("\\\\", "\\")


def extract_array(h, key):
    """エスケープ済みHTMLから "<key>":[ ... ] の配列を取り出して json.loads する。"""
    mark = '\\"%s\\":[' % key
    i = h.find(mark)
    if i < 0:
        raise RuntimeError("marker not found: " + key)
    start = i + len(mark) - 1
    depth, j, instr, esc = 0, start, False, False
    while j < len(h):
        c = h[j]
        if esc:
            esc = False
        elif c == "\\":
            esc = True
        elif instr:
            if c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return json.loads(unescape(h[start:j + 1]))
        j += 1
    raise RuntimeError("unterminated array: " + key)


def pick(i18n, lang):
    return (i18n or {}).get(lang)


def build_active(sk):
    key = sk["SkillKey"]
    cls = CLASS_BY_DIGIT.get(str(key)[0])
    name_i = sk.get("SkillNameKey_i18n") or {}
    desc_i = sk.get("SkillDescriptionKey_i18n") or {}
    dmg = sk.get("DamageType")
    out = {
        "skillKey": key,
        "class": cls,
        "nameJa": pick(name_i, "ja-JP"),
        "nameEn": pick(name_i, "en-US"),
        "descJa": pick(desc_i, "ja-JP"),
        "descEn": pick(desc_i, "en-US"),
        "activationType": sk.get("ACTIVATIONTYPE"),
        "activationValue": sk.get("ActivationValue"),
        "slotType": sk.get("SLOTTYPE"),
        "buffType": sk.get("SkillBuffType"),
        "damageType": ELEM.get(dmg, (dmg or "").lower() or None),
        "deliveryType": sk.get("DamageDeliveryType"),
        "range": sk.get("Range"),
        "value": sk.get("Value"),
        "params": [sk.get("Param%d" % n) for n in range(1, 6)],
        # Lv1〜10 のスケーリング。説明文 {0} に入る値（probonk生値）
        "levels": [{"level": lv.get("level"), "value": lv.get("value")} for lv in (sk.get("levels") or [])],
    }
    # null だらけの params 末尾を削る
    while out["params"] and out["params"][-1] is None:
        out["params"].pop()
    return out


def build_passive(p):
    key = p.get("PassiveSkillKey")
    cls = CLASS_BY_DIGIT.get(str(key)[0]) if key is not None else None
    name_i = p.get("SkillNameKey_i18n") or {}
    return {
        "passiveKey": key,
        "class": cls,
        "nameJa": pick(name_i, "ja-JP"),
        "nameEn": pick(name_i, "en-US"),
        "statType": p.get("STATTYPE"),
        "modType": p.get("MODTYPE"),   # FLAT / PERCENT 等
        "value": p.get("Value"),
    }


def main():
    h = fetch("skills")
    active_raw = extract_array(h, "activeSkills")
    passive_raw = extract_array(h, "passiveSkills")

    active = [build_active(s) for s in active_raw if "SkillKey" in s]
    passive = [build_passive(p) for p in passive_raw if "PassiveSkillKey" in p]
    active.sort(key=lambda x: str(x["skillKey"]))
    passive.sort(key=lambda x: str(x["passiveKey"]))

    path = os.path.join(HERE, "tbh-data.json")
    data = json.load(open(path, encoding="utf-8"))
    data["skills"] = active
    data["passiveSkills"] = passive

    # _meta の出典・注記を更新
    meta = data.setdefault("_meta", {})
    src = meta.setdefault("compiledFrom", [])
    if "probonk.com /skills" not in src:
        src.append("probonk.com /skills")
        src.sort()
    meta["skillNote"] = (
        "skills(アクティブ106)/passiveSkills(108) は probonk(実機データマイン)由来。"
        "skillKeyの第1桁=クラス(1ナイト/2レンジャー/3ソーサラー/4プリースト/5ハンター/6スレイヤー)。"
        "levels[]はLv1〜10の生値(説明文{0}に対応)。value/paramsはprobonk内部生値で実機表示と"
        "スケールが異なる場合あり(%系は概ね÷10で整数%)。"
    )

    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    by_cls = {}
    for s in active:
        by_cls[s["class"]] = by_cls.get(s["class"], 0) + 1
    print("active skills:", len(active), "passive:", len(passive))
    print("active by class:", by_cls)
    print("written ->", path)


if __name__ == "__main__":
    main()
