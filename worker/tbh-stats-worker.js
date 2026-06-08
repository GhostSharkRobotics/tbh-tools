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
    if (env.FEEDBACK_WEBHOOK) {                       // Slack等のIncoming Webhookへ転送（URLは秘密）
      const text = `:speech_balloon: *MarketLens feedback*  (v${ver || '?'} · ${lang || '?'} · ${country || '?'})\n${msg}` + (contact ? `\n_reply to:_ ${contact}` : '');
      try { await fetch(env.FEEDBACK_WEBHOOK, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ text }) }); } catch (_) {}
    }
    return new Response('ok', { headers: CORS });
  } catch (e) {
    return new Response('err', { status: 200, headers: CORS });
  }
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
