#!/usr/bin/env python3
"""DATA(tbh-data.json) をHTMLツールに再埋め込み（価格は触らない・ネット不要）。
重いitemSourcesは省き、軽量acqを残す。価格を更新したい時は tbh-fetch-prices.py を使う。"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "tbh-data.json"), encoding="utf-8"))
d_web = {k: v for k, v in d.items() if k != "itemSources"}
if "itemSources" in d:
    d_web["itemSources"] = {"_note": "Web版では省略。全件は tbh-data.json / acq を参照"}
dcompact = json.dumps(d_web, ensure_ascii=False, separators=(",", ":"))

for fn in ("tbh-gem-search.html", "tbh-build-simulator.html", "tbh-best-build.html"):
    fp = os.path.join(HERE, fn)
    if not os.path.exists(fp):
        continue
    h = open(fp, encoding="utf-8").read()
    if "/*DATA_START*/" not in h:
        continue
    h = re.sub(r"/\*DATA_START\*/.*?/\*DATA_END\*/",
               "/*DATA_START*/" + dcompact + "/*DATA_END*/", h, flags=re.S)
    open(fp, "w", encoding="utf-8").write(h)
    print("injected DATA ->", fn, "(%.2f MB)" % (len(dcompact) / 1e6))
