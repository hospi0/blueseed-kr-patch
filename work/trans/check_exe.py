# -*- coding: utf-8 -*-
"""실행 파일 번역 예행 검사 — 창 폭(1D 명령)·줄 수·글자 → work/trans/exe_overflow.tsv"""
import sys
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools'); sys.path.insert(0, 'tools')
import build, bdf
sys.stdout.reconfigure(encoding='utf-8')
F = bdf.Font(build.GALMURI); hm, fm = build.glyph_maps()
x = open('work/disc/0', 'rb').read(); d = x[build.EXE_MES[0]:build.EXE_MES[1]]
h, msgs, half = build.parse(d)
HALF = '0123456789abcdefghijklmnopqrstuvwxyz_?! FLGMS-YD+AIEX%V'
NL = chr(92) + 'n'


def win(segs):
    for k, s in segs:
        if k == 'c' and s[:3] == b'\xff\xff\x1d':
            t = ''.join(HALF[b - 1] for b in s[3:]).split()
            return int(t[1]), int(t[2])
    return None


rows = open('work/trans/exe/blueseed_실행파일.tsv', encoding='utf-8').read().split('\n')[1:]
errs = []
for l in rows:
    if not l:
        continue
    c = l.split('\t'); tid, loc = c[0], c[1]
    tr = c[5].replace(chr(92) * 2 + 'n', NL); src = c[4].replace(chr(92) * 2 + 'n', NL)
    mi, bi = map(int, loc.split('-')[1:])
    w = win(msgs[mi]); box = w[0] if w else 272; maxl = w[1] // 16 if w else len(src.split(NL))
    lines = [build.align_stats(build.squeeze(s), box, hm, fm, F) for s in tr.split(NL)]
    for ln in lines:
        toks, px, hh, bad = build.encode(ln, hm, fm, F)
        if bad:
            errs.append((tid, '글자 ' + ''.join(bad), ln))
        if px > box:
            errs.append((tid, '%dpx>%d (%+d)' % (px, box, px - box), ln))
    if len(lines) > maxl:
        errs.append((tid, '줄 %d>%d' % (len(lines), maxl), ''))
print('오류', len(errs))
with open('work/trans/exe_overflow.tsv', 'w', encoding='utf-8') as f:
    f.write('ID\t문제\t줄\n')
    for e in errs:
        f.write('\t'.join(e) + '\n')
