# -*- coding: utf-8 -*-
r"""OCR 판정 후처리 + 대사 풀기 (2026-09-27) — work/glyphmap.tsv → work/glyphfinal.tsv(해시 글자) · work/decoded.txt
  · 모양이 완전히 같은 짝(ヘへ ベべ ペぺ)과 반각 «-»(一/ー 겸용)은 앞뒤 글자 문자 종류 다수결로
  · 작은/큰 가나·탁점/반탁점·가나/한자 닮은꼴은 눈 검토(work/overrides.tsv, 해시 기준)
    ⛔잉크 높이로 작은 가나를 가리면 틀린다(っ 높이 8 / つ 9) — 큰 글자와 나란히 그려 보고 정할 것
  python tools/glyphfix.py
"""
import collections, glob, hashlib, os, pickle, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ocrprep

PAIRS = [('ヘ', 'へ'), ('ベ', 'べ'), ('ペ', 'ぺ'), ('ー', '一')]


def script(ch):
    o = ord(ch) if ch else 0
    if 0x30A0 <= o <= 0x30FF:
        return 'K'
    if 0x3040 <= o <= 0x309F:
        return 'H'
    if 0x4E00 <= o <= 0x9FFF:
        return 'C'
    return None


def hk(g):
    return hashlib.sha1(g).hexdigest()[:16]


def load_map():
    M = {}
    for ln in list(open(os.path.join(ROOT, 'work', 'glyphmap.tsv'), encoding='utf-8'))[1:]:
        c = ln.rstrip('\n').split('\t'); M[c[1]] = c[2]
    return M


def lines():
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc', 'MES', 'S*.MES'))):
        d = open(f, 'rb').read(); half, full = ocrprep.font(d)
        for mi, li, cs in ocrprep.text_lines(d):
            yield os.path.basename(f), mi, li, [ocrprep.glyph(c, half, full) for c in cs]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    M = load_map()
    OV = {l.split('\t')[0] for l in list(open(os.path.join(ROOT, 'work', 'overrides.tsv'), encoding='utf-8'))[1:]}
    ctx = collections.defaultdict(collections.Counter)
    L = list(lines())
    for fn, mi, li, gs in L:
        ks = [hk(g) if g else None for g in gs]
        for j, k in enumerate(ks):
            if k is None:
                continue
            for nb in (j - 1, j + 1):
                if 0 <= nb < len(ks) and ks[nb]:
                    s = script(M.get(ks[nb], ''))
                    if s:
                        ctx[k][s] += 1
    changed = []
    for a, b in PAIRS:
        for k, ch in list(M.items()):
            if k in OV or ch not in (a, b + ('' if b != '一' else '-')) and not (b == '一' and ch == '-'):
                continue
            c = ctx[k]
            if not c:
                continue
            want = a if c[script(a)] >= c.get(script(b), 0) + (c['H'] if b == '一' else 0) else b
            if want != ch:
                changed.append((k, ch, want, dict(c))); M[k] = want
    with open(os.path.join(ROOT, 'work', 'glyphfinal.tsv'), 'w', encoding='utf-8') as f:
        f.write('해시\t글자\n')
        for k in sorted(M):
            f.write('%s\t%s\n' % (k, M[k]))
    out = []
    for fn, mi, li, gs in L:
        out.append('%s\t%d\t%d\t%s' % (fn, mi, li, ''.join('　' if g == b'' else '·' if g is None else M.get(hk(g), '?') for g in gs)))
    open(os.path.join(ROOT, 'work', 'decoded.txt'), 'w', encoding='utf-8').write('\n'.join(out))
    print('고침 %d · 줄 %d' % (len(changed), len(out)))
    for c in changed[:20]:
        print('  ', c)


if __name__ == '__main__':
    main()
