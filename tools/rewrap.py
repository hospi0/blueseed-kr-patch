# -*- coding: utf-8 -*-
r"""받은 번역 조판 검사·자동 줄 다시 접기 (2026-09-29)
  창(상자 폭·줄 한도)은 빌더 groups 로 원문 덩어리마다 구한다(한 ID 가 여러 곳이면 가장 좁은 쪽).
  넘치는 덩어리 → 줄을 이어 붙여 낱말 단위로 다시 접음(상자 폭 안, 줄 한도 안이면 자동 고침)
  못 고치는 것(낱말 하나가 상자보다 넓음 · 줄 한도 초과 · 칸 맞춤 전각 빈칸 줄)은 손질 목록으로.
  python tools/rewrap.py 폴더            → 보고 + work/trans/rewrap_fix.tsv · rewrap_manual.tsv
  python tools/rewrap.py 폴더 --write    → 폴더의 TSV 에 자동 고침 반영
"""
import collections, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build, mes

sys.stdout.reconfigure(encoding='utf-8')
N = chr(92) + 'n'
folder = os.path.abspath(sys.argv[1])
build.TSV = folder
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
    h, msgs, half = build.parse(d)
    hs0 = set(half)
    for mi, segs in enumerate(msgs):
        for bi, (idx, bx, ml) in enumerate(build.groups(segs, hs0)):
            box['%s-%d-%d' % (key, mi, bi)] = (bx, ml)


def px(s):
    return build.encode(build.squeeze(s).rstrip(' 　'), hm, fm, F)[1]


DEP = ('게', '것', '거', '수', '줄', '때', '데', '뿐', '듯', '만큼', '적', '건', '걸')


def cascade(lines, bx):
    """원래 줄바꿈은 살리고, 넘치는 뒤 낱말만 다음 줄 앞으로 넘긴다(연쇄). 의존명사(게·것·수…)가 줄 머리면 앞 낱말도 함께"""
    out = []; carry = []
    for l in lines + [None]:
        if l is None:
            if not carry:
                break
            words = carry; carry = []
        else:
            words = carry + [w for w in l.strip().split(' ') if w]; carry = []
        while words:
            cur = []
            while words:
                cand = ' '.join(cur + [words[0]])
                if px(cand) <= bx:
                    cur.append(words.pop(0))
                else:
                    break
            if not cur:
                return None, '낱말 «%s» %dpx > %d' % (words[0], px(words[0]), bx)
            if words and l is not None:
                carry = words; words = []
            out.append(' '.join(cur))
    for k in range(1, len(out)):                      # 줄 머리 의존명사
        head = out[k].split(' ')[0]
        prev = out[k - 1].split(' ')
        if any(head == d or head.startswith(d) and len(head) <= len(d) + 1 for d in DEP) and len(prev) >= 2:
            cand = prev[-1] + ' ' + out[k]
            if px(cand) <= bx:
                out[k - 1] = ' '.join(prev[:-1]); out[k] = cand
    return out, None


fix = {}; manual = []; ok = 0
for i, t in tr.items():
    ls = [l for l in loc.get(i, []) if not l.startswith('EXE')]
    if not ls:
        continue
    lim = [box[l] for l in ls if l in box]
    if not lim:
        continue
    bx = min(b for b, _ in lim); ml = min(m for _, m in lim)
    lines = t.split(N)
    if all(px(l) <= bx for l in lines) and len(lines) <= ml:
        ok += 1; continue
    tail = re.search('[　]*$', t).group()           # 덩어리 끝 채움(시간 맞춤, 투명)은 떼었다가 다시 붙임
    body = t[:len(t) - len(tail)] if tail else t
    lines = body.split(N)
    if '　　' in body or any(l.startswith('　') for l in lines):
        manual.append((i, bx, ml, '칸 맞춤(전각 빈칸) — 손으로', t)); continue
    out, bad = cascade(lines, bx)
    if not bad and len(out) > ml:                     # 줄바꿈 살리면 줄 한도를 넘음 → 한 문단으로 다시 채움
        out, bad = cascade([' '.join(l.strip() for l in lines)], bx)
    if bad:
        manual.append((i, bx, ml, bad, t)); continue
    if len(out) > ml:
        manual.append((i, bx, ml, '다시 접어도 %d줄 > %d — 줄여야 함' % (len(out), ml), t)); continue
    fix[i] = N.join(out) + tail

print('검사 %d덩어리 · 그대로 통과 %d · 자동 다시 접기 %d · 손질 %d' % (ok + len(fix) + len(manual), ok, len(fix), len(manual)))
print('손질 사유', collections.Counter(m[3].split('«')[0].split(' —')[0].split('다시')[0] for m in manual))
with open(os.path.join(ROOT, 'work', 'trans', 'rewrap_fix.tsv'), 'w', encoding='utf-8') as f:
    f.write('ID\t전\t후\n' + ''.join('%s\t%s\t%s\n' % (i, tr[i], v) for i, v in sorted(fix.items())))
with open(os.path.join(ROOT, 'work', 'trans', 'rewrap_manual.tsv'), 'w', encoding='utf-8') as f:
    f.write('ID\t상자px\t줄한도\t사유\t번역\n' + ''.join('%s\t%d\t%d\t%s\t%s\n' % m for m in manual))
if '--write' in sys.argv:
    n = 0
    for p in sorted(glob.glob(os.path.join(folder, 'blueseed_*.tsv'))):
        L = open(p, encoding='utf-8').read().split('\n'); ch = False
        for k, ln in enumerate(L):
            c = ln.split('\t')
            if len(c) >= 6 and c[0] in fix:
                c[5] = fix[c[0]]; L[k] = '\t'.join(c); ch = True; n += 1
        if ch:
            open(p, 'w', encoding='utf-8').write('\n'.join(L))
    print('반영 %d줄' % n)
