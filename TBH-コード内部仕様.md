# TBH コード内部仕様（GameAssembly.dll 逆アセンブル）

CSVテーブルには出ない「コードにしか無い」情報をまとめたもの。出典は `TaskbarHero/GameAssembly.dll`（Unity IL2CPP, x86-64）を Il2CppDumper + capstone で解析。
※AssetRipper出力(ar_export)はメソッド本体が空スタブで使えない。実ロジックはネイティブDLLのみ。il2cppセクション delta 0x1600 / dump.csのRVAで位置特定。

---

## 1. ステータス・システム（最重要）

### StatType 全64種
NONE=0, AttackDamage=1, AttackSpeed=2, CriticalChance=3, CriticalDamage=4, MaxHp=5, Armor=6, MovementSpeed=7, AreaOfEffect=8, BaseAttackCountReduction=9, CooldownReduction=10, SkillRangeExpansion=11, FireResistance=12, ColdResistance=13, LightningResistance=14, ChaosResistance=15, DodgeChance=16, BlockChance=17, MaxDodgeChance=18, MaxBlockChance=19, Multistrike=20, HpLeech=21, ProjectileCount=22, HpRegenPerSec=23, PhysicalDamagePercent=24, FireDamagePercent=25, ColdDamagePercent=26, LightningDamagePercent=27, ChaosDamagePercent=28, MaxFireResistance=29, MaxColdResistance=30, MaxLightningResistance=31, MaxChaosResistance=32, AddHpPerHit=33, DamageReduction=34, PhysicalDamageReduction=35, FireDamageReduction=36, ColdDamageReduction=37, LightningDamageReduction=38, ChaosDamageReduction=39, DamageAbsorption=40, DamageAddition=41, PhysicalDamageAddition=42, FireDamageAddition=43, ColdDamageAddition=44, LightningDamageAddition=45, ChaosDamageAddition=46, IncreaseExpAmount=47, AdditionalExp=48, CastSpeed=49, SkillHealIncrease=50, SkillDurationIncrease=51, AllElementalResistance=52, IncreaseProjectileDamage=53, IncreaseMeleeDamage=54, IncreaseAreaOfEffectDamage=55, IncreaseSummonDamage=56, IncreaseProjectileSpeed=57, AddHpPerKill=58, AddAllSkillLevel=59, ElementalBlockChance=60, ElementalDodgeChance=61, MaxElementalBlockChance=62, MaxElementalDodgeChance=63

### ステータス合算式【逆アセンブルで確定】
集計は `xe.kbb(List<uq>)`（uq = {StatType@0x10, MODTYPE@0x14, value@0x18, MODSOURCE@0x1C}）。MODTYPEで3アキュムレータに振り分け、最後に結合：
- **MODTYPE=FLAT(0)** → 合計 F（base を含む加算）… `xmm7 += value`
- **MODTYPE=ADDITIVE(1)** → 合計 Ad（加算%）… `xmm6 += value`
- **MODTYPE=MULTIPLICATIVE(2)** → 積 M（各々を個別乗算）… `xmm8 *= (1 + value)`
- 最終結合 `F × (1 + Ad) × M`

```
最終ステ = (base + ΣFLAT) × (1 + Σ加算% ) × Π(1 + 乗算%ᵢ)
```
※FLAT は素の加算（同種は単純合計）、ADDITIVE は全部足して1回だけ ×(1+Σ)、MULTIPLICATIVE は1つずつ ×(1+x) を掛け重ねる。出所は **MODSOURCE = BASE / ITEM / ATTRIBUTE / PASSIVE / AccountStatus / StatusEffect / BuffSkill / ENVIROUNMENT** の8種、どれも上式の同じMODTYPE層に入る。
- `StatModInfoData`: { StatType, MODTYPE, 値×3 }。`AttributeInfoData`: { HeroKey, GroupKey, AttributeType, Value, RequiredPoint, MaxLevel }（=スキルツリーのノード）。

### 上限（クランプ）【逆アセンブルで確定】
最終ステ算出後、`Hero.goj(StatType)` で派生ステに上限をかける：
- **抵抗・各種軽減の上限 = 0.75（75%）がハードコード**（`minss xmm, 0.75`）。`MaxFireResistance`等(29-32) / `MaxDodge/BlockChance`(18/19) / `MaxElemental…`(62/63) のステは、この 0.75 の上限"天井"自体を加算で押し上げる方式（`min(値, 0.75 + Max系ボーナス)`）。
- 別途 **2000.0 の上限**を持つステがある（`minss xmm, 2000.0`、対象ステは要特定）。

