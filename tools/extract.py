# -*- coding: utf-8 -*-
r"""블루 시드 번역용 원문 추출 (2026-09-27)
  단위 = 메시지 안에서 명령(FF FF …) 사이에 이어진 글 줄 덩어리(창 한 번) — 줄은 «\n»
  글자 = 판독표 work/glyphfinal.tsv(해시 → 글자, 반각 51자 포함 — 빈 반각 = « »), 판독 못 한 칸 = «·», 글 줄 안 명령 = «{1E28010401}»(FF FF 뺀 16진)
  같은 글은 한 번만: → my files/tsv/blueseed_NNN.tsv (29KB, 열: ID 위치 구분 공유 원문 번역) + blueseed_전체.tsv
                     work/trans/ids.tsv (ID → 전체 위치 파일:메시지:덩어리)
  python tools/extract.py
"""
import glob, hashlib, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import mes, ocrprep, build

CHUNK = 29 * 1024
EXE_MES = (0x9F12C, 0xAB43C)            # 실행 파일 /0 속 MES 구역(RAM 0x060AF12C)


def blocks(d, F):
    """[(메시지 번호, 덩어리 번호, 글)]"""
    half, full = ocrprep.font(d)
    out = []
    for mi, (o, b) in enumerate(mes.messages(d)):
        cur = []; bi = 0
        for seg in ocrprep.segments(b):
            if build.is_cmd(seg):                    # 인라인 명령으로 시작하는 글 줄은 글(build.is_cmd)
                if cur:
                    out.append((mi, bi, '\\n'.join(cur))); bi += 1; cur = []
                continue
            gs = build.tokens(seg, half, full)       # 인라인 명령(FF FF …)은 «{1E28010401}» 표기로
            cur.append(''.join('{%s}' % g[2:].hex().upper() if isinstance(g, build.Cmd)
                               else F.get(hashlib.sha1(g).hexdigest()[:16], '·') for g in gs))
        if cur:
            out.append((mi, bi, '\\n'.join(cur)))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    F = {l.split('\t')[0]: l.rstrip('\n').split('\t')[1] for l in list(open(os.path.join(ROOT, 'work', 'glyphfinal.tsv'), encoding='utf-8'))[1:]}
    seen = {}; rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc', 'MES', 'S*.MES'))):
        fn = os.path.basename(f).split('.')[0]
        for mi, bi, t in blocks(open(f, 'rb').read(), F):
            loc = '%s-%d-%d' % (fn, mi, bi)
            if t in seen:
                seen[t].append(loc); continue
            seen[t] = [loc]; rows.append(t)
    # 실행 파일 속 MES(시스템 글 — 저장 화면·화 제목·아이템·편지 …) → ID «X0001»‥, 파일 blueseed_실행파일.tsv
    xseen = {}; xrows = []
    for mi, bi, t in blocks(open(os.path.join(ROOT, 'work', 'disc', '0'), 'rb').read()[EXE_MES[0]:EXE_MES[1]], F):
        loc = 'EXE-%d-%d' % (mi, bi)
        if t in xseen:
            xseen[t].append(loc); continue
        xseen[t] = [loc]; xrows.append(t)
    os.makedirs(os.path.join(ROOT, 'work', 'trans'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'trans', 'ids.tsv'), 'w', encoding='utf-8') as f:
        f.write('ID\t위치…\n')
        for i, t in enumerate(rows):
            f.write('%05d\t%s\n' % (i + 1, '\t'.join(seen[t])))
        for i, t in enumerate(xrows):
            f.write('X%04d\t%s\n' % (i + 1, '\t'.join(xseen[t])))
    tdir = os.path.join(ROOT, 'my files', 'tsv'); os.makedirs(tdir, exist_ok=True)
    for x in os.listdir(tdir):
        if x.startswith('blueseed_'):
            os.remove(os.path.join(tdir, x))
    head = 'ID\t위치\t구분\t공유\t원문\t번역\n'
    lines = ['%05d\t%s\t대사\t%d\t%s\t\n' % (i + 1, seen[t][0], len(seen[t]), t) for i, t in enumerate(rows)]
    files = []; buf = head
    for ln in lines:
        if len((buf + ln).encode('utf-8')) > CHUNK and buf != head:
            files.append(buf); buf = head
        buf += ln
    files.append(buf)
    for n, t in enumerate(files):
        open(os.path.join(tdir, 'blueseed_%03d.tsv' % (n + 1)), 'w', encoding='utf-8').write(t)
    open(os.path.join(tdir, 'blueseed_전체.tsv'), 'w', encoding='utf-8').write(head + ''.join(lines))
    open(os.path.join(tdir, 'blueseed_실행파일.tsv'), 'w', encoding='utf-8').write(
        head + ''.join('X%04d\t%s\t시스템\t%d\t%s\t\n' % (i + 1, xseen[t][0], len(xseen[t]), t) for i, t in enumerate(xrows)))
    xch = sum(len(re.sub(r'\\n', '', t)) for t in xrows)
    print('실행 파일: 덩어리 %d (출현 %d) · 글자 %d · 미판독 칸 %d'
          % (len(xrows), sum(len(v) for v in xseen.values()), xch, sum(t.count('·') for t in xrows)))
    chars = sum(len(re.sub(r'\\n', '', t)) for t in rows)
    W = [len(x) for t in rows for x in t.split('\\n')]
    unk = sum(t.count('·') for t in rows)
    print('덩어리 %d (출현 %d) · 글자 %d · 파일 %d개 · 줄 폭 최대 %d (95%% ≤ %d) · 미판독 칸 %d'
          % (len(rows), sum(len(v) for v in seen.values()), chars, len(files), max(W), sorted(W)[int(len(W) * .95)], unk))


if __name__ == '__main__':
    main()
