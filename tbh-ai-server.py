#!/usr/bin/env python3
"""
TBH ローカルAIサーバ（このデバイス専用）
------------------------------------------------
公開している tbh-build-simulator.html から呼ばれ、`claude -p` を使って
自然言語の指示からビルド（盛りステータス）を提案する。

- localhost:8765 のみで待ち受け（外部公開しない）
- `claude -p` はこのMacのClaude契約で動く＝API従量課金なし
- 起動していない他デバイス/一般訪問者からは到達しないので、AI機能は出ない

使い方:
    python3 tbh-ai-server.py
そのうえで:
    - このデバイスで http://localhost:8765/ を開く（確実に同一オリジンで動く）
    - もしくは公開ページ(github.io)を開けば、自動でローカルサーバを検出してAIパネルが出る
      （Chrome系。Safariはmixed-content制限で出ない場合あり→localhost直開きで確実）
"""
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8765
APPID = "3678970"  # Task Bar Hero on Steam

# 1件だけライブ価格を取りに行く用の軽いキャッシュ（同じhashの連打でSteamを叩かない）
_PRICE_CACHE = {}          # hash -> (epoch_sec, result_dict)
_PRICE_TTL = 120           # 秒。これより新しければキャッシュを返す
CLAUDE = next((p for p in [str(Path.home() / ".local/bin/claude"),
                           "/opt/homebrew/bin/claude", "/usr/local/bin/claude"]
               if Path(p).exists()), "claude")
TIMEOUT = 300

PROMPT = """あなたは放置ハクスラ「Task Bar Hero (TBH)」のDPSビルドシミュレーター用のビルドを設計します。

DPS式:
DPS = 攻撃力 × 攻撃速度 × (1 + クリ率 × (クリダメ/100 − 1)) × (1 + ダメージ種別%/100) × バフ(力の祝福)
- クリダメはゲーム表示の「合計倍率%」。例: 242% はクリ時2.42倍。宝石/刻印の「クリダメ+X%」はこの合計%に加算（242→267 など）。
- 係数%（攻撃力係数/攻撃速度係数/クリ率係数/クリダメ係数）は基礎値への乗算。

各部位に積める盛りステータス（stat名: 単位）:
攻撃力=実数, 攻撃力係数=%, 攻撃速度=%, クリ率=%, クリ率係数=%, クリダメ=%, クリダメ係数=%, 物理ダメージ=%, 火炎ダメージ=%, 冷気ダメージ=%, 雷ダメージ=%, カオスダメージ=%

部位インデックス: 0=武器,1=オフハンド,2=頭,3=胴,4=手,5=足,6=首飾り,7=イヤリング,8=指輪,9=腕輪

必ず ./tbh-data.json（装飾/宝石/彫刻/刻印の実数値・色×部位で効果が変わる）と ./tbh-prices.json（Steam中央値）を Grep/Read で参照し、実在するアイテムで裏付けること（巨大なので検索推奨・全文読みしない）。slotStats の数値は、推薦した実アイテムの効果量と整合させる。
特定ステージ攻略向けの指示（例「Act2のHELLで死ぬ」）なら、tbh-data.json の stages[]（{act,no,difficulty,boss,enemies}）と enemies[]（{nameJa,element,atk,hp,...}）を引き、敵の element に対する耐性や防御も考慮して提案・picks に反映する。
クラス固有の事情が効く場合は classes[]・skills[]（アクティブ、class名で紐づく）・passiveSkills[]（{class,statType,modType,value}）も参照し、そのクラスの攻撃属性(attackElement)やスキルのdamageTypeに合うダメージ種別・ステを優先する。DB に無い情報は WebSearch で補ってよいが、DB の数値が優先。

現在のビルド状態(JSON):
%%STATE%%

ユーザーの指示:
%%REQUEST%%

出力は説明文を一切付けず、次の形のJSONオブジェクトのみ:
{"base": {"ad":数値, "adc":数値, "as":数値, "asc":数値, "cc":数値, "ccc":数値, "cd":数値, "cdc":数値}, "slotStats": {"0":[{"stat":"攻撃速度","val":5,"cnt":2}]}, "picks":"Markdown文字列", "note":"日本語で短い総括"}
- base は変更したいフィールドだけ含めればよい（省略可）。
- slotStats は現在の部位ごと盛りを丸ごと置き換える。cnt 省略時は1。stat は上記リストの名前のみ使う。装飾枠は装備レアリティで1〜2、加えて彫刻・刻印が現実的な範囲。
- picks は「具体的なおすすめ装飾」を部位別にMarkdownで。各アイテムは 日本語名(英語名)・レアリティ・付与stat+数値・分かれば中央値$ を明記。なぜそれかを一言。uncertain:true のデータは断定せず注記。表(Markdown table)推奨。
- Steamリンク: tbh-prices.json の prices のキー（=Steamのmarket_hash_name。例 "Composite Bow (Legendary) A"）に一致するアイテムは、英語名部分をそのキーへのMarkdownリンクにする: `[英語名](https://steamcommunity.com/market/listings/3678970/<キーをURLエンコード>)`（スペース→%20, (→%28, )→%29, '→%27）。prices に無い（market=false等で取引不可・相場なし）アイテムはリンクを捏造せずプレーンテキストのままにする。
"""


