# 出品待ち機能のデータ層を、アプリ最終コードそのまま headless 実行して検証する。
import os, re, json, time, urllib.request

TBH_INV_APPID = "3678970"
HOLD_DAYS = 7
_sell_seen, _sell_known = {}, {}
_sell_state = {"status": "init", "items": [], "ts": 0}

def _detect_steamid():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam\ActiveProcess")
        au = winreg.QueryValueEx(k, "ActiveUser")[0]
        if au:
            return str(76561197960265728 + int(au))
    except Exception:
        pass
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        path = winreg.QueryValueEx(k, "SteamPath")[0]
    except Exception:
        path = r"C:\Program Files (x86)\Steam"
    try:
        vdf = os.path.join(path.replace("/", "\\"), "config", "loginusers.vdf")
        txt = open(vdf, encoding="utf-8", errors="ignore").read()
        best = None
        for m in re.finditer(r'"(7656\d{13})"\s*\{(.*?)\}', txt, re.S):
            sid, body = m.group(1), m.group(2)
            if best is None:
                best = sid
            if re.search(r'"MostRecent"\s*"1"', body):
                return sid
        return best
    except Exception:
        return None

def _sell_fetch():
    sid = _detect_steamid()
    print("detected SteamID64:", sid)
    if not sid:
        _sell_state.update(status="no_steam", items=[]); return
    url = f"https://steamcommunity.com/profiles/{sid}/inventory/json/{TBH_INV_APPID}/2"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        d = json.loads(urllib.request.urlopen(req, timeout=20).read())
    except Exception as e:
        _sell_state.update(status="error"); print("fetch err:", repr(e)); return
    if not d.get("success"):
        err = (d.get("Error") or "").lower()
        _sell_state.update(status="private" if "private" in err else "error")
        print("not success. Error =", d.get("Error")); return
    inv = d.get("rgInventory") or {}
    desc = d.get("rgDescriptions") or {}
    now = time.time()
    items = []
    for a in (inv.values() if isinstance(inv, dict) else []):
        x = desc.get(f"{a.get('classid')}_{a.get('instanceid')}") or {}
        rar = ""
        for t in (x.get("tags") or []):
            if (t.get("category") or "").lower() in ("rarity", "quality"):
                rar = t.get("internal_name") or t.get("name") or ""
        items.append({
            "assetid": str(a.get("id") or a.get("assetid") or ""),
            "name": x.get("name") or x.get("market_hash_name") or "?",
            "icon": x.get("icon_url") or "",
            "tradable": int(x.get("tradable") or 0),
            "marketable": int(x.get("marketable") or 0),
            "rarity": rar,
            "_owner_desc": x.get("owner_descriptions"),   # 検証用: 解除日が公開で見えるか
        })
    _sell_state.update(status=("empty" if not items else "ok"), items=items, ts=now)

_sell_fetch()
print("status:", _sell_state["status"], "count:", len(_sell_state["items"]))
ready = sum(1 for it in _sell_state["items"] if it["tradable"] == 1)
locked = sum(1 for it in _sell_state["items"] if it["tradable"] == 0)
print(f"ready(売れる)={ready}  locked(ロック中)={locked}")
for it in _sell_state["items"][:15]:
    print(f"  trad={it['tradable']} mkt={it['marketable']} rar={it['rarity']:14} {it['name']}")
    if it["_owner_desc"]:
        print("     owner_descriptions:", json.dumps(it["_owner_desc"], ensure_ascii=False))
