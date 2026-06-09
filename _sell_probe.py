import urllib.request, urllib.error, json

sid = 76561198009427740
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"

def raw(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")

for app, ctx in [(3678970, 2), (3678970, 6), (3678970, 1), (753, 6)]:
    url = f"https://steamcommunity.com/profiles/{sid}/inventory/json/{app}/{ctx}"
    try:
        txt = raw(url)
    except Exception as e:
        print(f"\n=== {app}/{ctx}: ERR {e!r}")
        continue
    try:
        d = json.loads(txt)
    except Exception:
        print(f"\n=== {app}/{ctx}: non-json head:", txt[:200]); continue
    succ = d.get("success")
    inv = d.get("rgInventory") or {}
    desc = d.get("rgDescriptions") or {}
    print(f"\n=== {app}/{ctx}: success={succ} rgInventory={len(inv) if isinstance(inv,dict) else inv} rgDescriptions={len(desc) if isinstance(desc,dict) else desc}")
    if isinstance(d, dict) and not succ:
        print("   keys:", list(d.keys()), "| Error:", d.get("Error"))
    # 最初のdescriptionを丸ごと（tradable/owner_descriptions等のフィールド名を見る）
    if isinstance(desc, dict) and desc:
        first = next(iter(desc.values()))
        print("   FIRST DESC KEYS:", list(first.keys()))
        print("   FIRST DESC:", json.dumps(first, ensure_ascii=False)[:1800])
