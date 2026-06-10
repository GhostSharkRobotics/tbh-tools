<!-- 言語 / Language -->
**日本語** · [English](README.en.md) · [中文](README.zh.md)

# TBH Tools — Task Bar Hero 非公式ツール集

**Task Bar Hero**（タスクバーヒーロー）を遊ぶ人のための無料ツール集です。
ブラウザですぐ使える **Webツール** と、ゲーム中に価格を瞬時に出す Windows アプリ **MarketLens** の2種類があります。

---

## 🌐 Webツール ＝ インストール不要・リンクをクリックするだけ

### ▶ まとめページ： **https://ghostsharkrobotics.github.io/tbh-tools/**

ダウンロードは要りません。ブックマークすれば PC でもスマホでも使えます。下のリンクから直接ひらけます：

| ツール | できること |
|---|---|
| [🏆 最強ビルドメーカー](https://ghostsharkrobotics.github.io/tbh-tools/tbh-best-build.html) | 各部位の装備・宝石・彫刻・刻印を選ぶと DPS を自動計算。「最強」ボタンで全クラス×全装備を総当たりして最高 DPS 構成を自動セット。 |
| [🔍 アイテム検索](https://ghostsharkrobotics.github.io/tbh-tools/tbh-gem-search.html) | 装備・宝石・彫刻・刻印・特殊ステータスを **効果や名前で検索**。市場価格つき・日英対応・並べ替え可。 |
| [💰 お買い得ファインダー](https://ghostsharkrobotics.github.io/tbh-tools/tbh-deals.html) | 市場の装備を「強さ ÷ 今の最安値」で並べ、相場より安い出品を発見。Steam マーケットへ直リンク。 |
| [🧱 クラフト素材](https://ghostsharkrobotics.github.io/tbh-tools/tbh-crafting.html) | クラフト（キューブ）のレシピと必要素材を tier・部位で検索。素材ごとに価格つき・直リンク。 |
| [📦 ステージ別ドロップ](https://ghostsharkrobotics.github.io/tbh-tools/tbh-stage-drops.html) | どのステージのどの箱から何が出るかを確率つきで一覧。「どこで掘れる？」の逆引きも。 |
| [⚡ 経験値効率](https://ghostsharkrobotics.github.io/tbh-tools/tbh-exp.html) | レベルからオーバーレベル補正済みの EXP でステージを順位付け。クリアタイムを入れると毎時 EXP で並べ替え。 |
| [🛠 ビルドシミュレーター](https://ghostsharkrobotics.github.io/tbh-tools/tbh-build-simulator.html) | 装備・宝石・バフから DPS を計算。 |
| [📊 DPS計算機](https://ghostsharkrobotics.github.io/tbh-tools/tbh-dps.html) | シンプルな DPS 計算。 |
| [📖 仕様メモ](https://ghostsharkrobotics.github.io/tbh-tools/tbh-info.html) | 合成・クラフトの排出種類と確率、DLC 条件、箱ドロップ率。 |

価格データは GitHub Actions で毎日自動更新されます。

---

## 🖥 TBH MarketLens（Windows アプリ）

ゲーム中、**アイテムにカーソルを合わせてキーを押すだけ**で、その Steam 市場価格（最安・中央値）を小さなカードで表示します。名前を打って検索する手間はありません。日本語 / English / 中文 対応。

<p>
  <img src="docs/marketlens-lens.png" width="380" alt="価格ポップ">
  <img src="docs/marketlens-history.png" width="380" alt="価格履歴・出品待ち">
</p>

### ⬇ ダウンロード手順（GitHub に詳しくない方向け）

1. ダウンロードページを開く → **[📥 Releases ページ](https://github.com/GhostSharkRobotics/tbh-marketlens/releases)**
2. 一番上（最新版）の **「Assets」** を開き、**`TBH-MarketLens` で始まる `.zip` ファイル**をクリックしてダウンロード
3. ダウンロードした zip を **右クリック → すべて展開**
4. 展開フォルダの中の **`TBH MarketLens.exe`** をダブルクリックで起動

> 💡 起動時に「**WindowsによってPCが保護されました**」と出たら、**詳細情報 → 実行** を押してください（署名なしアプリのための表示で、問題ありません）。

起動するとタスクトレイ（時計の近く）に常駐します。初回に使い方が表示されます。発動キーや表示言語は **トレイ → 設定** で変えられます（既定の発動キーはマウスの「戻る」ボタン）。

### 安全？（チート対策）

はい。MarketLens は**画面に映っているものを読むだけ**です。Windows 標準の画面キャプチャ（スクリーンショットと同じ）で画面を撮り、OCR でアイテム名を認識して、その価格を Steam で調べます。別プロセスで動き、**ゲームのメモリを読んだり書き換えたりしません**。だからゲームのアンチチートに**チートとして検出されません**。詳しくは [dist-README.md](dist-README.md)。

---

## 開発者向けメモ

- Web ツールは各 HTML がデータを内蔵した**自己完結ファイル**（オフラインでも動作）。`tbh-data.json` 等からビルドスクリプトで生成。
- MarketLens 本体は `tbh-price-ocr.py`、配布版は別リポジトリ [tbh-marketlens](https://github.com/GhostSharkRobotics/tbh-marketlens) の Releases。
- 価格は日次の GitHub Actions で自動更新。

---

## 免責事項

非公式のファン制作ツールです（**ゲーム開発元・Valve/Steam とは無関係**で、提携・承認もありません）。**現状のまま・いかなる保証もなく**提供します。

表示価格は Steam コミュニティマーケット由来で、**不正確・遅延・誤りの可能性があります**（米ドル以外は為替換算の概算）。**取引・投資の助言ではありません**。売買の前に必ず Steam マーケットでご確認ください。**本ツールの利用はすべて自己責任**であり、利用により生じたいかなる損害・損失（売買・購入・販売によるものを含む）についても作者は一切責任を負いません。

*by **Ghost Shark Robotics** · 応援（任意）：[☕ Ko-fi](https://ko-fi.com/ghostsharkrobotics)*