def extract_json(text):
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


CHAT_PROMPT = """あなたは放置ハクスラ「Task Bar Hero (TBH)」のアイテム/ビルド/攻略に詳しいアシスタントです。
このフォルダの ./tbh-data.json と ./tbh-prices.json（Steam相場）を必要に応じて Grep/Read で参照し、根拠のある回答をしてください（巨大なので全文読みせず検索推奨）。
tbh-data.json の主なキー:
- gems / engravings / inscriptions / equipment / uniqueMods: 装備・装飾の実数値（装飾は「色×部位(武器/防具/アクセ)」で効果が変わる）
  ※equipment[].market = Steamマーケット取引可否。false の装備(Lv25/35/45/55/60/70/75/85/90, およびUncommon以上TypeB)はVer1.00.07(2026-06-02)でSteam負荷対策により市場削除。ただし**ゲーム内には存在し所持・使用は可**(新規入手・合成・取引のみ不可)。市場価格や入手前提の話では market=false を「取引不可・相場なし」として扱い、所持済み前提のビルド相談では使用可として扱う。
- classes[]: {name(クラス名), nameEn, role, primaryStats, attackType, attackElement(physical/elemental), mainWeapon/subWeapon(gear種), baseStats(基礎攻撃力/攻撃速度(回/秒)/詠唱速度/クリ率/クリダメ/最大HP/防御力), baseStatsRaw(生値), notes} — 6クラス
- weaponBaseStats: 主武器gear種別(SWORD/BOW/STAFF/SCEPTER/CROSSBOW/AXE)→{classEn, gearJa, baseAttackSpeed(回/秒), baseCritChance, baseCritDamage, baseAttackDamage}。**基礎攻撃速度は個別装備でなく『その武器種を使うクラス』の基礎値**（例: 弓BOW=Ranger=1.0回/秒）。装備の攻撃速度%等はこの基礎値に加算/乗算される。「弓の基礎速度は？」等はここを引く
- skills[]: {skillKey, class(クラス名ja), nameJa, nameEn, descJa, descEn, activationType, slotType, buffType, damageType, deliveryType(Melee/Ranged), range, value, params, levels} — アクティブスキル。class フィールドでクラスに紐づく
- passiveSkills[]: {passiveKey, class, nameJa, nameEn, statType, modType(FLAT/PERCENT), value} — クラス別パッシブのステ強化
- stages[]: {key, act(章1-3), no, level, difficulty(NORMAL/NIGHTMARE/HELL/TORMENT), boss(敵key), enemies[](敵key配列), expectedGold, expectedExp}
- enemies[]: {key, nameJa, nameEn, type, atk, atkSpeed, hp, moveSpeed, element(physical/fire/cold/lightning/chaos), gold, exp}
- 【キューブ(Cube)】クラフト装置で、キャラとは別に『キューブ自身のレベル』を持つ。質問に「キューブ」とあれば必ずこのキューブの話（キャラレベルやステージ周回に読み替えない）。
  - キューブEXPは『キューブにアイテムを投入する』ことで入る（錬金/合成/捧げ物等）。入るEXP量は投入アイテムの**グレード**で決まり、ステージや個数効率より桁で効く。
  - progression.cubeLevelExp[] = キューブのLv別必要EXP（例 Lv51→52 = 967,250）。crafting.gradeExp = グレード別の獲得キューブEXP(cubeExp)とalchemyGold（COMMON2…ARCANA518…COSMIC71089）。crafting.cubeLevels = 累積EXPの節目。grades[].BaseCubeExp も同値。
  - キューブレベルは高グレード合成の解放条件にもなる（イモータル合成=Lv10, セレスティアル合成=Lv50 等）。
  - 既知の仕様だがデータに数式が無い点: 「キューブレベルより高いレベルの装備を投入してもキューブEXPが入らない（=自分のキューブLv帯までの装備でしかEXPは伸びない）」。この手の“データに式が無い仕様”は創作で補わず、分かる範囲＋ユーザー申告を前提に答える。
クラス/スキルの質問（例「ナイトのおすすめスキルは？」「レンジャーで火力が上がるパッシブは？」）では classes/skills/passiveSkills を class 名で絞って答える。
「このステージで死ぬ、どんな装備？」のような攻略質問では、該当 stage を特定し、その boss/enemies の key を enemies から引いて、敵の element（→対応する耐性を優先）・atk・hp を見て、防御/属性耐性/早期撃破(火力)の観点で具体的に助言する。stage は act・no・difficulty で指定されることが多い。
データに無い最新情報や一般的な攻略は WebSearch/WebFetch で調べてよいが、tbh-data.json に数値があるものは必ずDB優先（ネット情報より実データを信頼）。情報源がネットの場合はその旨を明記。
DPS式: DPS = 攻撃力 × 攻撃速度 × (1 + クリ率 × (クリダメ/100 − 1)) × (1 + ダメージ種別%/100) × バフ。クリダメはゲーム表示の「合計倍率%」。
回答ルール:
- 【最優先】ユーザーが明示した前提・用語・手段を絶対に尊重する。勝手に読み替えたり否定して別の話にすり替えない。
  - 用語: 「キューブ」と言われたらキューブの話。キャラのレベルやステージに勝手に置き換えない。指す対象が曖昧なら推測で進めず一言で聞き返す。
  - 手段の縛り: 「ステージ周回で」「クラフトで」のように手段を指定されたら、その枠の中だけで答える。自分が別手段の方が良いと思っても、まずユーザー指定の手段で具体的に答えること。
  - 否定された前提は蒸し返さない: ユーザーが「それで合ってる」「ステージで出る」等と訂正・断言したら、その前提を受け入れて続ける。再反論しない。
  - 代替案は、ユーザー指定の手段にきちんと答えた『後』に、1行だけ「他にXもある」と添える程度に留める（求められなければ不要）。
- データに無い仕様（例: キューブのレベル上げ機構）を聞かれたら、数値や式を創作しない。「データに無い」と正直に言い、ユーザーが述べた事実(箱ドロップ等)を前提に答えるか、分かる範囲だけ答える。
- 質問と同じ言語で、簡潔に（前置き不要、結論から）。
- アイテム名は 日本語(英語) 併記。価格に触れるなら中央値 $ を添える。
- Steamリンク: tbh-prices.json の prices のキー（=Steamのmarket_hash_name。例 "Composite Bow (Legendary) A"）に一致するアイテムは、英語名部分をそのキーへのMarkdownリンクにする: `[英語名](https://steamcommunity.com/market/listings/3678970/<キーをURLエンコード>)`（スペース→%20, (→%28, )→%29, '→%27）。prices に無い（market=false等で取引不可・相場なし）アイテムはリンクを捏造せずプレーンテキストのままにする。
- 装飾(宝石)は「色×部位(武器/防具/アクセ)」で効果が変わる点に注意。
- uncertain:true など不確実なデータは断定しない。

質問:
%%Q%%
"""


