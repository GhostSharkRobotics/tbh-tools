#!/usr/bin/env python3
"""TBH お買い得ファインダー生成スクリプト
tbh-data.json(装備+stats) と tbh-prices.json(Steam相場) から、
「強いのに今の最安値が安い」装備を見つける単体HTML(tbh-deals.html)を生成する。

強さスコア = Σ weight[stat] × (val / その(stat,unit)の全装備中の最大値)。重みはUIで編集可。
コスパ = 強さ / 現在の最安値(USD)。相場割れ = (中央値-最安値)/中央値。
価格は base|grade|variant でSteam相場に対応。出品の無いものは価格欠落=表示外。
使い方: python3 tbh-build-deals.py
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
APPID = "3678970"


def build_payload():
    d = json.load(open(os.path.join(HERE, "tbh-data.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(HERE, "tbh-prices.json"), encoding="utf-8"))
    prices = P["prices"]

    # en -> ja ラベル & 全装備での (en|unit) 最大値（強さ正規化の分母）
    en_ja, mx = {}, {}
    for e in d["equipment"]:
        for s in e.get("stats", []):
            en_ja.setdefault(s["en"], s.get("ja", s["en"]))
            k = s["en"] + "|" + (s.get("unit") or "")
            v = abs(s.get("val") or 0)
            if v > mx.get(k, 0):
                mx[k] = v

    all_icons = d.get("icons", {})  # sha -> CDN相対パス
    used_icons = {}
    slot_ja = {}  # gear(英) -> 日本語部位名 (gearJa)
    rows = []
    for e in d["equipment"]:
        if not e.get("market"):
            continue
        hn = f"{e['nameEn']} ({e['rarity']}) {e.get('variant','A')}"
        pr = prices.get(hn) or prices.get(f"{e['nameEn']} ({e['rarity']})")
        if not pr or not pr.get("sell"):
            continue
        slot_ja[e.get("gear")] = e.get("gearJa") or e.get("gear")
        ic = e.get("icon")
        if ic and ic in all_icons:
            used_icons[ic] = all_icons[ic]
        st = [[s["en"], (s.get("unit") or ""), s.get("val") or 0] for s in e.get("stats", [])]
        rows.append({
            "n": e.get("name"), "e": e["nameEn"],
            "g": e.get("gear"), "cat": e.get("cat"),
            "lvl": e.get("lvl"), "r": e.get("rarity"),
            "v": e.get("variant", "A"), "icon": e.get("icon"),
            "st": st,
            "sell": pr.get("sell"), "med": pr.get("median"),
            "lst": pr.get("listings"), "vol": pr.get("volume"),
        })

    return {
        "rows": rows,
        "enJa": en_ja,
        "max": mx,
        "icons": used_icons,
        "slotJa": slot_ja,
        "rarityOrder": d["rarityOrder"],
        "iconCdn": d["_meta"].get("iconCdn", "https://community.akamai.steamstatic.com/economy/image/"),
        "appid": APPID,
        "source": P.get("source"), "sourceUrl": P.get("sourceUrl"),
        "marketUpdated": P.get("marketUpdated"), "fetchedAt": P.get("fetchedAt"),
    }


HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TBH お買い得ファインダー / Deal Finder</title>
<style>
  :root{--bg:#14110d;--surface:#1f1b15;--surface2:#262017;--accent:#d8a657;--text:#ece3d2;--muted:#9a8f7a;--border:#3a342a;
    --good:#6fcf6f;--warn:#e0c060;--bad:#e07a7a;--deal:#6fcf6f;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:var(--bg);color:var(--text);font-family:"Hiragino Kaku Gothic ProN","Yu Gothic",sans-serif;line-height:1.6;padding:24px;max-width:980px;margin:0 auto;}
  h1{font-size:24px;color:var(--accent);margin-bottom:4px;}
  .sub{font-size:13px;color:var(--muted);margin-bottom:16px;}
  .back{font-size:13px;color:var(--muted);text-decoration:none;}
  .back:hover{color:var(--accent);}

  .panel{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 14px;margin-bottom:12px;}
  .row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:5px 0;}
  .lab{font-size:11px;color:var(--muted);width:56px;flex:none;}

  /* sort mode = 角タブ(四角), filter = 丸タブ で形で区別 */
  button.mode{background:var(--surface2);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:5px 12px;font-size:13px;cursor:pointer;}
  button.mode:hover{border-color:var(--accent);}
  button.mode.on{background:var(--accent);color:#1a1610;border-color:var(--accent);font-weight:600;}
  button.chip{background:var(--surface2);border:1px solid var(--border);color:var(--text);border-radius:20px;padding:3px 11px;font-size:12px;cursor:pointer;}
  button.chip:hover{border-color:var(--accent);}
  button.chip.on{background:var(--accent);color:#1a1610;border-color:var(--accent);font-weight:600;}
  label.tgl{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:5px;cursor:pointer;}

  details.adv{margin-top:6px;}
  details.adv summary{cursor:pointer;color:var(--accent);font-size:12px;}
  .wgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:4px 14px;margin-top:8px;}
  .wrow{display:flex;align-items:center;gap:6px;font-size:12px;}
  .wrow .wn{flex:1;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .wrow input[type=range]{width:70px;accent-color:var(--accent);}
  .wrow .wv{width:14px;color:var(--muted);text-align:right;}

  .count{font-size:12px;color:var(--muted);margin:8px 2px;}
  table{width:100%;border-collapse:collapse;font-size:13px;}
  th{font-size:11px;color:var(--muted);font-weight:500;text-align:right;padding:6px 8px;border-bottom:1px solid var(--border);white-space:nowrap;}
  th.l{text-align:left;}
  td{padding:7px 8px;border-bottom:1px solid var(--border);text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}
  td.l{text-align:left;}
  tr.row:hover{background:var(--surface2);}
  .rank{color:var(--muted);font-size:12px;width:24px;}
  .ic{width:30px;height:30px;border-radius:5px;background:var(--surface2);vertical-align:middle;border:1px solid var(--border);}
  .nm{display:flex;align-items:center;gap:8px;}
  .nm .tx b{color:var(--text);font-weight:600;}
  .nm .tx .e{color:var(--muted);font-size:10px;}
  .rr{font-size:10px;padding:0 5px;border-radius:4px;color:#15120d;font-weight:700;}
  .stats{color:var(--muted);font-size:11px;white-space:normal;max-width:300px;}
  .price{font-weight:700;color:var(--accent);}
  .med{color:var(--muted);font-size:11px;}
  .disc{font-size:11px;font-weight:700;}
  .disc.up{color:var(--deal);} .disc.dn{color:var(--bad);} .disc.flat{color:var(--muted);}
  .str{color:var(--text);} .val{font-weight:700;color:var(--good);}
  .liq{color:var(--muted);font-size:11px;}
  a.buy{color:var(--accent);text-decoration:none;font-size:12px;border:1px solid var(--border);border-radius:6px;padding:2px 8px;}
  a.buy:hover{border-color:var(--accent);background:var(--surface2);}
  .foot{font-size:11px;color:var(--muted);margin-top:18px;border-top:1px solid var(--border);padding-top:10px;}
</style>
</head>
<body>
<a class="back" href="index.html">← TBHツール</a>
<h1>💰 お買い得ファインダー</h1>
<div class="sub">市場に出ている装備を「強さ÷今の最安値」で並べ、相場割れ（普段より安い出品）を見つけます。</div>

<div class="panel">
  <div class="row"><span class="lab">並べ替え</span><div id="modes"></div></div>
  <div class="row"><span class="lab">重視</span><div id="presets"></div>
    <label class="tgl">最低強さ <input type="number" id="minStr" value="0" min="0" step="10" style="width:62px;background:var(--surface2);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:3px 6px;font-size:12px;text-align:right;"></label>
    <label class="tgl"><input type="checkbox" id="liqOnly" checked>取引のあるものだけ</label>
    <button class="chip" id="reset" style="margin-left:auto">リセット</button>
  </div>
  <div class="row"><span class="lab">部位</span><div id="slots"></div></div>
  <div class="row"><span class="lab">レア</span><div id="rars"></div></div>
  <details class="adv"><summary>重みを細かく調整</summary><div class="wgrid" id="weights"></div></details>
</div>

<div class="count" id="count"></div>
<table>
  <thead><tr>
    <th class="rank"></th><th class="l">装備</th><th class="l">ステータス</th>
    <th>強さ</th><th>最安値</th><th>相場差</th><th>コスパ</th><th>出品/取引</th><th></th>
  </tr></thead>
  <tbody id="tb"></tbody>
</table>
<div class="foot" id="foot"></div>

<script>
const D = /*PAYLOAD_START*/{}/*PAYLOAD_END*/;
const CDN=D.iconCdn, APPID=D.appid;
const RC={Common:'#9a8f7a',Uncommon:'#6fcf6f',Rare:'#6f9fe0',Legendary:'#d8a657',Immortal:'#d05b5b',Arcana:'#c07ad0',Beyond:'#e0c060',Celestial:'#7fd0d0',Divine:'#e0b0e0',Cosmic:'#ff9d5c'};

// 強さ重みプリセット（statごとの優先度 0..3）
const PRESETS={
  'DPS':{AttackDamage:3,AttackSpeed:3,CriticalDamage:3,CriticalChance:3,Multistrike:3,AreaOfEffect:2,CooldownReduction:2,IncreaseProjectileDamage:2,ProjectileCount:2,AddAllSkillLevel:2,CastSpeed:1,BaseAttackCountReduction:1,SkillDurationIncrease:1,SkillRangeExpansion:1,HpLeech:1},
  '耐久':{MaxHp:3,Armor:3,DamageReduction:3,DamageAbsorption:3,BlockChance:2,DodgeChance:2,AllElementalResistance:2,HpRegenPerSec:2,HpLeech:2,AddHpPerHit:1,AddHpPerKill:1,MovementSpeed:1},
  '均等':null  // null=全statを1
};
// 全statキー
const ALLST=Object.keys(D.enJa);
function presetWeights(name){
  const w={}; for(const k of ALLST) w[k]=0;
  if(name==='均等'){ for(const k of ALLST) w[k]=1; return w; }
  const p=PRESETS[name]||{}; for(const k in p) w[k]=p[k]; return w;
}

const LS='tbh-deals-state';
function loadState(){try{return JSON.parse(localStorage.getItem(LS))||{};}catch(e){return {};}}
function saveState(){try{localStorage.setItem(LS,JSON.stringify(state));}catch(e){}}
let state=Object.assign({mode:'value',preset:'DPS',slot:'all',rar:'all',liqOnly:true,minStr:0,weights:presetWeights('DPS')},loadState());

// ---- UI 構築 ----
function seg(host,items,getOn,onClick,cls){
  const el=document.getElementById(host); el.innerHTML='';
  for(const it of items){const b=document.createElement('button');b.className=cls+(getOn(it.k)?' on':'');b.textContent=it.t;b.onclick=()=>onClick(it.k);
    if(it.c){b.style.borderColor=it.c;if(getOn(it.k)){b.style.background=it.c;b.style.color='#15120d';}}el.appendChild(b);} }

const MODES=[{k:'value',t:'コスパ'},{k:'deal',t:'相場割れ'},{k:'strength',t:'強さ'},{k:'cheap',t:'安い順'}];
const SLOTS=[{k:'all',t:'すべて'}].concat(Object.keys(D.slotJa).map(g=>({k:g,t:D.slotJa[g]})));
const RARS=[{k:'all',t:'すべて'}].concat(D.rarityOrder.filter(r=>D.rows.some(x=>x.r===r)).map(r=>({k:r,t:r,c:RC[r]})));
const PRES=Object.keys(PRESETS).map(p=>({k:p,t:p}));

function renderUI(){
  seg('modes',MODES,k=>state.mode===k,k=>{state.mode=k;renderUI();render();},'mode');
  seg('presets',PRES,k=>state.preset===k,k=>{state.preset=k;state.weights=presetWeights(k);renderUI();render();},'chip');
  seg('slots',SLOTS,k=>state.slot===k,k=>{state.slot=k;renderUI();render();},'chip');
  seg('rars',RARS,k=>state.rar===k,k=>{state.rar=k;renderUI();render();},'chip');
  document.getElementById('liqOnly').checked=state.liqOnly;
  document.getElementById('minStr').value=state.minStr;
  // weights
  const wg=document.getElementById('weights'); wg.innerHTML='';
  for(const k of ALLST){const r=document.createElement('div');r.className='wrow';
    r.innerHTML='<span class="wn">'+D.enJa[k]+'</span><input type="range" min="0" max="3" step="1" value="'+state.weights[k]+'"><span class="wv">'+state.weights[k]+'</span>';
    const inp=r.querySelector('input'),vv=r.querySelector('.wv');
    inp.oninput=()=>{state.weights[k]=+inp.value;vv.textContent=inp.value;render();};
    wg.appendChild(r);} }
document.getElementById('liqOnly').onchange=e=>{state.liqOnly=e.target.checked;render();};
document.getElementById('minStr').oninput=e=>{state.minStr=+e.target.value||0;render();};
document.getElementById('reset').onclick=()=>{try{localStorage.removeItem(LS);}catch(e){}state={mode:'value',preset:'DPS',slot:'all',rar:'all',liqOnly:true,minStr:0,weights:presetWeights('DPS')};renderUI();render();};

// ---- 計算 ----
function strength(x){let s=0;for(const[en,u,val]of x.st){const w=state.weights[en]||0;if(!w)continue;const m=D.max[en+'|'+u]||1;s+=w*Math.abs(val)/m;}return s*100;}
function fmtUsd(c){return '$'+(c/100).toFixed(2);}
function statText(x){return x.st.map(([en,u,val])=>D.enJa[en]+' '+(val>0?'+':'')+val+(u==='%'?'%':u==='/s'?'/s':'')).join(' · ');}

function render(){
  saveState();
  let rows=D.rows.filter(x=>{
    if(state.slot!=='all'&&x.g!==state.slot)return false;
    if(state.rar!=='all'&&x.r!==state.rar)return false;
    if(state.liqOnly&&!(x.lst>0))return false;
    return true;
  }).map(x=>{
    const str=strength(x), usd=x.sell/100;
    const disc=x.med?((x.med-x.sell)/x.med*100):0;
    return {x,str,usd,disc,val:usd>0?str/usd:0};
  }).filter(r=>r.str>=state.minStr);
  const cmp={
    value:(a,b)=>b.val-a.val,
    deal:(a,b)=>b.disc-a.disc||b.str-a.str,
    strength:(a,b)=>b.str-a.str,
    cheap:(a,b)=>a.x.sell-b.x.sell,
  }[state.mode];
  rows.sort(cmp);
  const top=rows.slice(0,200);
  document.getElementById('count').textContent=rows.length+'件中 上位'+top.length+'件表示';
  const tb=document.getElementById('tb'); tb.innerHTML='';
  top.forEach((r,i)=>{
    const x=r.x;
    const tr=document.createElement('tr');tr.className='row';
    const iu=x.icon&&D.icons[x.icon];
    const ic=iu?'<img class="ic" src="'+CDN+iu+'" loading="lazy">':'<span class="ic"></span>';
    const dc=r.disc>2?'up':r.disc<-2?'dn':'flat';
    const ds=r.disc>0?'-'+r.disc.toFixed(0)+'%':r.disc<0?'+'+(-r.disc).toFixed(0)+'%':'±0';
    const url='https://steamcommunity.com/market/listings/'+APPID+'/'+encodeURIComponent(x.e+' ('+x.r+') '+x.v);
    tr.innerHTML=
      '<td class="rank">'+(i+1)+'</td>'+
      '<td class="l"><div class="nm">'+ic+'<div class="tx"><b>'+x.n+'</b> <span class="rr" style="background:'+(RC[x.r]||'#888')+'">'+x.r+'</span><br><span class="e">'+x.e+' · '+(D.slotJa[x.g]||x.g)+' · Lv'+x.lvl+'</span></div></div></td>'+
      '<td class="l"><span class="stats">'+statText(x)+'</span></td>'+
      '<td class="str">'+r.str.toFixed(1)+'</td>'+
      '<td class="price">'+fmtUsd(x.sell)+'</td>'+
      '<td><span class="disc '+dc+'">'+ds+'</span><br><span class="med">中央'+fmtUsd(x.med||x.sell)+'</span></td>'+
      '<td class="val">'+r.val.toFixed(1)+'</td>'+
      '<td class="liq">'+(x.lst||0)+'<br>'+(x.vol||0)+'/日</td>'+
      '<td><a class="buy" href="'+url+'" target="_blank" rel="noopener">Steam</a></td>';
    tb.appendChild(tr);
  });
}
renderUI();render();
document.getElementById('foot').innerHTML='強さ=Σ(重み×そのステの全装備中最大に対する割合)。コスパ=強さ÷最安値($)。相場差=中央値に対する最安値の割安率。<br>価格出典: <a class="back" href="'+(D.sourceUrl||'#')+'" target="_blank">'+(D.source||'')+'</a>（'+(D.fetchedAt||'')+' 取得 / 市場更新 '+(D.marketUpdated||'')+'）。Steam負荷対策でレジェンダリー未満は取引停止のため対象外。';
</script>
</body>
</html>
"""


def main():
    payload = build_payload()
    pc = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html = HTML.replace("/*PAYLOAD_START*/{}/*PAYLOAD_END*/",
                        "/*PAYLOAD_START*/" + pc + "/*PAYLOAD_END*/")
    out = os.path.join(HERE, "tbh-deals.html")
    open(out, "w", encoding="utf-8").write(html)
    print("wrote", out, "| rows:", len(payload["rows"]),
          "| size:", round(len(html) / 1024), "KB")


if __name__ == "__main__":
    main()
