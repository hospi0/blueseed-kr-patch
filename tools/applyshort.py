# -*- coding: utf-8 -*-
r"""손질 번역(ID \t 새 번역) 검사 → 통과분만 번역 폴더에 반영 (2026-09-29)
  python tools/applyshort.py 번역폴더 손질.tsv [--write]"""
import glob, os, sys
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
loc = build.load_ids()
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
    t, p, _, bad = build.encode(build.squeeze(s).rstrip(' 　'), hm, fm, F)
    return p, bad


new = {}
for ln in open(sys.argv[2], encoding='utf-8').read().split('\n'):
    if '\t' in ln:
        i, t = ln.split('\t', 1); new[i.strip()] = t.rstrip('\r')
good = {}; nbad = 0
for i, t in new.items():
    lim = [box[l] for l in loc.get(i, []) if l in box]
    bx = min(b for b, _ in lim); ml = min(m for _, m in lim)
    lines = t.split(N); errs = []
    if len(lines) > ml:
        errs.append('줄 %d > %d' % (len(lines), ml))
    for l in lines:
        p, bad = px(l)
        if bad:
            errs.append('모르는 글자 %s' % ''.join(bad))
        if p > bx:
            errs.append('«%s» %dpx > %d' % (l, p, bx))
    if errs:
        nbad += 1; print('✗', i, '; '.join(errs))
    else:
        good[i] = t
print('통과 %d · 실패 %d' % (len(good), nbad))
if '--write' in sys.argv:
    n = 0
    for p in sorted(glob.glob(os.path.join(folder, 'blueseed_*.tsv'))):
        L = open(p, encoding='utf-8').read().split('\n'); ch = False
        for k, ln in enumerate(L):
            c = ln.split('\t')
            if len(c) >= 6 and c[0] in good and c[5] != good[c[0]]:
                c[5] = good[c[0]]; L[k] = '\t'.join(c); ch = True; n += 1
        if ch:
            open(p, 'w', encoding='utf-8').write('\n'.join(L))
    print('반영 %d줄' % n)
