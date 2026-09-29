# -*- coding: utf-8 -*-
r"""블루 시드 대사 파일(MES/S*.MES) 전체 되넣기 (2026-09-27)
  파일 = 머리 | 스크립트 등(h[6] 앞, 그대로) | 메시지 표+본문(h[6], 크기 h[7]) | 글꼴(h[8], 크기 h[9])
    머리 h[10]‥ 은 오프셋이 아니라 번호(여러 파일에 같은 값) → 건드리지 않는다. 고치는 값은 h[7]·h[8]·h[9] 뿐.
  메시지 표 = [u32 오프셋(표 시작 기준)][u32 크기] × n, 본문은 4바이트 정렬로 이어 붙임
  글꼴 = 14B 머리(+12 = 반각 수 N) + 반각 8×16 N개 + 전각 16×16 + 4바이트 채움
    글자 번호: 1‥N 반각[번호−1] · N+1‥ 전각[번호−N−1] · ≥0x80 이면 2바이트 (0x80|v>>8, v&0xFF), v = 번호−0x80
  글꼴은 그 파일에 쓰인 글리프만, 쓰인 횟수 순(자주 쓰는 글자가 1바이트 번호)
  번역: my files/tsv/blueseed_전체.tsv 번역 열(덩어리 ID → work/trans/ids.tsv 위치) — 빈 칸은 원문 글리프 그대로
  python tools/build.py            → 왕복 검사 + work/kr/MES/*.MES
  python tools/build.py --write    → 디스크(work/out) 까지
"""
import collections, glob, hashlib, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import mes, ocrprep

BUF = 0x30000                       # MES 버퍼 malloc 크기(리터럴 0x060134E8)
EXE_MES = (0x9F12C, 0xAB43C)            # 실행 파일 /0 속 MES 구역(RAM 0x060AF12C, 자리 고정 49,936B)
INLINE = {0x1E: 4, 0x1A: 0, 0x13: 0, 0x0D: 0}   # 글 줄 안의 «FF FF 명령 인수…» — 명령별 인수 바이트 수(전 파일 13곳)


class Cmd(bytes):
    """글 줄 안 인라인 명령(FF FF 포함 원바이트) — 글리프 바이트와 구별"""


def tokens(s, half, full):
    out = []; i = 0
    while i < len(s):
        if s[i] == 0xFF:
            assert s[i + 1] == 0xFF, s.hex()
            n = 3 + INLINE[s[i + 2]]
            out.append(Cmd(s[i:i + n])); i += n; continue
        if s[i] >= 0x80:
            c = ((s[i] & 0x7F) << 8 | s[i + 1]) + 0x80; i += 2
        else:
            c = s[i]; i += 1
        g = ocrprep.glyph(c, half, full)
        assert g is not None, (c, s.hex())
        out.append(g)
    return out


def hk(g):
    return hashlib.sha1(g).hexdigest()[:16]


def parse(d):
    """→ 머리 값, [메시지별 조각 목록: ('c', 명령 바이트) | ('t', [글리프 바이트…])], 반각 목록"""
    h = mes.header(d)
    half, full = ocrprep.font(d)
    msgs = []
    for o, b in mes.messages(d):
        segs = []
        for s in ocrprep.segments(b):
            if s[:2] == b'\xff\xff' or not s or s[:1] == b'\x00':
                segs.append(('c', s))
            else:
                segs.append(('t', tokens(s, half, full)))
        msgs.append(segs)
    return h, msgs, half


def code_bytes(c):
    if c < 0x80:
        return bytes([c])
    v = c - 0x80
    assert v < 0x8000
    return bytes([0x80 | v >> 8, v & 0xFF])


