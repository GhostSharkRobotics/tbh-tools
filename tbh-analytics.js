// TBH アクセス記録ビーコン
// 各ページ読み込み時に Cloudflare Worker を1回叩いて訪問を記録する。
// ↓デプロイ後に取得した Worker の URL に書き換えるのはここ1か所だけ。
//   例: 'https://tbh-stats.yourname.workers.dev'
var TBH_STATS_WORKER = 'https://__REPLACE_WITH_YOUR_WORKER_URL__';

(function () {
  try {
    if (TBH_STATS_WORKER.indexOf('__REPLACE') !== -1) return; // 未設定なら何もしない
    var page = (location.pathname.split('/').pop() || 'index.html');
    var ref = document.referrer ? new URL(document.referrer).hostname : '';
    var url = TBH_STATS_WORKER + '/hit'
      + '?p=' + encodeURIComponent(page)
      + (ref ? '&r=' + encodeURIComponent(ref) : '');
    if (navigator.sendBeacon) {
      navigator.sendBeacon(url);
    } else {
      fetch(url, { method: 'POST', mode: 'no-cors', keepalive: true });
    }
  } catch (e) { /* 記録失敗はサイト動作に影響させない */ }
})();