def build_optimize_prompt(body):
    req = (body.get("request") or "").strip() or "DPS最大化のビルドを提案して"
    if (body.get("session_id") or "").strip():  # 会話継続: 追加指示のみ
        return ("追加の指示: " + req +
                "\n前回と同じJSON形式（base/slotStats/picks/note）のオブジェクトだけで返答して。"
                "必要なら tbh-data.json / tbh-prices.json を再参照してよい。")
    return PROMPT.replace("%%STATE%%", json.dumps(body, ensure_ascii=False)).replace("%%REQUEST%%", req)


def build_chat_prompt(body):
    q = (body.get("question") or "").strip()
    if not q:
        raise RuntimeError("質問が空です")
    if (body.get("session_id") or "").strip():  # 会話継続: 質問だけ送る（文脈は保持済み）
        return q
    return CHAT_PROMPT.replace("%%Q%%", q)


def _progress(ev):
    """stream-json イベント → 人間向けの進捗テキスト（無ければ None）"""
    t = ev.get("type")
    if t == "system" and ev.get("subtype") == "init":
        return "🚀 AIを起動中…"
    if t == "assistant":
        for b in ev.get("message", {}).get("content", []):
            bt = b.get("type")
            if bt == "tool_use":
                name = b.get("name", "")
                inp = b.get("input", {}) or {}
                if name == "Read":
                    return "📖 " + os.path.basename(str(inp.get("file_path", ""))) + " を読み込み中"
                if name == "Grep":
                    return "🔎 データ内検索: 「" + str(inp.get("pattern", ""))[:48] + "」"
                if name == "Glob":
                    return "🗂 ファイルを探索中"
                if name == "WebSearch":
                    return "🌐 ネット検索: " + str(inp.get("query", ""))[:48]
                if name == "WebFetch":
                    return "🌐 ページ取得: " + str(inp.get("url", ""))[:60]
                if name == "Bash":
                    cmd = str(inp.get("command", ""))
                    if "tbh-prices" in cmd:
                        return "💰 相場データを照会中"
                    if any(w in cmd for w in ("enem", "stage", "boss", "敵", "ステージ")):
                        return "👹 敵・ステージデータを照会中"
                    if any(w in cmd for w in ("skill", "passive", "class", "スキル", "クラス", "パッシブ")):
                        return "🧙 クラス・スキルデータを照会中"
                    if "tbh-data" in cmd:
                        return "📖 アイテムデータを照会中"
                    return "🛠 データを照会中"
                return "🛠 " + str(name) + " 実行中"
            if bt == "text" and b.get("text", "").strip():
                return "💭 考えています…"
    return None


