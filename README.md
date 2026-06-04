# TBH Tools — Task Bar Hero 非公式ユーティリティ

タスクバーヒーロー（Task Bar Hero）のアイテム検索・ビルド計算ツール。
GitHub Pages で公開しており、ブックマークすればどの端末でも使えます。

## ツール
- **アイテム検索** (`tbh-gem-search.html`) — 装備 / 装飾(宝石) / 彫刻 / 碑文(刻印) / 特殊ステータスを効果・名前で検索。市場価格つき、日英対応、ヘッダクリックで並べ替え、名前クリックで英語名コピー。
- **ビルドシミュレーター** (`tbh-build-simulator.html`) — DPS計算。
- **DPS計算機** (`tbh-dps.html`)。

各HTMLはデータを内部に埋め込んだ自己完結ファイル（オフラインでも動作）。

## データ更新
価格・装備リストの再取得とHTMLへの再注入:

```
python3 tbh-fetch-prices.py
git commit -am "update data" && git push
```

価格出典: [tbh-market.com](https://tbh-market.com/)（Steam Community Market 相場集計）。
数値はコミュニティwiki由来でやや不確実、実機の値が優先。
