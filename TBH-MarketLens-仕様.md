# TBH MarketLens — 仕様書（スレッドをまたぐ唯一の真実）

> 新しいスレッドで作業する前に必ずこれを読む。コードの推測で動かない。
> 本体: `tbh-price-ocr.py`（pythonw常駐・タスクトレイ・tkinterポップ）。配信名 **Ghost Shark Robotics**。現行 v1.1（未公開）。

## 1. 概要
ゲーム「TBH: Task Bar Hero」(`taskbarhero.exe`, Steam appid `3678970`)用の常駐ツール。
アイテムにカーソルを合わせ**発動キー**（既定=マウスのサイドボタン「戻る」。設定で自由割当）を押すと、
画面の名前領域をOCR→既知アイテムへ曖昧マッチ→**Steam市場価格をカード型ポップで表示**。タイピング不要。
ゲームには一切干渉しない（別プロセスで画面OCR＋ホットキーのみ＝チート非検出。[[tbh-tools-no-cheat-detection]] 厳守）。

## 2. 配備手順（最重要・これを外すと「何も変わらない」が再発）
Windows実機(Tailscale `ssh tbhwin`, 鍵`~/.ssh/tbh_win`, 配備先`C:\Users\monoq\tbh-price-ocr\`)へ。
**必ずこの順序**：
1. `ssh tbhwin "taskkill /f /im pythonw.exe"`（**先に殺す**。稼働中はファイルロックでscpが黙って失敗→旧版が動き続ける＝過去最大の消耗源）
2. `scp -i ~/.ssh/tbh_win tbh-price-ocr.py tbhwin:tbh-price-ocr/tbh-price-ocr.py`
3. **ハッシュ照合**：`md5 -q`(ローカル) と `certutil -hashfile ... MD5`(リモート) が一致するまで確認。`>/dev/null`でscpのエラーを握り潰さない
4. schtasks(`/it`対話デスクトップ)で起動 → `tasklist|findstr pythonw` が**単一PID**・`error.log`無し(NO_ERROR)を確認
変更したら**毎回pushして公開URLにも反映**（[[tbh-deploy-to-live]]）。デプロイ前に `python3 i18n_lint.py` 必須。

## 3. ファイル構成（repo root。tools/はgitignoreのためroot配置）
- `tbh-price-ocr.py` … 本体
- `tbh-price-lookup.json` … 全アイテムの名前索引＋バンドル価格（USD, `cur:1`）。`tbh-build-price-lookup.py`が生成（`tbh-data.json`＋`tbh-prices.json`＋`localization.json`の中国語名＋`market-icons.json`から）
- `frame_tpl.png` … 名前枠の左角テンプレート。**TBHのUI倍率「2x」で撮った固定ピクセル＝倍率1.0の基準**。検出は`detect_boxes`で**UI倍率1x/1.25x/1.5x/2x/3x（解像度で実ピクセルが変わる）に自動追従**＝再キャリブレーション不要。要点：
  - **倍率f自動検出**：テンプレ側を多倍率にリサイズ(`_SCALE_GRID`)して相関最大の倍率`f`を選ぶ(`_best_template_factor`)。クロップ座標・クラスタ閾値は全て`f`倍。
  - **速度**：探索は`_SEARCH_MAXW`(=1100px)以下へ縮小した画像で実施（3x等の大画像でも軽い）。直近当選倍率は`_SCALE_CACHE`に保持し、まずそれだけ照合→相関`>=_SCALE_STRONG`なら**1回で即確定**（倍率を変えた直後だけ全grid走査）。倍率非依存でほぼ一定速度。
  - **OCRは必ずベース文字サイズへ正規化**：`_ocr`/`_adapt`(BoxBlur半径固定)は2xの文字サイズ前提。crop を `1/f` 倍してからOCRに渡す。**これを外すと小さいUI倍率で枠は当たるのにOCRが空＝該当なしになる**（実機で確定した落とし穴）。
- `tbh_price_match.py` … OCR文字→既知名の曖昧スナップ（stdlibのみ。`open`は`encoding=utf-8`必須＝Win cp932対策）
- `i18n_lint.py` … TR(文言カタログ)完全性＋UIに日本語直書きが無いかをAST検査
- `start-tbh-price.bat` / `tbh-price-ocr.ps1`(irm|iex導入) / `dist-README.md`(配布用)
- 価格は日次GitHub Actionsで全自動更新（[[tbh-price-autoupdate-actions]]）。手動取得不要

## 4. 価格取得の仕様（最も誤解されやすい・実機検証済み 2026-06）
**結論：表示通貨が¥/¥なら priceoverview の現地通貨を優先、ダメなら search/render の単品USD（為替換算）。**

- **priceoverview**（`/market/priceoverview/`, 現地通貨¥を返す）は時期により429のことがある（429時はsearch/renderにフォールバック）。**動いている時は現地¥の正確値**。
  - **重要（在庫なし判定）**：在庫が無い品は `lowest_price`(現在の最安＝買える価格)が**返らず**、`median_price`(過去の中央値)と`volume`だけ返る。
    **`lowest_price`無し＝現在出品0件＝最安は「出品なし」**。`apply_live`は `low is None` で `ent["_nolist"]=True`＋`ent["sell"]=None`。
    ただし **`median_price`(過去の中央値)があれば中央値は表示する**（UIは「最安 出品なし／中央値 ¥X」）。medianは`ent["median"]`に、通貨は`ent["cur"]=src`で入れる。
    **`sell`(USDバンドル値)を残したまま `cur=¥` にすると USDセントが現地通貨扱いになり¥31/¥1等の誤値**が出る（実機で確定した過去の不具合）。だから出品なし時は必ず `sell=None`。
- **search/render**（`/market/search/render/`）が**本線**。`_render_price()`が**品名+レア度クエリ**で叩き、その変種の現在USDを**1リクエストで取得**。429になりにくい＝**BANされない**。
  - クエリは**記号除去必須**：`-`はSteam検索の除外演算子で誤爆。`"War Bow (Legendary) A"→"War Bow Legendary"`、`"Soulstone - Torment"→"Soulstone Torment"`
  - **USD固定**（currency/country パラメータ無視）。**10件/ページ固定**（全624種の一括取得は63req必要＝非現実的。だから単品クエリ方式）
  - **出品なし vs 取得失敗を区別**（`_render_price`は3値：`(usd,listings)`=出品あり／`_RENDER_EMPTY`=クエリ成功で該当変種なし＝**現在出品なし**／`None`=429・通信エラー）。
    - 出品なし→`apply_live`が`ent["_nolist"]=True`にしUIは**「出品なし」(`nolisting`)を表示**。バンドルの小額(例¥6)を価格として出さない（過去の不具合：未出品でも¥6等の変な値が出た）。
    - 取得失敗(None)→**バンドル(集計USD)価格を保持**（出品なしと断定しない）。`_nolist`は出品なしキャッシュ`(now,None,0)`に保存し再取得を抑制。`_live`同様に履歴へは永続化しない。
- **通貨**：`_CURRENCY = {en:1=USD, ja:8=JPY, zh:23=CNY}`（UI言語に連動）。
  - en(USD)＝search/renderの値そのまま＝**Steamと完全一致の正確値**
  - ja/zh(¥)＝Steamが¥を出さないので**USDを為替換算**（`JPY_RATE/CNY_RATE`, `fetch_rate()`がopen.er-api.comで起動時更新）。数円ズレ得る
- **表示は印を付けない**：以前 `≈`/`🕓`/グレーを付けたら「壊れ・オフライン・BAN」に見えると却下された。
  **価格は普通の色で堂々と「¥29」「$0.19」**と出す（`price(c, src)`は印なし）。
- **キャッシュ**：render=5分(`_render_cache`)、native=5分(`_price_cache`)。バックオフは**render用`_render_blocked`とnative用`_rl_blocked`を分離**（native429がrenderを止めないため）。
- 主要関数：`_render_price`(単品USD) / `_native_price`(priceoverview¥) / `live_price(...)→(low,med,vol,src)` / `apply_live(ent,...)`(ent書換＝sell/median/volume/cur/_live)

## 5. UI仕様
**レンズ・ポップ**（`show_popup`）:
- overrideredirect + Win11角丸。**NOACTIVATE+keep_on_topでフルスクリーンゲームの前面に常駐**（透過/フォーカス奪取は消える原因なので不可）。外側クリック/ホバーアウト/無操作6秒(`POPUP_SECONDS`)で閉じる。✕は右上角。
- **読み取り中**＝スピナー回転（静止文字にしない）。
- **マッチ時**＝アイテム名／レア度ドロップダウン（選び直しで再マッチ）／価格（安値・中央）／種別・出品数／🛒Steam市場／🕘履歴。
- **該当なし時**＝**「該当なし」＋🕘履歴＋✕ だけ**。文字化けの生OCR・レア度・価格・🛒は**一切出さない**（開く先の無いボタンを出さない）。

**履歴ウィンドウ**（`show_history`, トレイでオン/オフ, `tbh-price-history.json`永続化, 位置/サイズ記憶）:
- 行：アイコン（CDN`/96x96`をmd5名でローカルキャッシュ。無い品はレア度色タイル）／名前・レア度／価格／種別／**右下に追加日時**（`rec["ts"]`=`_stamp_str()` 年なし「M/D H:M」）。右クリックで お気に入り・名前変更・レア度変更・削除。上限設定(既定50, お気に入りは対象外)。
- **並べ替え**：ヘッダにpill「追加日(`sort_added`)/最安(`low`)/中央値(`med`)」。単一選択・選択中を再タップで昇順⇄降順(▼/▲)。`_hist_sort`/`_hist_sort_desc`（設定永続）。`_hist_ordered()`が並べ替え（**お気に入りは常に上／価格なしは常に末尾**）。価格ソート中の新規レンズは増分挿入でなく全再構築（正しい位置へ）。
- ヘッダの更新ボタン下に**現在日時を1つ**（`_hist_now`=`_now_str()` 年あり、20秒毎更新）。
- **全部更新ボタン**：押すと**ボタンにスピナー＋「12/50」件数**、ヘッダー下に**進捗バー**（緑=取得済、render待機中はアンバーの流れる帯＋⏳残り秒）、**各行は更新時に一瞬フラッシュ**、完了で✓。連打は無視(`_hist_updating`)、言語切替/再押下で世代`_hist_gen`が古い取得を中断。
- レンズ中は最新1件だけ増分反映(`_hist_sync_top`)＝全消ししない（チラつき防止）。
- **状態は文章でなくUIで見せる**のが鉄則（ユーザー強い要望。[[tbh-ux-principles]] [[tbh-compact-display-principle]]）。

**出品待ちウィンドウ**（`show_sell`, トレイ「出品待ち」でオン/オフ, 位置/サイズ記憶, 状態`tbh-sell-state.json`永続化）[[marketlens-sell-timer]]:
Steam在庫の出品ホールドを追跡し、出品可になったら通知。**実機検証で確定（推測禁止・2026-06）**:
- SteamID自動検出：`HKCU\…\Steam\ActiveProcess\ActiveUser`＋76561197960265728（FB=loginusers.vdfのMostRecent）。ユーザー入力不要＝配布時も各PC自動（`_detect_steamid`）。
- 取得は**新inventory API** `inventory/{sid}/3678970/2?l=..&count=2000`（assets/descriptions）。**インベントリ「公開」必須**：公開=200／非公開=**403**（旧`/inventory/json/`は公開だと逆に403で使えない）。403→`status=private`で「🔓公開設定を開く」(`/profiles/{sid}/edit/settings`)導線。
- **正確な解除日は公開データに無い**（owner限定でCookie必要／クライアントcookieは排他ロックで自動取得不可＝VSS管理者権限要・配布不向き）。よって `marketable`フラグ＋「初めて出品不可を見た時刻+7日(HOLD_DAYS)」の**推定残り日数**＋**0→1のflipをトレイ通知**で構成（`_sell_fetch`/30分`_sell_poller`）。
- 表示：🟢売れる／🕒解除日ごと（≈M/D・あとN日）にまとめ、同名は×個数集約。状態は文章でなくUIで（[[tbh-ux-principles]]）。
- **制約**：TBH出品が一時停止中は在庫が全て marketable:0＝追跡対象の実ホールド無し→本番検証は市場再開後。機能は完成・配備済みで再開時に自動で効く（一時条件で諦めない [[dont-abandon-on-temporary-conditions]]）。

**設定**（トレイ→設定）: 表示言語(ja/en/zh, 起動時PC言語自動取得)／発動キー割当(欄クリック→任意キー/組合せを押す、実況表示)／**Windowsと一緒に起動**(トグル)。`tbh-price-settings.json`永続化。初回起動で使い方画面。
- **自動起動**は `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`(管理者不要)。**レジストリ自体が真実＝設定jsonに持たない**（トグルは`_autostart_get/_set`でRunキーを直接読み書き、既定オフ）。コマンドはexe化時=`sys.executable`単体／.py時=`pythonw + script`。起動毎に`_autostart_refresh()`が有効なら現在パスで貼り直す（フォルダ移動・バージョン更新でパスが変わっても効き続ける）。

**配信系**: フッターに `v1.1 · by Ghost Shark Robotics`、Ko-fi寄付(`KOFI_URL`)、アプリ内フィードバック(`FEEDBACK_URL`→Cloudflare Worker→Slack, 匿名・返信先任意)。起動時にGitHub最新リリースを確認し新版を控えめ告知。

**利用統計（匿名テレメトリ）** [[marketlens-telemetry]]: `STATS_URL`(=Worker `/ml`)へ `_telemetry_send(ev,item,rarity,err)` が送信。`ev=launch`(main・言語確定後)／`lookup`(found確定時・アイテム英名+rarity_en)／`error`(`log_fatal`本文・`_scrub()`でユーザー名/パス伏字化)。匿名ID `_cid`(uuid4・設定に永続・IP由来でない)。**IP・Steam在庫・個人情報は送らない**(国はWorkerがエッジで付与・IP非保存)。設定→「利用統計」トグル(`_telemetry`, 既定オン)でオフ可。閲覧: `…/mlstats?pw=<DASH_PW>`。dist-READMEに開示済み。

## 6. i18n（多言語対応＝必須要件。「言われたらやる」ではない）
**ja / en / zh の3言語すべてが第一級。** 中国が最大ユーザー層なので zh を「未収録→英語でOK」で済ませない＝それは未完成。
新しい機能・文字列・ボタン・トレイ項目・ダイアログを足したら、**その時点で必ず ja/en/zh の3つを揃える**（後回し・別TODO化しない）。

- 全UI文字列は `TR[lang][key]` ＋ `T(key, **fmt)` 経由。`LANGS=("ja","en","zh")`。日本語直書き禁止。
- **データ由来のラベルも対象**：レア度(`disp_rarity`)・種別(`disp_type`)等は現状 zh で英語にフォールバックしている＝**未対応の穴**。zh の rarity/type 訳を用意して埋める（lookup側に `rarity_zh`/`type_zh` を持たせ、`disp_*` を zh 対応にする）。`localization.json` に game の zh-hans 名がある。
- **デプロイ前に `python3 i18n_lint.py` 必須**（TRカタログ完全＋UIに日本語直書きが無いか）。
  カタログ検査を通っても**データ由来の zh 漏れは別途目視/テストで確認**（lintの死角。将来 lint を拡張してここも落とすこと）。
- 参照: [[marketlens-i18n]]

## 7. 既知の制約・落とし穴
- Steamの¥(priceoverview)は現在取得不可＝¥は為替換算の概算。正確値が要るなら英語(USD)。これはSteam側都合でアプリの不具合でない。
- search/renderは10件/ページ・USD固定。全件一括は非現実的（単品クエリで運用）。

※ 作業の進め方（配備時の確認・公開前の確認・git運用など）はアプリ仕様ではないのでここには書かない。メモリ(feedback)を参照。

## 8. 状態（2026-06時点）
価格本線=search/render切替・印なし表示・該当なし最小表示まで実装＆実機反映済み。
匿名テレメトリ(`/ml`+`/mlstats`)をコード実装済み＝ローカル検証(py compile/i18n_lint/node --check)通過。
出品待ち機能=実装＆Win実機配備済み（新inventory API・公開で200確認）。実ホールド検証はTBH市場再開後（現在 marketable:0）。
未了：**Worker再デプロイ**（`/feedback`+`/ml`の両方。`cd worker && npx wrangler deploy`＝wrangler未ログイン→Cloudflare認証待ち）／Win機へ scp 反映／Ko-fi最終確認／v1.1ビルド＆公開／.icoアイコン・告知文・中国語レア度/種別訳。

関連メモリ: [[tbh-price-ocr-tool]] [[marketlens-i18n]] [[tbh-tools-no-cheat-detection]] [[tbh-price-ocr-tool]] [[verify-before-claiming-fixed]] [[tbh-deploy-to-live]]