def rebuild(d, msgs, half):
    """조각 목록(글리프 바이트) → 새 파일 바이트. half = 반각 글리프 목록(번호 1‥N 순서)"""
    h = mes.header(d)
    N = len(half)
    hidx = {g: k + 1 for k, g in enumerate(half)}
    cnt = collections.Counter(g for segs in msgs for kind, x in segs if kind == 't' for g in x
                              if not isinstance(g, Cmd) and g not in hidx)
    fulls = [g for g, _ in sorted(cnt.items(), key=lambda t: -t[1])]
    fidx = {g: N + 1 + k for k, g in enumerate(fulls)}
    code = dict(fidx); code.update(hidx)
    area = bytearray(); offs = []
    n = len(msgs)
    for segs in msgs:
        b = b'\xff\xfe'.join(x if kind == 'c' else b''.join(g if isinstance(g, Cmd) else code_bytes(code[g]) for g in x) for kind, x in segs)
        offs.append((8 * n + len(area), len(b)))
        area += b + bytes(-len(b) % 4)
    table = b''.join(struct.pack('>II', o, s) for o, s in offs)
    msec = table + bytes(area)
    fo_old = h[8]
    fhead = bytearray(d[fo_old:fo_old + 14]); struct.pack_into('>H', fhead, 12, N)
    font = bytes(fhead) + b''.join(half) + b''.join(fulls)
    t = h[6]
    fo = t + len(msec)
    font += bytes(-(fo + len(font)) % 4)
    hb = bytearray(d[:t])
    struct.pack_into('>III', hb, 4 * 7, len(msec), fo, len(font))
    return bytes(hb) + msec + font, len(fulls)


GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
FACE_PX, NOFACE_PX = 160, 272           # 상자 폭: 얼굴 있음(0x10 뒤·명령 전) / 얼굴 없음(0x18 뒤) — 원문 줄 폭 분포 벼랑 10칸·17칸
FACE_LINES, NOFACE_LINES = 5, 3         # 창 한 번 줄 수(원문 최대)
FULL_TESTED = 722                       # 실기로 확인한 전각 칸 수(PoC 2차). 넘으면 경고
TSV = os.path.join(ROOT, 'my files', 'tsv')
EXE_TSV = os.path.join(ROOT, 'work', 'trans', 'exe', 'blueseed_실행파일.tsv')   # 실행 파일 번역 작업본(아라가미 통일·줄임 반영)
EXE_HALF = '0123456789abcdefghijklmnopqrstuvwxyz_?! FLGMS-YD+AIEX%V'
if '--tsv' in sys.argv:                 # 시험용 번역 폴더(예: work/trans/test)
    TSV = os.path.abspath(sys.argv[sys.argv.index('--tsv') + 1])
# 반각 쉼표(원본 반각 51종에 없음) — 마침표(12‥13행 3‥4열) 모양에 꼬리
COMMA = bytes(12) + bytes([0x18, 0x18, 0x08, 0x10])


def squeeze(t):
    """부호 뒤 공백 삭제(전프로젝트 규칙 — 빌더에서 무조건)"""
    import re
    # ★전프로젝트 규칙: 모든 문장부호 뒤 띄어쓰기 1칸(반각·전각) 삭제. 2칸 이상 이어진 것은 칸 맞춤 채움이라 둔다
    return re.sub('([' + re.escape(PUNCT) + '])[ 　](?![ 　])', r'\1', t)


# 문장부호 전부(메모리 feedback_no_space_after_punct 와 같은 목록)
PUNCT = (",.!?:;)]}'\"~"
         "、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥")