def stream_claude(prompt, emit, resume=None):
    """claude を stream-json で起動。進捗を emit(text)、最終 (result, session_id) を返す。"""
    cmd = [CLAUDE, "-p", prompt,
           "--dangerously-skip-permissions",
           "--allowedTools", "Read,Grep,Glob,WebSearch,WebFetch",
           "--output-format", "stream-json", "--verbose"]
    if resume:
        cmd += ["--resume", resume]
    proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, bufsize=1)
    result, session_id = "", (resume or "")
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("session_id"):
                session_id = ev["session_id"]
            msg = _progress(ev)
            if msg:
                emit(msg)
            if ev.get("type") == "result":
                result = ev.get("result", "") or result
    finally:
        proc.wait()
    if proc.returncode not in (0, None) and not result:
        err = proc.stderr.read() if proc.stderr else ""
        raise RuntimeError(err.strip() or "claude failed")
    return result, session_id


_MONEY = re.compile(r"[\d.,]+")


def _money_to_cents(s):
    """'$71.76' / '71,76€' などの価格文字列をUSDセント(int)に。失敗時 None。"""
    if not s:
        return None
    m = _MONEY.search(s.replace(",", "."))
    if not m:
        return None
    try:
        return int(round(float(m.group(0)) * 100))
    except ValueError:
        return None


