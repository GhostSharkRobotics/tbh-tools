#!/usr/bin/env python3
"""TBH 特殊ステータス(固有効果/UniqueMod)の実テキストを Steam Community Market から取得する。

Steam の market listing render ページ(SSR HTML)には装備のツールチップが丸ごと入っており、
その "Unique Stats" セクションがゲーム内の正式な固有効果テキスト(英語)になっている。
これを各 UniqueMod の代表アイテム(基本は mod が固定される武器/オフハンド)から1件ずつ取得する。

出典: Steam Community Market (appid 3678970)。礼儀として低頻度・低速で利用すること。
出力: tbh-uniquemods-fetched.json (mod -> {item, grade, text})。
"""
import urllib.request, urllib.parse, re, html, time, json, os

APPID = 3678970
HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (personal research cache)"

# mod -> 代表アイテム(英名) と、市場にリスティングがあるグレード(試行順)。
# 原則 mod が固定される武器/オフハンド/ブーツを代表に選ぶ(頭装備はランダム枠なので避ける)。
REPS = [
 ("ArrowRainCriticalCooldown",  "Chaos Bow",            ["Arcana","Immortal","Legendary"]),
 ("AxeSpinBleedingChance",      "Legend Axe",           ["Arcana","Immortal","Legendary","Beyond"]),
 ("ChargeTrapExplosiveCooldown","Dimensional Crossbow", ["Arcana","Immortal","Legendary","Beyond"]),
 ("CrossbowTurretAddAmount",    "Ancient Crossbow",     ["Arcana","Immortal","Legendary"]),
 ("CrossbowTurretCooldown",     "Fast Crossbow",        ["Immortal","Legendary"]),
 ("ExplosiveBoltHalf",          "Complete Crossbow",    ["Arcana","Immortal","Legendary"]),
 ("FlameHydraBerserk",          "Abyssal Staff",        ["Arcana","Immortal","Legendary"]),
 ("IceOrbFreezeToCold",         "Azure Staff",          ["Arcana","Immortal","Legendary"]),
 ("ShieldChargeKillCooldown",   "Ancient Shield",       ["Arcana","Immortal","Legendary"]),
 ("SkewerShotBleedingStrike",   "Ancient Bow",          ["Arcana","Immortal","Legendary","Beyond"]),
 ("SkillBaseAttackCountReduce", "Barrier Shield",       ["Arcana","Immortal","Legendary","Beyond"]),
 ("SkillCooldownReduce",        "Ancient Shield",       ["Arcana","Immortal","Legendary"]),
 ("SkillElementChange",         "Heavy Axe",            ["Arcana","Immortal","Legendary"]),
 ("SkillMultiStrikeCountUp",    "Crimson Shield",       ["Arcana","Immortal","Legendary","Beyond"]),
 ("SkillProjectileCountUp",     "Azure Staff",          ["Arcana","Immortal","Legendary"]),
 ("SlayerLowHpAttackSpeed",     "Dimensional Crossbow", ["Arcana","Immortal","Legendary","Beyond"]),
 ("SnowstormEnhanceFrozenEnemy","Chaos Staff",          ["Arcana","Immortal","Legendary"]),
 ("SorcererLightningShock",     "Witch Staff",          ["Arcana","Immortal","Legendary"]),
 ("WaveMoveFastestPartyMember", "Eternal Helmet",       ["Arcana","Immortal","Legendary"]),
 ("WaveMoveSlowestPartyExcludeSelf","Knight Boots",     ["Arcana","Immortal","Legendary"]),
 ("WhirlwindFireIgnite",        "Steel Axe",            ["Arcana","Immortal","Legendary"]),
 ("WrathOfHeavenHeal",          "Chaos Staff",          ["Arcana","Immortal","Legendary"]),
]

def fetch_html(hn):
    url = (f"https://steamcommunity.com/market/listings/{APPID}/"
           + urllib.parse.quote(hn)
           + "/render/?query=&start=0&count=1&currency=1&country=US&language=english")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def parse_unique(b):
    i = b.find("Unique Stats")
    if i < 0:
        return None
    rest = b[i + len("Unique Stats"):]
    ends = [rest.find(x) for x in ("Decoration Slot", "Engraving Slot", "Inscription Slot") if rest.find(x) >= 0]
    seg = rest[:min(ends)] if ends else rest[:600]
    txt = html.unescape(re.sub(r"<[^>]+>", "", seg))
    lines = [re.sub(r"^[-\s]+", "", l).strip() for l in txt.split("\n")]
    return " ".join(l for l in lines if l) or None

def get_text(nameEn, grades, delay=12.0):
    for g in grades:
        hn = f"{nameEn} ({g}) A"
        for attempt in range(4):
            try:
                b = fetch_html(hn)
                t = parse_unique(b)
                if t:
                    return g, t
                # 200だが item データ無し = ソフトレート制限。待って再試行。
            except Exception as e:
                print(f"   exc {hn}: {e}", flush=True)
            time.sleep(delay * (attempt + 1))
        print(f"   miss {hn}", flush=True)
    return None, None

def main():
    print("cooldown 60s before start...", flush=True)
    time.sleep(60)
    out = {}
    for mod, name, grades in REPS:
        g, t = get_text(name, grades)
        out[mod] = {"item": name, "grade": g, "text": t}
        print(f"{mod:32s} [{name} {g}] -> {t}", flush=True)
        time.sleep(12)
    p = os.path.join(HERE, "tbh-uniquemods-fetched.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", p, flush=True)

if __name__ == "__main__":
    main()