def glyph_maps():
    """판독표로 «글자 → 원본 글리프»(반각·전각) — 전 파일에서 모음"""
    M = {l.split('\t')[0]: l.rstrip('\n').split('\t')[1]
         for l in list(open(os.path.join(ROOT, 'work', 'glyphfinal.tsv'), encoding='utf-8'))[1:]}
    hm, fm = {}, collections.Counter()
    fmap = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc', 'MES', 'S*.MES'))):
        d = open(f, 'rb').read()
        if mes.header(d)[6] == 0:
            continue
        half, full = ocrprep.font(d)
        for g in half:
            c = M.get(hk(g))
            if c is not None:
                hm.setdefault(c, g)
        for g in full:
            c = M.get(hk(g))
            if c is not None and c != '·':
                fmap.setdefault(c, g)
    # 실행 파일 속 MES 글꼴(반각 Y·D·+·A·I·X, 전용 한자 閃·拳 …)도
    x = open(os.path.join(ROOT, 'work', 'disc', '0'), 'rb').read()[EXE_MES[0]:EXE_MES[1]]
    half, full = ocrprep.font(x)
    for g in half:
        c = M.get(hk(g))
        if c is not None:
            hm.setdefault(c, g)
    for g in full:
        c = M.get(hk(g))
        if c is not None and c != '·':
            fmap.setdefault(c, g)
    hm[','] = COMMA
    hm.setdefault('O', hm['0'])          # 반각 O 없음 — 원문도 «0FF» 처럼 숫자 0 을 쓴다
    fmap.pop(' ', None)
    return hm, fmap