### 値のスケーリング（データ解釈の鍵）
`EParamExchangeType` / `ModStatExchangeType` = **Raw_Divide1000 / Raw_Divide100 / Divided / DamageAttribute**。CSVの生int値はこの方式で実数化する（÷1000 or ÷100 等）。tbh-data.json の値解釈時に必須。

---

## 2. ダメージ・スキル・戦闘

- **EDamageAttribute（元素5種）**: Physical=0, Fire=1, Cold=2, Lightning=3, **Chaos=4**, AllElement=5, None=6
- **EDamageType（ビットフラグ）**: Melee=1, Projectile=2, AOE=4, Summon=8, DOT=16, Trap=32
- **SKILLTYPE（ビットフラグ）**: Direct=1, Projectile=4, Aoe=8, SpawnTurret=16, SpawnTrap=32, SpawnSomething=64, SpawnRandomMonster=128
- **ACTIVATIONTYPE（スキル発動条件）**: BASEATTACK / BASEATTACK_COUNT / COOLDOWN / CONTINUOUS
- **SLOTTYPE**: BASEATTACK / SKILL
- **DamageableType**: Hero=1, Monster=2, Structure=6（タレット/トラップ=Structure）
- **EUNITSTATE**: NONE/IDLE/MOVE/RETURN_TO_POSITION/ATTACK/REVIVE/DIE
- **EATTACKSTATE**: PREDELAY / ACTIONTIME / POSTDELAY（攻撃前隙・本体・後隙）
- **戦闘はスキル1個＝1クラスで実装（計68クラス）**。各スキルの実係数/挙動はコード側（例: KnightSacredBlade, WizardMeteorStrike, SlayerAxeSpin, ArcherArrowRainAtk, ActBoss系の攻撃パターン群）。

### 状態異常（StatusEffectType）
Chill=101, Freeze=102, Ignite=103, Shock=104, Bleed=105, Stun=106（冷気/凍結/発火/感電/出血/スタン）。上書き挙動: StatusEffectOverrideType = InitDuration / NotOverride。

### バフ/デバフ（コードのみの仕様）
- **失効条件 BuffExpireConditionType = Time / BaseAttackCount / Stage** … 時間以外に「基本攻撃N回」「ステージ跨ぎ」でも切れる。
- **重複 BuffStackType = OnlyOne / Stackable**。BuffType = Buff / Debuff。
- エフェクト重複 EffectStackType = UseStack / UseOnlyOne / None。

---

## 3. アイテム・装備

- **EGearType（21種）**: SWORD, BOW, STAFF, SCEPTER, CROSSBOW, AXE, SHIELD, ARROW, ORB, TOME, BOLT, HATCHET, HELMET, ARMOR, GLOVES, BOOTS, AMULET, EARING, RING, BRACER（オフハンド=SHIELD/ARROW/ORB/TOME/BOLT/HATCHET）
- **EGearGroup**: WEAPON / ARMOR / ACCESSORY / COMMON
- **EGradeType（11段）**: COMMON, UNCOMMON, RARE, LEGENDARY, IMMORTAL, ARCANA, BEYOND, CELESTIAL, DIVINE, COSMIC, NONE
- **EItemParts（装備11部位）**: MAIN_WEAPON, SUB_WEAPON, HELMET, ARMOR, GLOVES, BOOTS, AMULET, EARING, RING, BRACER
- **EItemCraftingType（クラフト枠）**: MainWeapon, SubWeapon, Helmet, Armor, Gloves, Boots, Accessory
- **EMaterialType**: DECORATION, **SOULSTONE**, ENGRAVING, INSCRIPTION, OFFERING, CRAFTING（SOULSTONE=ステージ入場で消費する魂石）
- **EItemType**: STAGEBOX / MATERIAL / GEAR
- **装備条件**: `ETryEquipGearResult` = ClassTypeNotMatch / LowHeroLevel / CannotEquipableItem / InvalidItem / Success → **職一致＋英雄レベルが必要**。
- **EEquipClassType**: All / Knight / Ranger / Sorcerer / Priest / Hunter / Slayer

