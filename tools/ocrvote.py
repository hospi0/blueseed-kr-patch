# -*- coding: utf-8 -*-
r"""OCR 표 → 글리프 판정 (2026-09-27)
  칸 간격 고정 → 인식 글자의 가로 중심으로 칸 번호를 짚는다(단어 상자는 글자 수로 균등 분할)
  글리프(그림 키)마다 다수결 → work/glyphmap.tsv «키 글자 득표 총표 확신도 후보…»
  덮어쓰기 work/overrides.tsv «해시(sha1 앞 16자) 글자 근거» 가 늘 우선(눈 검토 결과) — 키 번호는 ocrprep 를 돌릴 때마다 바뀐다
  python tools/ocrvote.py [work/ocr …]
"""
import collections, hashlib, json, os, sys, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)


def nk(ch):
    return unicodedata.normalize('NFKC', ch)


def read_votes(dirs):
    votes = collections.defaultdict(collections.Counter); ok = tot = 0
    for D in dirs:
        L = json.load(open(os.path.join(D, 'layout.json'), encoding='utf-8'))
        pitch, x0, lh, gh = L['pitch'], L['x0'], L['lineh'], L['glyph']
        for im in L['images']:
            p = os.path.join(D, im['img'].replace('.png', '.txt'))
            if not os.path.exists(p):
                continue
            for row in open(p, encoding='utf-8-sig'):
                f = row.rstrip('\n').split('\t')
                if len(f) < 5 or not f[0].replace(' ', ''):
                    continue
                text = f[0].replace(' ', '')
                X, Y, W, H = map(float, f[1:5])
                cy = Y + H / 2
                li = min(range(len(im['lines'])), key=lambda i: abs(im['lines'][i]['y'] + gh / 2 - cy))
                line = im['lines'][li]
                if abs(line['y'] + gh / 2 - cy) > lh / 2:
                    continue
                n = len(text)
                for i, ch in enumerate(text):
                    j = int((X + (i + 0.5) * W / n - x0) // pitch)
                    if not 0 <= j < len(line['cells']):
                        continue
                    if line['cells'][j] is None:
                        if line['known'][j] and line['known'][j] != ' ':
                            tot += 1; ok += nk(ch).lower() == line['known'][j]
                        continue
                    votes[line['cells'][j]][ch] += 1
    return votes, ok, tot


def load_overrides():
    p = os.path.join(ROOT, 'work', 'overrides.tsv'); o = {}
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8'):
            c = ln.rstrip('\n').split('\t')
            if len(c) >= 2 and len(c[0]) == 16 and c[0] != '해시':
                o[c[0]] = c[1]
    return o


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    dirs = sys.argv[1:] or [os.path.join(ROOT, 'work', 'ocr')]
    votes, ok, tot = read_votes(dirs)
    import pickle
    keys = pickle.load(open(os.path.join(ROOT, 'work', 'glyphkeys.pkl'), 'rb'))
    ov = load_overrides()
    rows = []; conf = collections.Counter()
    for k in range(len(keys)):
        v = votes.get(k, collections.Counter()); t = sum(v.values())
        hk = hashlib.sha1(keys[k]).hexdigest()[:16]
        if hk in ov:
            ch, n, c = ov[hk], t, 1.0; conf['덮어쓰기'] += 1
        elif t:
            ch, n = v.most_common(1)[0]; c = n / t
            conf['확신 ≥0.8' if c >= 0.8 else '0.5‥0.8' if c >= 0.5 else '<0.5'] += 1
        else:
            ch, n, c = '?', 0, 0.0; conf['표 없음'] += 1
        rows.append((k, hashlib.sha1(keys[k]).hexdigest()[:16], ch, n, t, c, ' '.join('%s%d' % x for x in v.most_common(4))))
    with open(os.path.join(ROOT, 'work', 'glyphmap.tsv'), 'w', encoding='utf-8') as f:
        f.write('키\t해시\t글자\t득표\t총표\t확신도\t후보\n')
        for r in rows:
            f.write('%d\t%s\t%s\t%d\t%d\t%.2f\t%s\n' % r)
    print('반각 검산 %d/%d' % (ok, tot), dict(conf))


if __name__ == '__main__':
    main()
