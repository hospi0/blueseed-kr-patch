# -*- coding: utf-8 -*-
"""받은 번역(work/trans/recv) 일괄 손질 1단계 (2026-09-29, 사용자 승인: 거센소리 통일·글꼴 밖 글자)
 python work/trans/recv_fix.py"""
import glob, os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUB = [
    # 荒神 = 아라가미(사용자 결정) — 받침 바뀌는 조사까지
    ('대(對) 코진전', '대 아라가미전'), ('코진의', '아라가미의'), ('코진 발견', '아라가미 발견'), ('코진이라', '아라가미라'),
    ('란(亂)', '란'),
    # 거센소리 통일(사용자 2026-09-29)
    ('마쓰다이라', '마츠다이라'), ('다이테쓰', '다이테츠'), ('구니키다', '쿠니키다'), ('다케우치', '타케우치'),
    ('구사나기', '쿠사나기'), ('고우메', '코우메'),
    # 글꼴 밖 부호
    ('―', 'ー'), ('·', '・'), ('＋', '+'), ('‘', "'"), ('’', "'"),
]
cnt = {a: 0 for a, _ in SUB}
for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'trans', 'recv', 'blueseed_*.tsv'))):
    L = open(p, encoding='utf-8').read().split('\n'); ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) < 6:
            continue
        t = c[5]
        for a, b in SUB:
            if a in t:
                cnt[a] += t.count(a); t = t.replace(a, b)
        if t != c[5]:
            c[5] = t; L[k] = '\t'.join(c); ch = True
    if ch:
        open(p, 'w', encoding='utf-8').write('\n'.join(L))
for a, b in SUB:
    print('%s → %s  %d' % (a, b, cnt[a]))