def fetch_steam_price(hash_name):
    """Steam公式 priceoverview から1アイテムだけライブ相場を取得。
    全件は叩かず、ユーザーがクリックした1件だけを都度取得する（Steamに優しい）。
    返り値: {ok, sell, median, volume, fetchedAt} （sell/medianはUSDセント）。"""
    hn = (hash_name or "").strip()
    if not hn:
        return {"ok": False, "error": "empty hash"}
    now = time.time()
    hit = _PRICE_CACHE.get(hn)
    if hit and now - hit[0] < _PRICE_TTL:
        return hit[1]
    url = ("https://steamcommunity.com/market/priceoverview/"
           "?appid=" + APPID + "&currency=1&market_hash_name=" + urllib.parse.quote(hn))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (TBH price refresh)"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        msg = "Steam混雑(429) — 少し待って再試行" if e.code == 429 else f"Steam {e.code}"
        return {"ok": False, "error": msg}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"取得失敗: {e}"}
    if not d.get("success"):
        # success=false は「出品なし/相場なし」。市場ページは存在し得る。
        out = {"ok": True, "sell": None, "median": None, "volume": 0,
               "fetchedAt": int(now), "empty": True}
        _PRICE_CACHE[hn] = (now, out)
        return out
    vol = 0
    try:
        vol = int(str(d.get("volume", "0")).replace(",", ""))
    except ValueError:
        vol = 0
    out = {
        "ok": True,
        "sell": _money_to_cents(d.get("lowest_price")),
        "median": _money_to_cents(d.get("median_price")),
        "volume": vol,
        "fetchedAt": int(now),
    }
    _PRICE_CACHE[hn] = (now, out)
    return out


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        route = self.path.split("?")[0]
        if route == "/health":
            return self._json({"ok": True})
        if route == "/price":
            q = urllib.parse.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
            hn = (q.get("hash") or [""])[0]
            return self._json(fetch_steam_price(hn))
        self._serve_static()

    def do_POST(self):
        route = self.path.split("?")[0]
        if route not in ("/optimize", "/chat"):
            self.send_response(404); self._cors(); self.end_headers(); return
        # Server-Sent Events: 進捗をリアルタイムに流す
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def send(obj):
            try:
                self.wfile.write(("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            resume = (body.get("session_id") or "").strip() or None
            prompt = build_chat_prompt(body) if route == "/chat" else build_optimize_prompt(body)
            text, sid = stream_claude(prompt, lambda m: send({"progress": m}), resume=resume)
            if route == "/chat":
                result = {"answer": text.strip()}
            else:
                obj = extract_json(text)
                if obj is None:
                    raise RuntimeError("claudeの出力からJSONを取り出せませんでした")
                obj.setdefault("note", ""); obj.setdefault("picks", "")
                result = obj
            send({"done": True, "result": result, "session_id": sid})
        except Exception as e:  # noqa: BLE001
            send({"error": str(e)})

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self):
        rel = self.path.split("?")[0].lstrip("/") or "tbh-build-simulator.html"
        f = (ROOT / rel).resolve()
        if not str(f).startswith(str(ROOT)) or not f.is_file():
            self.send_response(404); self._cors(); self.end_headers(); return
        ctype = {".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8",
                 ".js": "text/javascript", ".css": "text/css"}.get(f.suffix, "application/octet-stream")
        data = f.read_bytes()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # 静かに
        pass


if __name__ == "__main__":
    print(f"TBH AI server → http://localhost:{PORT}/  (claude: {CLAUDE})")
    print("停止: Ctrl+C")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
