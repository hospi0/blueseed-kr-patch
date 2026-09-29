# -*- coding: utf-8 -*-
"""사용자 실행 파일 번역(my files/번역완료) → 작업본 work/trans/exe/blueseed_실행파일.tsv
  ① 줄바꿈 «\\n»(이스케이프 두 겹) → «\n» ② 荒神 = 아라가미 통일(사용자 2026-09-27) — 받침 따라 조사도 ③ 줄임 표(fix.tsv) 덮어쓰기
"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(ROOT, 'my files', '번역완료', 'blueseed_실행파일_번역완료.tsv')
DST = os.path.join(HERE, 'blueseed_실행파일.tsv')
FIX = os.path.join(HERE, 'fix.tsv')
BS = chr(92)

TERMS = [('코진(荒神)', '아라가미'), ('대(對)코진', '대아라가미'),
         ('코진이', '아라가미가'), ('코진은', '아라가미는'), ('코진을', '아라가미를'),
         ('코진과', '아라가미와'), ('코진으로', '아라가미로'), ('코진', '아라가미')]

rows = open(SRC, encoding='utf-8').read().split('\n')
fix = {}
if os.path.exists(FIX):
    for l in open(FIX, encoding='utf-8').read().split('\n')[1:]:
        if l.strip():
            i, t = l.split('\t', 1)
            fix[i] = t
out = [rows[0]]; n = 0
for l in rows[1:]:
    if not l:
        continue
    c = l.split('\t')
    c[4] = c[4].replace(BS * 2 + 'n', BS + 'n')
    t = c[5].replace(BS * 2 + 'n', BS + 'n')
    for a, b in TERMS:
        t = t.replace(a, b)
    if c[0] in fix:
        t = fix[c[0]]; n += 1
        if t == '=원문':                 # 원본 바이트 그대로(번역 비움) — 버튼 글자·0N/0FF 는 원문이 전각 글리프
            t = ''
    c[5] = t
    out.append('\t'.join(c))
open(DST, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
left = sum(r.split('\t')[5].count('코진') for r in out[1:])
print('→', DST, '· 줄임 표 적용 %d · 남은 «코진» %d' % (n, left))
