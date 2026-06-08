#!/usr/bin/env python3
"""多言語UIの健全性チェック（配備前に必ず実行）。
1) カタログ完全性: TR の全キーが全言語に存在するか（言語を足したら未翻訳キーを列挙）。
2) 文言漏れ: UIに渡る文字列(text=/title=/label=/round_pill/section/_ask_text 等)に
   T()を通さない日本語リテラルが無いか（＝英語モードで日本語が残る箇所）。
どちらか1つでも問題があれば exit 1。"""
import ast, sys, re

JP = re.compile(r'[぀-ヿ㐀-鿿０-９！-～]')        # かな・カナ・漢字・全角記号/数字
UI_KW = {'text', 'title', 'label'}
UI_FUNC = {'round_pill', 'section', '_ask_text', 'showerror'}

def main(path):
    src = open(path, encoding='utf-8').read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        for c in ast.iter_child_nodes(node):
            c._parent = node

    errs = []

    # 1) TR 完全性
    TR = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'TR' for t in node.targets):
            try: TR = ast.literal_eval(node.value)
            except Exception: pass
    if not TR:
        errs.append('TR カタログが見つからない/評価不可')
    else:
        allkeys = set().union(*[set(TR[l]) for l in TR])
        for l in TR:
            for k in sorted(allkeys - set(TR[l])):
                errs.append(f'未翻訳: TR["{l}"] にキー "{k}" が無い')

    # 2) UIに渡る日本語リテラルで T() を通さないもの
    skip = set()       # TR/LANG_NAMES 定義の行は対象外（カタログ本体）
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) in ('TR', 'LANG_NAMES') for t in node.targets):
            skip.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))

    def in_T(n):
        while getattr(n, '_parent', None) is not None:
            n = n._parent
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'T':
                return True
        return False

    def is_ui(n):
        p = getattr(n, '_parent', None)
        if isinstance(p, ast.keyword) and p.arg in UI_KW:
            return True
        # 直近の囲みCallがUI関数の位置引数
        q = n
        while getattr(q, '_parent', None) is not None:
            q = q._parent
            if isinstance(q, ast.Call):
                name = getattr(q.func, 'attr', None) or getattr(q.func, 'id', None)
                return name in UI_FUNC or name == 'title'
            if isinstance(q, (ast.FunctionDef, ast.Module)):
                break
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and JP.search(node.value):
            if node.lineno in skip or in_T(node) or not is_ui(node):
                continue
            errs.append(f'L{node.lineno} UIに裸の日本語: {node.value[:40]!r}')

    if errs:
        print('⚠ i18n NG (%d):' % len(errs))
        for e in errs: print('  ' + e)
        sys.exit(1)
    print('✓ i18n OK（カタログ完全・UI文言漏れなし）')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'tbh-price-ocr.py')