def hangul(F, ch, cache={}):
    if ch not in cache:
        pts, _ = F.draw(ch, 0, -4)
        g = bytearray(32)
        for x, y in pts:
            if 0 <= x < 16 and 0 <= y < 16:
                g[2 * y + x // 8] |= 0x80 >> (x % 8)
        cache[ch] = bytes(g)
    return cache[ch]


def load_tr():
    """my files/tsv 의 번역 열 → {ID: 번역}. 쪼갠 파일(blueseed_001‥)과 전체 파일 둘 다 읽고, 같은 ID 가 다르면 오류"""
    tr = {}
    for p in sorted(glob.glob(os.path.join(TSV, 'blueseed_*.tsv'))) + [EXE_TSV]:
        for ln in open(p, encoding='utf-8').read().split('\n')[1:]:
            c = ln.split('\t')
            if len(c) >= 6 and c[5].strip(' \r\n'):
                # rstrip 은 줄바꿈 문자만 — 전각 빈칸(　)은 원문도 빈 줄 자리에 쓰므로 지우면 안 된다
                t = c[5].rstrip('\r\n').replace(chr(92) * 2 + 'n', chr(92) + 'n')   # 두 겹 이스케이프 줄바꿈도 받는다
                assert tr.get(c[0], t) == t, ('번역이 두 파일에서 다름', c[0], p)
                tr[c[0]] = t
    return tr


def load_ids():
    loc = {}
    for ln in open(os.path.join(ROOT, 'work', 'trans', 'ids.tsv'), encoding='utf-8').read().split('\n')[1:]:
        if ln:
            c = ln.split('\t')
            loc[c[0]] = c[1:]
    return loc


def line_px(toks, hs):
    """줄 폭 px — 끝의 빈 글리프(원문이 시간 맞춤용으로 붙이는 «　　　» 채움)는 뺀다: 넘쳐 되감겨도 투명이라 안 보인다"""
    s = list(toks)
    while s and not isinstance(s[-1], Cmd) and not any(s[-1]):
        s.pop()
    return sum(0 if isinstance(g, Cmd) else 8 if (len(g) == 16 or g in hs) else 16 for g in s)


def groups(segs, hs=()):
    """글 줄 덩어리(창 한 번) → [(조각 번호 목록, 상자 폭, 줄 한도)]
    창 = 0x10(얼굴) 뒤 160px·5줄 / 0x18(얼굴 끔) 뒤 272px·3줄. 창 상태는 메시지를 건너 이어지므로(명령 없는 메시지)
    원문 덩어리가 스스로 다른 창임을 보이면 그쪽: 176px 넘는 줄 → 넓은 창 · 4줄 이상이고 전부 176px 이하 → 얼굴 창"""
    out = []; cur = []; face = True

    def close():
        wide = max(line_px(segs[i][1], hs) for i in cur) > FACE_PX + 16
        f = face
        if f and wide:
            f = False
        elif not f and not wide and len(cur) > NOFACE_LINES:
            f = True
        # 줄 한도 = 창 규칙과 원문 덩어리 줄 수 중 큰 쪽(원문이 그만큼 보여 준다 — 쪽 넘김 명령이 낀 덩어리 등)
        out.append((list(cur), FACE_PX if f else NOFACE_PX, max(FACE_LINES if f else NOFACE_LINES, len(cur))))
    for i, (k, x) in enumerate(segs):
        if k == 't':
            cur.append(i); continue
        if cur:
            close(); cur = []
        if x[:2] == b'\xff\xff' and len(x) > 2:
            if x[2] == 0x10: face = True
            elif x[2] == 0x18: face = False
    if cur:
        close()
    return out


def groups_exe(segs, orig_lines):
    """실행 파일 MES: 창 폭·줄 수 = 메시지 첫 «FF FF 1D 모드 폭 높이 x y»(반각 숫자). 없으면 272px·원문 줄 수"""
    w = None
    for k, x in segs:
        if k == 'c' and x[:3] == bytes([0xFF, 0xFF, 0x1D]):
            t = ''.join(EXE_HALF[b - 1] for b in x[3:]).split()
            w = (int(t[1]), int(t[2]) // 16)
            break
    out = []; cur = []
    for i, (k, x) in enumerate(segs + [('c', b'')]):
        if k == 't':
            cur.append(i); continue
        if cur:
            out.append((cur, w[0] if w else NOFACE_PX, w[1] if w else len(cur))); cur = []
    return out


STAT_RE = r'^(.*?)[ 　]*((?:[SDA]\+\d+ ?)+|LIFE\+\d+|LF\+\d+|LIFEMAX|？？)$'


def align_stats(line, box, hm, fm, F):
    """«이름 … 능력치» 줄 = 능력치를 상자 오른쪽 끝에 맞춘다(원문 아이템 줄이 전부 이렇게 160px 딱 맞음). 아니면 그대로"""
    import re
    m = re.match(STAT_RE, line)
    if not m or not m.group(1).strip():
        return line
    name, stat = m.group(1).rstrip(' 　'), m.group(2).strip()
    w = encode(name, hm, fm, F)[1] + encode(stat, hm, fm, F)[1]
    fill = box - w
    if fill < 8:
        return name + ' ' + stat                  # 넘침 — 검사에서 걸린다
    return name + '　' * (fill // 16) + ' ' * (fill % 16 // 8) + stat


FULL_ALT = {',': '，、', '.': '．。'}      # 반각을 못 쓸 때 전각 대체


def encode(line, hm, fm, F, fixed=None):
    """번역 한 줄 → (토큰 목록, 폭 px, 반각 글리프 집합, 모르는 글자)
    fixed = 반각 목록을 늘릴 수 없는 글꼴(실행 파일 속 MES — 반각 55개에서 바꾸면 게임이 반각을 한 칸 앞 글리프로 그린다)
            이면 그 목록에 없는 반각 글자는 전각판으로"""
    import re
    toks = []; px = 0; halfs = set(); bad = []
    for m in re.finditer(r'\{([0-9A-Fa-f]+)\}|(.)', line):
        if m.group(1):
            toks.append(Cmd(b'\xff\xff' + bytes.fromhex(m.group(1)))); continue
        ch = m.group(2)
        if ch == '　' and '　' in fm:             # 전각 빈칸은 전각(16px) 그대로 — 원문이 가운데 맞춤·칸 맞춤에 쓴다
            toks.append(fm['　']); px += 16; continue
        if ch not in hm and ch not in fm and chr(ord(ch) + 0xFEE0) in fm and 0x21 <= ord(ch) < 0x7F:
            ch = chr(ord(ch) + 0xFEE0)         # 반각에 없는 영문 → 전각판(Ｃ·Ｙ …)
        if fixed is not None and ch in hm and hm[ch] not in fixed:
            alt = [c for c in FULL_ALT.get(ch, '') + chr(ord(ch) + 0xFEE0) if c in fm]
            if alt:
                toks.append(fm[alt[0]]); px += 16; continue
            bad.append(ch); continue
        if ch in hm:
            toks.append(hm[ch]); halfs.add(hm[ch]); px += 8
        elif '가' <= ch <= '힣':
            toks.append(hangul(F, ch)); px += 16
        elif ch in fm:
            toks.append(fm[ch]); px += 16
        else:
            bad.append(ch)
    return toks, px, halfs, bad


def apply(msgs, half, items, grp, key, hm, fm, F, errs, fixed=None):
    """items = {(메시지, 덩어리): (ID, 번역)} → msgs 제자리 교체, 새 반각 글리프는 half 에 덧붙임"""
    for (mi, bi), (tid, t) in sorted(items.items(), reverse=True):
        segs = msgs[mi]
        idx, box, maxl = grp(segs)[bi]
        lines = [align_stats(squeeze(x), box, hm, fm, F) for x in t.split(chr(92) + 'n')]   # TSV 줄바꿈 = 역슬래시+n
        if len(lines) > maxl:
            errs.append('%s %s-%d-%d 줄 %d > %d' % (tid, key, mi, bi, len(lines), maxl))
        new = []
        for ln in lines:
            if not ln:
                errs.append('%s 빈 줄(글 줄이 비면 명령으로 읽힌다 — 빈 줄은 «　»)' % tid)
            toks, px, halfs, bad = encode(ln, hm, fm, F, fixed)
            px = encode(ln.rstrip(' 　'), hm, fm, F, fixed)[1]      # 끝 빈칸 채움은 폭에서 뺀다(투명)
            if px > box and ln.rstrip(' 　')[-1:] in ('.', '。', '．'):   # 넘치면 줄 끝 마침표부터 뺀다(전프로젝트 규칙 1순위)
                ln = ln.rstrip(' 　')[:-1]
                toks, px, halfs, bad = encode(ln, hm, fm, F, fixed)
            if bad:
                errs.append('%s 모르는 글자 %s «%s»' % (tid, ''.join(bad), ln))
            if px > box:
                errs.append('%s «%s» %dpx > 상자 %dpx' % (tid, ln, px, box))
            for g in halfs:
                if g not in half:
                    half.append(g)
            new.append(('t', toks))
        msgs[mi] = segs[:idx[0]] + new + segs[idx[-1] + 1:]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
    import bdf
    F = bdf.Font(GALMURI)
    hm, fm = glyph_maps()
    tr = load_tr(); loc = load_ids()
    # 위치 → 번역
    want = collections.defaultdict(dict)
    for i, t in tr.items():
        for l in loc[i]:
            fn, mi, bi = l.rsplit('-', 2)
            want[fn][(int(mi), int(bi))] = (i, t)
    print('번역 %d덩어리 (위치 %d)' % (len(tr), sum(len(v) for v in want.values())))
    out = os.path.join(ROOT, 'work', 'kr', 'MES'); os.makedirs(out, exist_ok=True)
    errs = []; warns = []; res = []; files = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc', 'MES', 'S*.MES'))):
        fn = os.path.basename(f); d = open(f, 'rb').read(); key = fn.split('.')[0]
        if mes.header(d)[6] == 0:
            continue                                         # 빈 파일(S15_0C6)
        h, msgs, half = parse(d)
        # 왕복 검사(번역 없이 다시 짜도 같은가)
        nd0, _ = rebuild(d, msgs, half)
        assert parse(nd0)[1:] == (msgs, half), fn
        half = list(half)
        hs0 = set(half)
        apply(msgs, half, want.get(key, {}), lambda segs: groups(segs, hs0), key, hm, fm, F, errs)
        if errs:
            continue
        nd, nfull = rebuild(d, msgs, half)
        h2, msgs2, half2 = parse(nd)
        assert half2 == half and msgs2 == msgs and h2[:7] == h[:7] and h2[10:] == h[10:], fn
        if len(nd) > BUF:
            errs.append('%s 파일 %d B > 버퍼 %d' % (fn, len(nd), BUF))
        if nfull > FULL_TESTED:
            warns.append('%s 전각 %d > 실기 확인 %d' % (fn, nfull, FULL_TESTED))
        files[fn] = nd
        res.append((BUF - len(nd), fn, len(d), len(nd), nfull))
    # 실행 파일 속 MES(자리 고정 EXE_MES)
    x = bytearray(open(os.path.join(ROOT, 'work', 'disc', '0'), 'rb').read())
    d = bytes(x[EXE_MES[0]:EXE_MES[1]])
    h, msgs, half = parse(d); half = list(half)
    apply(msgs, half, want.get('EXE', {}), lambda segs: groups_exe(segs, None), 'EXE', hm, fm, F, errs,
          fixed=set(half))                  # ★실행 파일 글꼴은 반각 55개 고정(2026-09-27 실기: 58개로 늘리니 반각이 한 칸씩 밀림)
    if not errs:
        nd, nfull = rebuild(d, msgs, half)
        h2, msgs2, half2 = parse(nd)
        assert half2 == half and msgs2 == msgs and h2[:7] == h[:7] and h2[10:] == h[10:]
        if len(nd) > len(d):
            errs.append('실행 파일 MES %d B > 자리 %d B' % (len(nd), len(d)))
        else:
            x[EXE_MES[0]:EXE_MES[1]] = nd + bytes(len(d) - len(nd))
            files['0'] = bytes(x)
            print('실행 파일 MES %d → %d B (자리 %d, 여유 %d) · 전각 %d · 반각 %d'
                  % (len(d), len(nd), len(d), len(d) - len(nd), nfull, len(half)))
    if errs:
        print('⛔ 오류 %d건 — 쓰지 않음 (전체 목록 work/trans/errors.txt)' % len(errs))
        open(os.path.join(ROOT, 'work', 'trans', 'errors.txt'), 'w', encoding='utf-8').write('\n'.join(errs) + '\n')
        for e in errs[:60]:
            print('  ' + e)
        sys.exit(1)
    for w in warns:
        print('⚠️ ' + w)
    for fn, nd in files.items():
        open(os.path.join(out if fn != '0' else os.path.join(ROOT, 'work', 'kr'), fn), 'wb').write(nd)
    res.sort()
    print('파일 %d개 → work/kr/MES' % len(res))
    for r, fn, a, b, nf in res[:3]:
        print('  여유 적은 순: %s %d → %d B (여유 %d) 전각 %d' % (fn, a, b, r, nf))
    print('  전각 최대 %d' % max(x[4] for x in res))
    if '--write' in sys.argv:
        write_disc(files)
    return files


def write_disc(mesfiles):
    """트랙 01 = 대사 파일 전부(다시 짠 판) + 실행 파일(속 MES) + 타이틀 그림 3장 + 화 제목 13장 → work/out"""
    import disc, iso, title_art, ep_title
    files = {('/MES/' + fn if fn != '0' else '/0'): d for fn, d in mesfiles.items()}
    files.update({'/TITLE/' + fn: d for fn, d in title_art.build().items()})
    files.update({'/TITLE/' + fn + '.BIN': d for fn, d in ep_title.main().items()})
    import load_title                    # 불러오기 화면 제목(D.BIN)·화 제목(N01‥N13)
    files.update({'/TITLE/' + fn: d for fn, d in load_title.main().items()})
    import map_label                     # 지도 지명 상자 35장(LOCAL/*.LOC 11개)
    files.update({'/LOCAL/' + fn: d for fn, d in map_label.build().items()})
    out =os.path.join(ROOT, 'work', 'out'); os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, os.path.basename(disc.ROM))
    iso.patch(disc.ROM, dst, files, log=lambda *a: None)
    iso.verify(dst, files)
    print('→', dst, '(파일 %d개)' % len(files))


if __name__ == '__main__':
    main()
