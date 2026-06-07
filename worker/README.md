# TBH アクセス記録 — セットアップ手順

IP単位で「誰がどのページをいくつ見たか」を記録し、**自分だけ**がパスワード付きダッシュボードで見るための仕組み。
サイト本体（GitHub Pages）はそのまま。記録用に Cloudflare Worker を1つ併設する。**すべて無料枠**。

## 1. Worker を作る（Cloudflareダッシュボードだけで完結）

1. https://dash.cloudflare.com に無料登録 → ログイン
2. 左メニュー **Workers & Pages** → **Create application** → **Create Worker**
3. 名前を `tbh-stats` などにして **Deploy**
4. **Edit code** を開き、中身を全部消して [`tbh-stats-worker.js`](./tbh-stats-worker.js) の内容を貼り付け → **Deploy**

## 2. KV（保存先）を作って繋ぐ

1. **Workers & Pages → KV** → **Create a namespace**、名前 `tbh-stats`（任意）→ 作成
2. `tbh-stats` Worker の **Settings → Variables and Secrets → KV Namespace Bindings**
3. **Add binding**：
   - Variable name: `STATS`  ← この名前は必ず `STATS`
   - KV namespace: さっき作った `tbh-stats`
4. 保存

## 3. ダッシュボードのパスワードを設定

1. 同じ Worker の **Settings → Variables and Secrets**
2. **Add** で環境変数を追加：
   - Name: `DASH_PW`
   - Value: 好きなパスワード（自分だけが知る文字列）
3. 保存 → **Deploy**

## 4. Worker の URL をサイトに反映

- デプロイ後に出る URL（例 `https://tbh-stats.あなた名.workers.dev`）をコピー
- リポジトリの [`tbh-analytics.js`](../tbh-analytics.js) の先頭
  `var TBH_STATS_WORKER = 'https://__REPLACE_WITH_YOUR_WORKER_URL__';`
  をその URL に書き換えて push（※末尾スラッシュは付けない）
  - URL を教えてくれれば、こちらで書き換えて push まで done にできます。

## 使い方

- 記録：各ページを開くたび自動で記録（訪問者には何も見えない）
- 閲覧：`https://tbh-stats.あなた名.workers.dev/stats?pw=設定したパスワード`
  - IP別に「回数・国・最終/初回アクセス・主に見たページ・UA」を一覧
  - 緑の行 = いまアクセス中の自分のIP。bot系は既定で非表示（リンクで表示切替）

## 補足・注意

- **無料枠**: KV 書き込み 1000回/日。個人サイトなら十分。超える人気が出たら D1 への移行を検討。
- **集計の取りこぼし**: 同一IPで同時に複数ページを開くと稀にカウントを1〜2取りこぼす（個人用途では無視できる範囲）。
- **IPはプライバシー情報**: 生IPを保存するので、第三者に共有・公開しないこと。
- **自分を除外したい**: ダッシュボードで自分のIPは緑表示なので判別可能。完全除外が必要なら言ってくれれば自IP除外フィルタを足します。