### 固有効果（EGearUniqueMod 全23種, コード名つき）
ShieldChargeKillCooldown(10001), SkewerShotBleedingStrike(20001), ArrowRainCriticalCooldown(20002), FlameHydraBerserk(30001), IceOrbFreezeToCold(30002), SnowstormEnhanceFrozenEnemy(30003), SorcererLightningShock(1000009), WrathOfHeavenHeal(40001), ExplosiveBoltHalf(50001), ChargeTrapExplosiveCooldown(50002), CrossbowTurretCooldown(50003), CrossbowTurretAddAmount(50004), AxeSpinBleedingChance(60001), SlayerLowHpAttackSpeed(1000008), WhirlwindFireIgnite(1000010), SkillProjectileCountUp(1000011), SkillMultiStrikeCountUp(1000012), SkillElementChange(1000013), SkillBaseAttackCountReduce(1000014), SkillCooldownReduce(1000015), WaveMoveSlowestPartyExcludeSelf(1000001), WaveMoveFastestPartyMember(1000002)

---

## 4. キューブ（合成/クラフト等）

- **ERecipeType（8操作）**: ALCHEMY, SYNTHESIS, CRAFTING, DECORATION, ENGRAVING, INSCRIPTION, OFFERING, EXTRACTION
- **EItemSynthesisType**: Gear / Accessory / Material（カテゴリは跨げない）
- **合成結果 ECubeSynthesisResult = Fail / Success / GreatSuccess**（**失敗・大成功がある**）
- **結果グレード RESULTGRADETYPE = Lower2Grade(−2) / Lower1Grade(−1) / SameGrade / Higher1Grade / Higher2Grade** … **グレードが下がる結果も存在**。
- **EAddCubeResult（投入バリデーション24種）** から判明する仕様:
  - **CannotSynthesisCosmic** … COSMIC（最高グレ）は合成不可。
  - LowTierSynthesis / NotMatchSynthesisItemGrade / NotMatchSynthesisNowSynthesisType
  - ReservedSoulStone / ServerPendingItem（サーバー保留アイテム）/ BlockedItem / DeleteItemOnlyAlchemy
- **ALCHEMY＝アイテムを金に変換**（`EGoldCurrencySource.CubeAlchemy`, `CubeAlchemyGoldPercent`, AlchemyGoldText が裏付け）。
- **OFFERING（供物）**は独立操作として実装（詳細未調査）。

---

## 5. ドロップ／報酬の内部機構（武器ゲートの核心）

- **EDropType = EachDropOneWeight(0) / SelectOneByClass(1) / EachDropOneWeight_DLCVariant(2)** … ドロップ行の抽選方式。**SelectOneByClass がDLC職武器の「職で1つ選ぶ」ゲート**、DLCVariant がDLC差分処理。
- **EREWARDTYPE**: ITEM / ITEMGROUP / MONSTER（報酬はアイテム/アイテム群/モンスター召喚）
- **ロード時にドロップ行を二分割**（`yq.lpq`）: HeroKeyCondition==0 → 無条件dict `bfjf[DropKey]` / !=0 → 職別dict `bfje[DropKey][HeroKeyCondition]`。
- 取得 `hjc(dropKey, b)` = `bfje[dropKey][b]` を返すだけで所持確認なし → **出すかは呼び出し側が渡す職ID次第**。
- **ゲートの基準は「DLC所持」ではなく「現在プレイ中の職」**。Steam所持判定（`DLCManager.gxq→IsSubscribed`）は戦利品処理から一切呼ばれずUI専用。
- **ドロップは現在職で絞る**（StageManager.iby）。**合成(ue.Cube)はこの職ゲートを通らない** → 合成は職/DLCに縛られず武器が出る。詳細は [TBH-解析メモ.md] / メモ tbh-dlc-weapon-gating。
- 箱種別 EBoxType = NORMAL / BOSS(ステージボス) / ACTBOSS(章ボス)。

---

## 6. アカウント進行ボーナス（EAccountStatus 全36種）

カテゴリ EAccountStatusCategory = Battle / Exploration / Reward。

- **金**: IncreaseGoldAmount, AdditionalGold, AdditionalGoldStageBoss, AdditionalGoldActBoss, AdditionalGoldNormalMonster
- **EXP**: IncreaseExpAmount, AdditionalExp, AdditionalExpStageBoss, AdditionalExpActBoss, AdditionalExpNormalMonster, CubeExpPercent
- **ドロップ**: DropChanceNormalChest, DropChanceStageBossChest, DropChanceNormalChestPercent, DropChanceStageBossChestPercent, MaxAmountNormalChest, MaxAmountStageBossChest, MaxAmountActBossChest（箱からの個数上限）
- **Wave**: WaveCountReduction, WaveMonsterAmount
- **全英雄ステ**: AllHeroMoveSpeed, AllHeroAttackSpeed, AllHeroAttackDamage, AllHeroAttackDamagePercent, AllHeroArmor, AllHeroArmorPercent
- **解放/枠**: MaxInventorySlot, UnlockStashPageCount, UnlockArrangeSlotCount, UnlockSkillSlotCount
- **箱の自動オープン**: UnlockAutoOpenNormalChest, ReduceAutoOpenNormalChestTime, UnlockAutoOpenStageBossChest, ReduceAutoOpenStageBossChestTime, UnlockAutoOpenActBossChest
- **錬金**: CubeAlchemyGoldPercent

