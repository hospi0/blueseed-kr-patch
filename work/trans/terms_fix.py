# -*- coding: utf-8 -*-
"""받은 번역 용어 통일 2단계 (2026-09-29 사용자 결정)
 勾玉=곡옥 · 葦舟=갈대배 · 闇鬼=암귀 · 奇稲田之剣=쿠시나다의 검 · 人柱(별명)=히토바시라 · 인명·지명 거센소리
 받침이 바뀌는 말은 뒤 조사도 맞춘다.  python work/trans/terms_fix.py"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 받침 없음 → 있음 / 있음 → 없음 조사 짝
TO_BAT = [('가', '이'), ('를', '을'), ('는', '은'), ('와', '과'), ('로', '으로'), ('라', '이라'), ('야', '이야'),
          ('예요', '이에요'), ('랑', '이랑'), ('나', '이나'), ('다', '이다'), ('여', '이여')]


def swap(t, old, new, old_bat, new_bat):
    """old → new, 뒤 조사 받침 맞춤"""
    if old_bat == new_bat:
        return t.replace(old, new)
    pairs = TO_BAT if new_bat else [(b, a) for a, b in TO_BAT]
    out = ''; p = 0
    while True:
        j = t.find(old, p)
        if j < 0:
            return out + t[p:]
        out += t[p:j] + new; p = j + len(old)
        for a, b in sorted(pairs, key=lambda x: -len(x[0])):
            if t.startswith(a, p) and not re.match(r'[가-힣]', t[p + len(a):p + len(a) + 1] or ' ') or \
               t.startswith(a, p) and a in ('예요', '이에요'):
                out += b; p += len(a); break


# (옛말, 새말, 옛말 받침, 새말 받침)
R = [('쿠시나다노츠루기', '쿠시나다의 검', False, True), ('쿠시나다노 츠루기', '쿠시나다의 검', False, True),
     ('구시나다의 검', '쿠시나다의 검', True, True), ('키나다의 검', '쿠시나다의 검', True, True),
     ('키나다 비록', '쿠시나다 비록', False, False), ('키나다', '쿠시나다', False, False), ('구시나다', '쿠시나다', False, False),
     ('마가타마', '곡옥', False, True), ('아시부네', '갈대배', False, False),
     ('어둠귀신', '암귀', True, False), ('야미키', '암귀', False, False),
     ('인주 걸', '히토바시라 걸', True, True), ('인주\\n전설', '히토바시라\\n전설', True, True), ('“인주”', '“히토바시라”', True, True),
     ('도쿠하라', '토쿠하라', False, False), ('가스미', '카스미', False, False), ('게곤', '케곤', True, True),
     ('구마모토', '쿠마모토', False, False), ('규슈', '큐슈', False, False), ('도쿠가와', '토쿠가와', False, False),
     ('도쇼구', '토쇼구', False, False), ('구사미카도', '쿠사미카도', False, False), ('구풍', '구후', True, False),
     ('용천의', '류센의', True, True)]
cnt = {}
for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'trans', 'recv', 'blueseed_*.tsv'))):
    L = open(p, encoding='utf-8').read().split('\n'); ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) < 6:
            continue
        t = c[5]
        for old, new, ob, nb in R:
            if old in t:
                cnt[old] = cnt.get(old, 0) + t.count(old)
                t = swap(t, old, new, ob, nb)
        if t != c[5]:
            c[5] = t; L[k] = '\t'.join(c); ch = True
    if ch:
        open(p, 'w', encoding='utf-8').write('\n'.join(L))
for old, new, _, _ in R:
    print('%s → %s  %d' % (old, new, cnt.get(old, 0)))
