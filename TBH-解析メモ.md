# TBH 解析メモ（ゲーム抽出で判明した「見えない情報」だけ）

v1.00.09 抽出。一般論は省略。ゲーム内で見えない／誤解しやすい事実のみ。

## 合成（同グレ9個 → 上位1個）

- 結果は**入れた種類に無関係**＝カテゴリ固定プールからランダム（武器だけ入れても防具が出る／宝石だけ入れても彫刻が出る）。カテゴリ Gear / Accessory / Material は跨げない。

**出やすい種類（DLC無し）：**

[chart:synthGearType]

[chart:synthAccessoryType]

[chart:synthMaterialType]

- **DLC条件**（`HeroKeyCondition`＝所有DLC、編成は無関係）：Hunter DLC未所有なら**クロスボウ/ボルトは絶対出ない**、Slayer DLC未所有なら**斧/ハチェットは絶対出ない**。

**昇格確率（1つ上へ上がる確率＝「壁」）：**

[chart:gradeUpgrade]

- 降格なし。コズミックは合成不可。イモータル合成＝キューブLv10解放、セレスティアル＝Lv50。
- ★重みは `SynthesisRecipeInfoData` に無く、`SynthesisDropInfoData → DropInfoData.Weight` にある（見落とし注意）。RewardKeyはクラス別武器の束（例 1100010＝剣+弓+杖+セプター）。

## クラフト（部位タイプを選んで作る）

- 主武器クラフトで**防具は出ない**（部位固定）。Hunter無し＝クロスボウ/ボルト無、Slayer無し＝斧/ハチェット無。

[chart:craftMainWeaponGrade]

[chart:craftMainWeaponType]

- 種類別%は「グループ内で1個をどう選ぶか（自クラス固定orランダム）」が未確認＝均等仮定。プール（出る/出ない）とDLC条件は確定。

## 箱

- 白箱(910)＝通常敵 **8〜16%** ／ 青箱(920)＝ステージボス **80〜100%** ／ 金箱(930)＝章ボス。中身は重み付きテーブル（職DLC条件あり）。
- 「白箱満杯→青箱が出やすい」は**データに該当ロジック無し＝迷信**。青箱はステージボス撃破＋進行ツリー `DropChanceStageBossChestPercent` で増える。

## Steam市場の絞り（2026）

- 取引可＝`IsCanExchangeMarketable=True` の **820件だけ**（Legendary+のAロール・特定Lvのみ）。Bロール／下位／非対象Lvは取引不可（ゲーム内には存在）。
- 「時間あたりドロップ上限」の仕組み（Steam在庫 `drop_window`/`max_per_window`）は**フィールドはあるがこのビルドで全0＝無効**。あるならサーバー側。

## 武器ベース攻撃速度（隠れDPSレバー）

- ＝`GearInfoData` BaseStat2。レアリティで上昇。弓 base÷100 ＋ Rangerクラス基礎1.0 ＝ **コモン弓1.3〜1.4 / コズミックLv65弓4.10**。
- Lv90コズミック基礎：**弓3.1/s vs スタッフ0.4/s（攻速8倍差）** → 素DPSは弓が約5倍。

## 被ダメージ

- 軽減前 ＝ 敵ATK × スキル倍率 × ステージLv補正 × ボス補正（全てデータにあり＝**算出可能**）。
- 軽減式（防御/耐性→%）は**ゲームコード内（IL2CPP・難読化）でデータに無い**。
