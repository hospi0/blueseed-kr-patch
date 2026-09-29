# -*- coding: utf-8 -*-
r"""칸 맞춤 줄 다시 맞추기 (2026-09-29): 전각 빈칸 2개 이상으로 시작하는 줄(오른쪽 서명·가격)은 글 폭에 맞춰
  빈칸 수를 다시 셈(상자 오른쪽 끝에 붙임 — 원문 방식). 줄 가운데 «　　» 두 칸은 한 칸으로.
  python tools/realign.py 번역폴더 [--write]  → 고친 것과 여전히 넘치는 줄 보고"""
import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build, mes

sys.stdout.reconfigure(encoding='utf-8')
N = chr(92) + 'n'
folder = os.path.abspath(sys.argv[1]); build.TSV = folder
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import bdf
F = bdf.Font(build.GALMURI)
hm, fm = build.glyph_maps()
tr = build.load_tr(); loc = build.load_ids()
box = {}
for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc', 'MES', 'S*.MES'))):
    d = open(f, 'rb').read(); key = os.path.basename(f).split('.')[0]
    if mes.header(d)[6] == 0:
        continue
    h, msgs, half = build.parse(d); hs0 = set(half)
    for mi, segs in enumerate(msgs):
        for bi, (idx, bx, ml) in enumerate(build.groups(segs, hs0)):
            box['%s-%d-%d' % (key, mi, bi)] = (bx, ml)


def px(s):
    return build.encode(build.squeeze(s).rstrip(' 　'), hm, fm, F)[1]


fix = {}; still = []
for i, t in tr.items():
    lim = [box[l] for l in loc.get(i, []) if l in box]
    if not lim:
        continue
    bx = min(b for b, _ in lim); ml = min(m for _, m in lim)
    lines = t.split(N)
    if all(px(l) <= bx for l in lines) and len(lines) <= ml:
        continue
    out = []
    for l in lines:
        m = re.match('^(　{2,}| {4,}　*)(.*)$', l)
        if m and m.group(2).strip():
            body = m.group(2).strip(' 　')
            k = max(0, (bx - px(body)) // 16)
            l = '　' * k + body
        out.append(l)
    bad = [l for l in out if px(l) > bx]
    new = N.join(out)
    if new != t:
        fix[i] = new
    if bad or len(out) > ml:
        still.append((i, bx, ml, new, bad))
print('다시 맞춤 %d · 여전히 넘침 %d' % (len(fix), len(still)))
for i, bx, ml, new, bad in still:
    print('%s\t%d\t%d\t%s\t%s' % (i, bx, ml, new, ' / '.join('%s(%d)' % (b, px(b)) for b in bad)))
if '--write' in sys.argv:
    n = 0
    for p in sorted(glob.glob(os.path.join(folder, 'blueseed_*.tsv'))):
        L = open(p, encoding='utf-8').read().split('\n'); ch = False
        for k, ln in enumerate(L):
            c = ln.split('\t')
            if len(c) >= 6 and c[0] in fix and c[5] != fix[c[0]]:
                c[5] = fix[c[0]]; L[k] = '\t'.join(c); ch = True; n += 1
        if ch:
            open(p, 'w', encoding='utf-8').write('\n'.join(L))
    print('반영 %d줄' % n)
