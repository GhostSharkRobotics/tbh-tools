// 内部アクセス記録（非表示）— ページ表示時に匿名のヒット数だけを外部カウンタへ送る。
// 画面には何も表示しない。オーナーが「自分以外に使っている人がいるか」を確認するための用途。
// 集計の閲覧: https://abacus.jasoncameron.dev/get/tbh-tools-monocro/<page>  (<page>=index / tbh-gem-search / ...)
//           合計: https://abacus.jasoncameron.dev/get/tbh-tools-monocro/all
(function () {
  try {
    var NS = "tbh-tools-monocro";
    var page = (location.pathname.split("/").pop() || "index").replace(/\.html$/, "") || "index";
    var base = "https://abacus.jasoncameron.dev/hit/" + NS + "/";
    // fire-and-forget（CORS無視・結果は読まない・失敗は黙殺）
    var ping = function (key) {
      try { fetch(base + key, { mode: "no-cors", cache: "no-store", keepalive: true }); } catch (e) {}
    };
    ping(page);   // ページ別
    ping("all");  // 全体合計
  } catch (e) {}
})();
