#!/usr/bin/env python3
"""TBH ヒーロー基礎ステータス生成スクリプト（probonk.com のゲーム内部データから）

各クラス（ヒーロー）の基礎ステータスを抽出し、tbh-data.json に書き込む:
  - classes[] の各エントリに mainWeapon / subWeapon / baseStats(表示換算) / baseStatsRaw(生値) を付与
  - 新規トップレベル weaponBaseStats: 主武器の gear 種別 → 基礎攻撃速度 等のルックアップ
    （「弓の基礎速度」のような“武器種ごとの基礎値”はこの表で引く。基礎攻撃速度は
      個別装備の属性ではなく、その武器を使うクラスの基礎値である点に注意）

スケーリング（実機表示に合わせる。[[tbh-dps-formula]] / equipStatNote で検証済み）:
  - AttackSpeed / CastSpeed → 生値 ÷100 = attacks(casts)/秒（基礎攻撃速度・基礎詠唱速度）
  - CriticalChance / CriticalDamage → 生値 ÷10 = %（クリダメは合計倍率%表示）
  - AttackDamage / MaxHp / Armor → そのまま（実数）
  検証: Ranger 基礎 AttackSpeed 100→1.0/秒, CriticalChance 40→初期クリ率4%（メモ一致）。

使い方: python3 tbh-fetch-heroes.py
"""
import re, json, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "https://probonk.com/tbh-task-bar-hero/heroes"
GJA = {"SWORD": "剣", "BOW": "弓", "STAFF": "杖", "SCEPTER": "セプター", "CROSSBOW": "クロスボウ",
       "AXE": "斧", "HATCHET": "手斧", "SHIELD": "盾", "ARROW": "矢", "ORB": "オーブ",
       "TOME": "本", "BOLT": "ボルト"}
# 各クラスの基礎ステータスブロック（probonk 生データのフィールド名）
FIELDS = ["AttackDamage", "AttackSpeed", "CastSpeed", "CriticalChance", "CriticalDamage", "MaxHp", "Armor"]
# 表示換算
DIV100 = {"AttackSpeed", "CastSpeed"}
DIV10 = {"CriticalChance", "CriticalDamage"}


def num(v):
    return int(v) if float(v).is_integer() else round(v, 2)


def scale(field, raw):
    if field in DIV100:
        return num(raw / 100)
    if field in DIV10:
        return num(raw / 10)
    return num(raw)


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    h = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")

    # 各ヒーローブロック: ClassType ... MainWeaponGearType ... SubWeaponGearType ... 基礎ステ
    blk = re.compile(
        r'\\"ClassType\\":\\"(\w+)\\",\\"MainWeaponGearType\\":\\"(\w+)\\",'
        r'\\"SubWeaponGearType\\":\\"(\w+)\\",\\"SkillKey\\":(\d+),(.*?)\\"CooldownReduction\\"')
    heroes = {}
    for m in blk.finditer(h):
        cls, mainw, subw, skill, body = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        raw = {}
        for f in FIELDS:
            mm = re.search(r'\\"%s\\":(\-?\d+)' % f, body)
            if mm:
                raw[f] = int(mm.group(1))
        heroes[cls] = {"main": mainw, "sub": subw, "skillKey": int(skill), "raw": raw}
    print("heroes parsed:", list(heroes.keys()))
    if len(heroes) < 6:
        raise SystemExit("解析失敗: ヒーロー数 %d（ページ構造変化の可能性）" % len(heroes))

    dj = os.path.join(HERE, "tbh-data.json")
    d = json.load(open(dj, encoding="utf-8"))

    # 1) classes[] を enrich（nameEn で突き合わせ）
    by_en = {c.get("nameEn"): c for c in d["classes"]}
    weapon_base = {}
    for cls, hv in heroes.items():
        c = by_en.get(cls)
        raw = hv["raw"]
        disp = {f: scale(f, raw[f]) for f in raw}
        base_stats = {
            "攻撃力": disp.get("AttackDamage"),
            "攻撃速度": disp.get("AttackSpeed"),       # attacks/秒（基礎攻撃速度）
            "詠唱速度": disp.get("CastSpeed"),         # casts/秒
            "クリ率": disp.get("CriticalChance"),      # %
            "クリダメ": disp.get("CriticalDamage"),    # %（合計倍率）
            "最大HP": disp.get("MaxHp"),
            "防御力": disp.get("Armor"),
        }
        if c is not None:
            c["mainWeapon"] = hv["main"]
            c["mainWeaponJa"] = GJA.get(hv["main"], hv["main"])
            c["subWeapon"] = hv["sub"]
            c["subWeaponJa"] = GJA.get(hv["sub"], hv["sub"])
            c["baseStats"] = base_stats
            c["baseStatsRaw"] = raw
        # 2) weaponBaseStats: 主武器 gear → 基礎値
        weapon_base[hv["main"]] = {
            "classEn": cls,
            "classJa": (c or {}).get("name", cls),
            "gearJa": GJA.get(hv["main"], hv["main"]),
            "baseAttackSpeed": base_stats["攻撃速度"],   # attacks/秒
            "baseCastSpeed": base_stats["詠唱速度"],
            "baseCritChance": base_stats["クリ率"],
            "baseCritDamage": base_stats["クリダメ"],
            "baseAttackDamage": base_stats["攻撃力"],
        }

    d["weaponBaseStats"] = weapon_base
    d.setdefault("_meta", {})["weaponBaseNote"] = (
        "基礎攻撃速度/基礎クリ等は個別装備ではなく『その武器種を使うクラス』の基礎値（probonk heroes 由来）。"
        "弓=Ranger 基礎攻撃速度1.0/秒 等。装備の攻撃速度%等はこの基礎値に加算/乗算される。"
        "raw値: 攻撃/詠唱速度は÷100=回/秒, クリ率/クリダメは÷10=%。")

    json.dump(d, open(dj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("weaponBaseStats written:", json.dumps(weapon_base, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