---

## 7. ステージ・モンスター・英雄

- **ESTAGEDIFFICULTY**: NORMAL / NIGHTMARE / HELL / TORMENT
- **EStageType**: NORMAL / ACTBOSS。EStageState: MONSTERSPAWN / BATTLE / REORGANIZATION。
- **入場結果 EStageEnterResultType**: Success / FailReasonEndStage / **FailReasonNeedSoulStone** / **FailReasonNeedChestSpace** / Failed → 入場に魂石と箱スペースが要る。
- **EMonsterType**: MONSTER / BOSS。EMonsterLogType: Monster / Boss / ActBoss。
- **EHeroType（内部名）= Knight / Archer / Wizard / Priest / Hunter / Barbarian**。表示名との対応 → Archer=レンジャー, Wizard=ソーサラー, Barbarian=スレイヤー。
- **EPetUnlockConditionType**: KillMonster / DLC（ペットはキル数 or DLCで解放）。

---

## 8. 経済・記録・その他システム

- **EGoldCurrencySource**: MonsterKill / CubeAlchemy / **OfflineReward**（オフライン報酬の存在を確認）
- **EAggregateType（17種の通算統計）**: MonsterKill, HeroDeath, GoldEarn, BoxObtain, ItemObtain, Synthesis, Alchemy, Crafting, Offering, Extraction, Decoration, Engraving, Inscription, StageClear, StageFail, PlayTime, BoxOpen
- **ESteamSessionStatType（26種, Steam実績/統計）**: BossKill, ...ArcanaItemFound, BeyondItemFound, CelestialItemFound, DivineItemFound, CosmicItemFound（高レア発見をトラッキング）, 各キューブ操作, AccountReset, SessionCount 等
- **ログ ELogType（16種）**: StageClear, GetItemWithBoxOpen, GetBox, HeroDie, HeroResurrection, HeroLevelUp, StageFailed, 各種Result(Synthesis/Alchemy/Decoration/Engraving/Inscription/Offering/Crafting/Extraction)
- **RedDot通知 ERedDotEvent**: NewItem, NewMail, SkillPoint, SkillEquipable, UnlockableSynthesisRecipe, UnlockStatus, UnlockCube, **UnlockRune**, UnlockedPet（Rune/Petシステムの存在）
- **メインタブ EMainTab**: Hero / NewStash / Portal / Cube
- **トレード**: ESlotType に TRADINGSTASH、ESlotAction に TradeIn / Toast_NotAllowedEnchantedTrade（エンチャント品はトレード不可）

---

## 9. アンチチート・DLC・保存

- **CodeStage ACTk（アンチチート）搭載**。多くの数値が **ObscuredInt（メモリ上で暗号化）** で保持され、読むたび `op_Implicit` で復号。アイテムID/セーブ値もこれ。→ メモリ直読みの動的解析には復号を挟む必要あり。検知時 `EPopupType.DetectAntiCheat`。
- **DLC = Heathen Steamworks の IsSubscribed** で判定。呼ぶのはUIのみ（スタッシュタブ/DLCバンドル販売/ペット表示）。ゲーム性（武器入手）に所持判定は効かない。
- ブロック要因 EBlockingReason: MailBox / SteamDisconnect / ResetData / RunningFixingInventory（インベントリ修復中ブロック）。サーバー同期前提のアイテム(ServerPendingItem/ReservedSoulStone)あり＝**一部オンライン連動**。

---

## 10. 未解析（要追加作業）の領域

数値レベルの式・確率・定数は本体の逆アセンブルを1ターゲットずつ要する：
- ステ合算 FLAT/ADDITIVE/MULTIPLICATIVE の正確な結合順と係数
- 抵抗/回避/ブロックのデフォルト上限値（`iir(StatType)→double` 等の per-stat 定数表に存在、switch分岐で要抽出）
- ドロップ率/箱個数の実数、オフライン報酬式
- 合成の Fail/GreatSuccess 確率、結果グレード（±2）の分布、レベル(LevelWeight1-4)の重み
- 各スキル(68クラス)の係数

解析基盤: `/tmp/lib.py`（rva2off=セクション別, il2cppセクション delta 0x1600）+ dump.cs のRVA + capstone。
