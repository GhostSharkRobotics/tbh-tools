// TBH アクセス記録 Worker (Cloudflare Workers + KV)
// ルート:
//   GET/POST /hit?p=<page>&r=<referrer>  … 訪問を記録（IPごとに集計）
//   GET      /stats?pw=<password>        … 自分だけが見るダッシュボード(IP別)
//
// 必要なバインド:
//   KV namespace を STATS という名前でバインド
//   環境変数 DASH_PW にダッシュボードのパスワードを設定
//
// 集計はIPごとに1キー(ip:<IP>)へ read-modify-write で書き込む。
// 個人サイト想定なので衝突は無視できる前提（高トラフィックなら D1 推奨）。

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': '*',
};

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname;

    if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });

    if (path === '/hit') return hit(req, env, url);
    if (path === '/stats') return stats(req, env, url);
    if (path === '/feedback') return feedback(req, env, url);
    if (path === '/ml') return ml(req, env, url);          // MarketLens アプリ利用テレメトリ（匿名）
    if (path === '/mlstats') return mlstats(req, env, url); // ↑のダッシュボード(?pw=)

    return new Response('TBH stats worker', { status: 200, headers: CORS });
  },
};

// MarketLens フィードバック受付。POST=受信(KV保存＋Slack転送), GET ?pw= でダッシュボード
async function feedback(req, env, url) {
  if (req.method === 'GET') {
    if (url.searchParams.get('pw') !== env.DASH_PW) return new Response('unauthorized', { status: 401 });
    const recs = [];
    let cursor;
    do {
      const list = await env.STATS.list({ prefix: 'fb:', cursor });
      for (const k of list.keys) { const r = await env.STATS.get(k.name, 'json'); if (r) recs.push(r); }
      cursor = list.list_complete ? null : list.cursor;
    } while (cursor);
    recs.sort((a, b) => b.ts - a.ts);
    const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    const fmt = (ts) => { const d = new Date(ts), p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`; };
    const rows = recs.map((r) => `<tr><td>${fmt(r.ts)}</td><td>${esc(r.lang)}/${esc(r.ver)}/${esc(r.country)}</td><td>${esc(r.msg).replace(/\n/g, '<br>')}</td><td>${esc(r.contact)}</td></tr>`).join('');
    const html = `<!doctype html><meta charset="utf-8"><title>MarketLens feedback</title>
<style>body{background:#14161b;color:#e6e8ec;font:14px/1.6 system-ui;margin:0;padding:20px}h1{font-size:18px}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #262a33;padding:8px 10px;vertical-align:top;text-align:left}th{color:#9aa0a6}td:nth-child(3){max-width:560px}</style>
<h1>MarketLens feedback (${recs.length})</h1>
<table><thead><tr><th>時刻</th><th>環境</th><th>本文</th><th>連絡先</th></tr></thead><tbody>${rows || '<tr><td colspan=4 style="color:#9aa0a6">まだありません</td></tr>'}</tbody></table>`;
    return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8' } });
  }
  // POST = 受信
  try {
    const ip = req.headers.get('CF-Connecting-IP') || '';
    const country = req.headers.get('CF-IPCountry') || '';
    // 簡易スパム防止：同一IPは20秒に1件まで
    const tkey = 'fbip:' + ip;
    if (await env.STATS.get(tkey)) return new Response('slow down', { status: 429, headers: CORS });
    let b = {};
    try { b = await req.json(); } catch (_) {}
    const msg = String(b.msg || '').slice(0, 2000).trim();
    if (!msg) return new Response('empty', { status: 400, headers: CORS });
    const contact = String(b.contact || '').slice(0, 200).trim();
    const ver = String(b.ver || '').slice(0, 20);
    const lang = String(b.lang || '').slice(0, 10);
    const now = Date.now();
    const rec = { ts: now, msg, contact, ver, lang, ip, country };
    await env.STATS.put('fb:' + now + ':' + Math.random().toString(36).slice(2, 7), JSON.stringify(rec), { expirationTtl: 60 * 60 * 24 * 180 });
    await env.STATS.put(tkey, '1', { expirationTtl: 20 });
    if (env.FEEDBACK_WEBHOOK) {                       // Slack/Discord どちらのIncoming Webhookでも転送（URLは秘密）
      const body = `💬 MarketLens feedback  (v${ver || '?'} · ${lang || '?'} · ${country || '?'})\n${msg}` + (contact ? `\n↩ reply to: ${contact}` : '');
      const isDiscord = /discord(app)?\.com/.test(env.FEEDBACK_WEBHOOK);   // DiscordはcontentキーでSlackはtextキー
      const payload = isDiscord ? { content: body } : { text: body };
      try { await fetch(env.FEEDBACK_WEBHOOK, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) }); } catch (_) {}
    }
    return new Response('ok', { headers: CORS });
  } catch (e) {
    return new Response('err', { status: 200, headers: CORS });
  }
}

// ===== MarketLens アプリ利用テレメトリ（匿名）=====
// POST /ml  body={cid,ev,ver,lang,item,rarity,msg}
//   ev: "launch" | "lookup" | "error"
//   cid = アプリが生成する匿名ランダムID（IP由来ではない）。国はエッジ(CF-IPCountry)で付与しIPは保存しない。
//   集計は ml:<cid> へ read-modify-write。error は本文を mlerr:<ts> に別途保存（デバッグ用・60日TTL）。
function _dayKey(ts) {
  const d = new Date(ts), p = (n) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}`;
}

async function ml(req, env, url) {
  try {
    const country = req.headers.get('CF-IPCountry') || '';
    let b = {};
    try { b = await req.json(); } catch (_) {}
    const cid = String(b.cid || '').slice(0, 40);
    if (!cid) return new Response('no cid', { status: 400, headers: CORS });
    const ev = String(b.ev || '').slice(0, 16);
    const ver = String(b.ver || '').slice(0, 20);
    const lang = String(b.lang || '').slice(0, 10);
    const now = Date.now();
    const day = _dayKey(now);

    if (ev === 'error') {
      const msg = String(b.msg || '').slice(0, 4000).trim();
      if (msg) {
        await env.STATS.put('mlerr:' + now + ':' + Math.random().toString(36).slice(2, 7),
          JSON.stringify({ ts: now, cid: cid.slice(0, 8), ver, lang, country, msg }),
          { expirationTtl: 60 * 60 * 24 * 60 });
      }
    }

    const key = 'ml:' + cid;
    let rec = await env.STATS.get(key, 'json');
    if (!rec) rec = { cid, country, ver, lang, first: now, last: now, launches: 0, lookups: 0, errors: 0, days: {}, items: {} };
    rec.last = now;
    if (country) rec.country = country;
    if (ver) rec.ver = ver;
    if (lang) rec.lang = lang;
    rec.days[day] = (rec.days[day] || 0) + 1;
    // days は直近31日だけ保持（無限肥大を防ぐ）
    const dks = Object.keys(rec.days).sort();
    while (dks.length > 31) delete rec.days[dks.shift()];

    if (ev === 'launch') rec.launches = (rec.launches || 0) + 1;
    else if (ev === 'lookup') {
      rec.lookups = (rec.lookups || 0) + 1;
      const it = String(b.item || '').slice(0, 80).trim();
      const rar = String(b.rarity || '').slice(0, 20).trim();
      if (it) { const k = rar ? `${it} (${rar})` : it; rec.items[k] = (rec.items[k] || 0) + 1; }
    } else if (ev === 'error') rec.errors = (rec.errors || 0) + 1;

    await env.STATS.put(key, JSON.stringify(rec));
    return new Response('ok', { headers: CORS });
  } catch (e) {
    return new Response('err', { status: 200, headers: CORS });
  }
}

async function mlstats(req, env, url) {
  if (url.searchParams.get('pw') !== env.DASH_PW) return new Response('unauthorized', { status: 401 });

  const recs = [];
  let cursor;
  do {
    const list = await env.STATS.list({ prefix: 'ml:', cursor });
    for (const k of list.keys) { const r = await env.STATS.get(k.name, 'json'); if (r) recs.push(r); }
    cursor = list.list_complete ? null : list.cursor;
  } while (cursor);

  // 直近のエラー本文
  const errs = [];
  cursor = undefined;
  do {
    const list = await env.STATS.list({ prefix: 'mlerr:', cursor });
    for (const k of list.keys) { const r = await env.STATS.get(k.name, 'json'); if (r) errs.push(r); }
    cursor = list.list_complete ? null : list.cursor;
  } while (cursor);
  errs.sort((a, b) => b.ts - a.ts);

  const users = recs.length;
  const totalLaunch = recs.reduce((s, r) => s + (r.launches || 0), 0);
  const totalLookup = recs.reduce((s, r) => s + (r.lookups || 0), 0);
  const totalErr = recs.reduce((s, r) => s + (r.errors || 0), 0);

  // 国別（ユーザー数 / 参照数）
  const byCountry = {};
  for (const r of recs) {
    const c = r.country || '?';
    if (!byCountry[c]) byCountry[c] = { users: 0, lookups: 0 };
    byCountry[c].users++; byCountry[c].lookups += (r.lookups || 0);
  }
  // 人気アイテム（全ユーザー横断）
  const items = {};
  for (const r of recs) for (const [k, v] of Object.entries(r.items || {})) items[k] = (items[k] || 0) + v;
  // 日次アクティブ（直近14日：その日に1イベント以上あったユニークID数）
  const dayActive = {};
  for (const r of recs) for (const d of Object.keys(r.days || {})) dayActive[d] = (dayActive[d] || 0) + 1;

  const fmt = (ts) => { const d = new Date(ts), p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`; };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const pw = esc(url.searchParams.get('pw'));

  const countryRows = Object.entries(byCountry).sort((a, b) => b[1].lookups - a[1].lookups)
    .map(([c, v]) => `<tr><td>${esc(c)}</td><td class="num">${v.users}</td><td class="num">${v.lookups}</td></tr>`).join('');
  const itemRows = Object.entries(items).sort((a, b) => b[1] - a[1]).slice(0, 40)
    .map(([k, v], i) => `<tr><td class="num">${i + 1}</td><td>${esc(k)}</td><td class="num">${v}</td></tr>`).join('');
  const dayRows = Object.entries(dayActive).sort((a, b) => a[0] < b[0] ? 1 : -1).slice(0, 14)
    .map(([d, v]) => `<tr><td>${esc(d)}</td><td class="num">${v}</td></tr>`).join('');
  const userRows = recs.slice().sort((a, b) => (b.lookups || 0) - (a.lookups || 0)).slice(0, 100)
    .map((r) => `<tr><td>${esc(r.country || '?')}</td><td>${esc(r.ver || '?')}/${esc(r.lang || '?')}</td><td class="num">${r.launches || 0}</td><td class="num">${r.lookups || 0}</td><td class="num">${r.errors || 0}</td><td>${fmt(r.last)}</td><td>${fmt(r.first)}</td></tr>`).join('');
  const errRows = errs.slice(0, 100)
    .map((r) => `<tr><td>${fmt(r.ts)}</td><td>${esc(r.country || '?')}/${esc(r.ver || '?')}</td><td class="msg">${esc(r.msg).replace(/\n/g, '<br>')}</td></tr>`).join('');

  const html = `<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MarketLens 利用解析</title>
<style>
  :root{color-scheme:dark}
  body{background:#14161b;color:#e6e8ec;font:14px/1.5 system-ui,sans-serif;margin:0;padding:20px}
  h1{font-size:18px;margin:0 0 4px} h2{font-size:14px;color:#9aa0a6;margin:22px 0 8px}
  .sub{color:#9aa0a6;margin:0 0 16px}
  .cards{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px}
  .card{background:#1d2027;border:1px solid #2a2e37;border-radius:10px;padding:10px 14px;min-width:110px}
  .card b{display:block;font-size:22px} .card span{color:#9aa0a6;font-size:12px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start}
  table{border-collapse:collapse;width:100%;font-size:13px}
  th,td{text-align:left;padding:6px 9px;border-bottom:1px solid #262a33}
  th{color:#9aa0a6;font-weight:600}
  td.num{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}
  td.msg{font-family:ui-monospace,monospace;color:#f0a0a0;max-width:680px;font-size:12px}
  a{color:#6cb6ff}
  @media(max-width:780px){.grid{grid-template-columns:1fr}}
</style></head><body>
<h1>MarketLens 利用解析（匿名）</h1>
<p class="sub">配布版アプリの利用状況。IPは保存せず、国はエッジ付与・IDは匿名ランダム。<a href="?pw=${pw}">更新</a> · <a href="/stats?pw=${pw}">サイトのアクセス記録へ</a></p>
<div class="cards">
  <div class="card"><b>${users}</b><span>ユニーク利用者</span></div>
  <div class="card"><b>${totalLaunch}</b><span>総起動</span></div>
  <div class="card"><b>${totalLookup}</b><span>総アイテム参照</span></div>
  <div class="card"><b>${totalErr}</b><span>エラー報告</span></div>
</div>
<div class="grid">
  <div>
    <h2>国別</h2>
    <table><thead><tr><th>国</th><th>人</th><th>参照</th></tr></thead><tbody>${countryRows || '<tr><td colspan=3 style="color:#9aa0a6">まだありません</td></tr>'}</tbody></table>
    <h2>日次アクティブ（直近14日・ユニーク）</h2>
    <table><thead><tr><th>日(UTC)</th><th>人</th></tr></thead><tbody>${dayRows || '<tr><td colspan=2 style="color:#9aa0a6">まだありません</td></tr>'}</tbody></table>
  </div>
  <div>
    <h2>人気アイテム Top40</h2>
    <table><thead><tr><th>#</th><th>アイテム</th><th>参照</th></tr></thead><tbody>${itemRows || '<tr><td colspan=3 style="color:#9aa0a6">まだありません</td></tr>'}</tbody></table>
  </div>
</div>
<h2>利用者（参照数順・上位100）</h2>
<table><thead><tr><th>国</th><th>版/言語</th><th>起動</th><th>参照</th><th>エラー</th><th>最終</th><th>初回</th></tr></thead><tbody>${userRows || '<tr><td colspan=7 style="color:#9aa0a6">まだありません</td></tr>'}</tbody></table>
<h2>エラー報告（直近100・デバッグ用）</h2>
<table><thead><tr><th>時刻</th><th>環境</th><th>本文</th></tr></thead><tbody>${errRows || '<tr><td colspan=3 style="color:#9aa0a6">まだありません</td></tr>'}</tbody></table>
</body></html>`;
  return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8' } });
}

async function hit(req, env, url) {
  try {
    const ip = req.headers.get('CF-Connecting-IP') || 'unknown';
    const country = req.headers.get('CF-IPCountry') || '';
    const ua = req.headers.get('User-Agent') || '';
    const page = (url.searchParams.get('p') || '/').slice(0, 80);
    const ref = (url.searchParams.get('r') || '').slice(0, 80);
    const now = Date.now();
    const bot = /bot|crawl|spider|slurp|bing|google|yandex|facebookexternal|headless/i.test(ua);

    const key = 'ip:' + ip;
    let rec = await env.STATS.get(key, 'json');
    if (!rec) {
      rec = { ip, country, ua, bot, first: now, last: now, total: 0, pages: {}, refs: {} };
    }
    rec.total++;
    rec.last = now;
    rec.ua = ua;
    rec.country = country;
    rec.bot = bot;
    rec.pages[page] = (rec.pages[page] || 0) + 1;
    if (ref) rec.refs[ref] = (rec.refs[ref] || 0) + 1;
    await env.STATS.put(key, JSON.stringify(rec));

    return new Response('ok', { headers: CORS });
  } catch (e) {
    return new Response('err', { status: 200, headers: CORS }); // 記録失敗でもサイトに影響させない
  }
}

async function stats(req, env, url) {
  if (url.searchParams.get('pw') !== env.DASH_PW) {
    return new Response('unauthorized', { status: 401 });
  }
  const showBots = url.searchParams.get('bots') === '1';
  const myIp = req.headers.get('CF-Connecting-IP') || '';

  // ip: 接頭辞のキーを全件取得
  const recs = [];
  let cursor;
  do {
    const list = await env.STATS.list({ prefix: 'ip:', cursor });
    for (const k of list.keys) {
      const r = await env.STATS.get(k.name, 'json');
      if (r) recs.push(r);
    }
    cursor = list.list_complete ? null : list.cursor;
  } while (cursor);

  const visible = recs.filter((r) => showBots || !r.bot);
  visible.sort((a, b) => b.total - a.total);

  const totalHits = visible.reduce((s, r) => s + r.total, 0);
  const humanIps = visible.length;
  const botCount = recs.filter((r) => r.bot).length;

  const fmt = (ts) => {
    const d = new Date(ts);
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  };
  const topPages = (pages) => Object.entries(pages).sort((a, b) => b[1] - a[1])
    .slice(0, 4).map(([k, v]) => `${k} (${v})`).join(', ');
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  const rows = visible.map((r) => {
    const isMe = r.ip === myIp;
    return `<tr class="${isMe ? 'me' : ''} ${r.bot ? 'bot' : ''}">
      <td class="ip">${esc(r.ip)}${isMe ? ' <span class="tag">あなた</span>' : ''}${r.bot ? ' <span class="tag bot">bot</span>' : ''}</td>
      <td>${esc(r.country || '?')}</td>
      <td class="num">${r.total}</td>
      <td>${fmt(r.last)}</td>
      <td>${fmt(r.first)}</td>
      <td class="pg">${esc(topPages(r.pages))}</td>
      <td class="ua" title="${esc(r.ua)}">${esc((r.ua || '').slice(0, 40))}</td>
    </tr>`;
  }).join('');

  const html = `<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TBH アクセス記録</title>
<style>
  :root{color-scheme:dark}
  body{background:#14161b;color:#e6e8ec;font:14px/1.5 system-ui,sans-serif;margin:0;padding:20px}
  h1{font-size:18px;margin:0 0 4px}
  .sub{color:#9aa0a6;margin:0 0 16px}
  .cards{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}
  .card{background:#1d2027;border:1px solid #2a2e37;border-radius:10px;padding:10px 14px;min-width:120px}
  .card b{display:block;font-size:22px}
  .card span{color:#9aa0a6;font-size:12px}
  table{border-collapse:collapse;width:100%;font-size:13px}
  th,td{text-align:left;padding:7px 10px;border-bottom:1px solid #262a33}
  th{color:#9aa0a6;font-weight:600;position:sticky;top:0;background:#14161b}
  td.num{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}
  td.ip{font-family:ui-monospace,monospace}
  td.pg{color:#b6bcc6}
  td.ua{color:#6b7280;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  tr.me{background:#15301f}
  tr.bot{opacity:.5}
  .tag{font-size:10px;background:#2f7d4f;color:#fff;border-radius:4px;padding:1px 5px;vertical-align:middle}
  .tag.bot{background:#555}
  a{color:#6cb6ff}
</style></head><body>
<h1>TBH アクセス記録</h1>
<p class="sub">IP別の利用状況。緑の行=いまアクセス中のあなた（${esc(myIp) || '不明'}）。</p>
<div class="cards">
  <div class="card"><b>${humanIps}</b><span>ユニークIP（人）</span></div>
  <div class="card"><b>${totalHits}</b><span>総アクセス（人）</span></div>
  <div class="card"><b>${botCount}</b><span>bot系IP</span></div>
</div>
<p style="margin:0 0 10px"><a href="?pw=${esc(url.searchParams.get('pw'))}&bots=${showBots ? '0' : '1'}">${showBots ? 'botを隠す' : 'botも表示'}</a></p>
<table>
<thead><tr><th>IP</th><th>国</th><th>回数</th><th>最終</th><th>初回</th><th>主なページ</th><th>ブラウザ(UA)</th></tr></thead>
<tbody>${rows || '<tr><td colspan="7" style="color:#9aa0a6">まだ記録がありません</td></tr>'}</tbody>
</table>
</body></html>`;

  return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8' } });
}
