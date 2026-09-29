# -*- coding: utf-8 -*-
r"""타이틀 화면 일본어 그림 3장 → 한글 (2026-09-27)
  TITLE/TITLE.BIN·T.BIN·T2.BIN 은 머리 = 적재 주소 표(0x200000+오프셋), 항목 = 16B 머리 + 15비트 RGB(압축 없음).
  세 파일이 같은 그림을 한 벌씩 갖는다 → 같은 새 그림을 세 곳에 제자리로 쓴다(크기 그대로).
    항목 2 320×120  «ブルーシード» 캡슐 → 캡슐 테두리는 두고 안쪽 글자만 «블루 시드»
    항목 3 320×32   저작권 1줄째만 한글(2줄째 © SEGA 1995 는 원본)
    항목 4 112×16   «〜奇稲田秘録伝〜» → «〜쿠시나다 비록전〜»
  그림 글자 규칙: 한 색 + 글자 둘레 1px 테두리.
  python tools/title_art.py          → work/title/*.png 미리보기
  python tools/title_art.py --write  → work/kr/TITLE.BIN·T.BIN·T2.BIN 도 만든다
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FONT = r'C:\claude\utils\font'
SRC = os.path.join(ROOT, 'work', 'disc', 'TITLE')
OUT = os.path.join(ROOT, 'work', 'title')

KANA_TEXT = '블루 시드'
KANA_PARTS = ['블', 2, '루', 5, '시', 2, '드']            # 원본 가타카나처럼 기울인 도트 글씨(작은 크기에선 윤곽 글꼴이 뭉개진다)
KANJI_TEXT = ['〜', 1, '쿠시나다', 4, '비록전', 1, '〜']   # 조각 사이 간격(px)을 직접 — 기본 자간으론 112px 를 넘는다
COPY_TEXT = ['©', 4, '타카다', 4, '유조', 1, '/', 1, '타케쇼보', 2, '·', 2, 'BS', 4, 'Project', 2, '·', 2,
             '테레비', 4, '토쿄', 2, '·', 2, 'NAS']   # 보통 굵기 갈무리11, 낱말 사이 4px·가운뎃점 둘레 2px(기본 자간이면 320px 를 넘는다)

MINT, TEAL = 0x6bb5, 0x2d89          # «ブルーシード» 글자색·테두리(원본에서 가장 많은 밝은/어두운 색)
RED, WHITE = 0x24ff, 0x7fff          # «奇稲田秘録伝» 글자색 · 테두리


def entries(b):
    offs = []
    for i in range(0, 256, 4):
        x = struct.unpack_from('>I', b, i)[0]
        if not 0x200000 <= x < 0x300000:
            break
        offs.append(x - 0x200000)
    out = []
    for o in offs[:-1]:
        _, _, w, h, _, d0, sz = struct.unpack_from('>HHHHHHI', b, o)
        assert sz == 2 * w * h
        out.append((o + d0, w, h))
    return out


def pix(b, e):
    a, w, h = e
    return [list(struct.unpack_from('>%dH' % w, b, a + 2 * w * y)) for y in range(h)]


def mask_text(text, font, size, shear=0.0, thr=128):
    """글자 모양(1비트) — 글자 칸 전체 크기로 그리고, 기울임은 아래를 기준으로 오른쪽으로"""
    f = ImageFont.truetype(font, size)
    l, t, r, btm = f.getbbox(text)
    W, H = r - l + int(abs(shear) * (btm - t)) + 4, btm - t + 2
    im = Image.new('L', (W, H), 0)
    ImageDraw.Draw(im).text((-l + 1, -t + 1), text, font=f, fill=255)
    if shear:
        im = im.transform(im.size, Image.AFFINE, (1, shear, -shear * H, 0, 1, 0), Image.BILINEAR)
    m = [[im.getpixel((x, y)) >= thr for x in range(W)] for y in range(H)]
    # 빈 가장자리 잘라내기
    ys = [y for y in range(H) if any(m[y])]; xs = [x for x in range(W) if any(m[y][x] for y in range(H))]
    return [row[xs[0]:xs[-1] + 1] for row in m[ys[0]:ys[-1] + 1]]


def join(parts, font, size):
    """[글, 간격, 글, …] 을 아래 맞춰 이어 붙인 글자 모양"""
    ms = [(mask_text(p, font, size, thr=128), p) if isinstance(p, str) else p for p in parts]
    f = ImageFont.truetype(font, size)
    top = min(f.getbbox(p)[1] for p in parts if isinstance(p, str))
    H = max(f.getbbox(p)[3] for p in parts if isinstance(p, str)) - top
    cols = []
    for p in ms:
        if isinstance(p, int):
            cols += [[False] * H for _ in range(p)]; continue
        m, t = p; y0 = f.getbbox(t)[1] - top
        for x in range(len(m[0])):
            cols.append([y0 <= y < y0 + len(m) and m[y - y0][x] for y in range(H)])
    rows = [[c[y] for c in cols] for y in range(H)]
    ys = [y for y in range(H) if any(rows[y])]
    return rows[ys[0]:ys[-1] + 1]


def italic(m, step):
    """도트 기울임 — 아래에서 step 줄마다 한 칸씩 오른쪽"""
    h, w = len(m), len(m[0]); k = (h - 1) // step
    return [[False] * ((h - 1 - y) // step) + row + [False] * (k - (h - 1 - y) // step) for y, row in enumerate(m)]


def stamp(P, m, x0, y0, fill, edge):
    """P 에 글자 m 을 (x0,y0) 에 찍고 둘레 1px(8방향) 테두리"""
    h, w = len(m), len(m[0])
    for y in range(-1, h + 1):
        for x in range(-1, w + 1):
            on = 0 <= y < h and 0 <= x < w and m[y][x]
            if on:
                P[y0 + y][x0 + x] = fill
            elif any(0 <= y + dy < h and 0 <= x + dx < w and m[y + dy][x + dx]
                     for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                P[y0 + y][x0 + x] = edge


def make_kana(P):
    # 캡슐 안쪽 글자 자리 비우기(원본 글자 = x 188‥281, y 66‥85; 괄호·밑줄은 그대로)
    for y in range(66, 86):
        for x in range(188, 282):
            P[y][x] = 0
    for y in range(79, 86):          # ブ 왼쪽 아래 획 끝(x 183‥187) — 괄호는 x 177 까지
        for x in range(180, 188):
            P[y][x] = 0
    m = join(KANA_PARTS, os.path.join(FONT, 'Galmuri-v2.40.3', 'Galmuri14.ttf'), 15)
    m = [[v or (x and row[x - 1]) for x, v in enumerate(row + [False])] for row in m]   # 가로 1칸 겹쳐 굵게
    m = italic(m, 3)
    h, w = len(m), len(m[0])
    assert w + 2 <= 281 - 188 and h + 2 <= 85 - 69, (w, h)
    x0 = 188 + (281 - 188 - w) // 2; y0 = 70 + (85 - 70 - h) // 2
    stamp(P, m, x0, y0, MINT, TEAL)
    return w, h


def make_kanji(P):
    for row in P:
        row[:] = [0] * len(row)
    m = join(KANJI_TEXT, os.path.join(FONT, 'Galmuri-v2.40.3', 'Galmuri11-Bold.ttf'), 12)
    h, w = len(m), len(m[0])
    assert w + 2 <= len(P[0]) and h + 2 <= len(P), (w, h)
    stamp(P, m, (len(P[0]) - w) // 2, (len(P) - h) // 2, RED, WHITE)
    return w, h


def make_copy(P):
    for y in range(0, 17):           # 1줄째 = 원본 4‥16행(15·16행에 한 점씩 있음), 2줄째는 17행부터
        P[y] = [0] * len(P[y])
    m = join(COPY_TEXT, os.path.join(FONT, 'Galmuri-v2.40.3', 'Galmuri11.ttf'), 12)
    h, w = len(m), len(m[0])
    x0 = (len(P[0]) - w) // 2        # 원본 1줄째 가운데(x 20‥299 → 159.5)에 맞춤
    assert x0 >= 0 and h <= 13, (w, h)
    for y in range(h):
        for x in range(w):
            if m[y][x]:
                P[3 + y][x0 + x] = WHITE     # 윗줄 3행부터(2줄째는 17행부터라 겹치지 않음)
    # 2줄째(© SEGA 1995, 원본 x 20 부터)를 1줄째 시작점에 맞춰 왼쪽으로
    d = 20 - x0
    for y in range(16, len(P)):
        P[y] = P[y][d:] + [0] * d
    return w, h


def to_png(P, path, scale=1):
    h, w = len(P), len(P[0])
    im = Image.new('RGB', (w, h), (0, 0, 0))
    for y in range(h):
        for x in range(w):
            c = P[y][x]
            if c:
                im.putpixel((x, y), ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3))
    if scale > 1:
        im = im.resize((w * scale, h * scale), Image.NEAREST)
    im.save(path)
    return im


def screen(b, E, repl):
    """VDP1 순서(스테이트에서 읽은 좌표)로 타이틀 화면 재현"""
    order = [(0, 0, 36), (1, 0, 68), (2, 0, 37), (4, 176, 124), (3, 0, 192)]
    im = Image.new('RGB', (320, 224), (0, 0, 0))
    for k, x0, y0 in order:
        P = repl.get(k) or pix(b, E[k])
        for y, row in enumerate(P):
            for x, c in enumerate(row):
                if c and 0 <= y0 + y < 224:
                    im.putpixel((x0 + x, y0 + y), ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3))
    return im


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True)
    b = open(os.path.join(SRC, 'TITLE.BIN'), 'rb').read()
    E = entries(b)
    new = {k: pix(b, E[k]) for k in (2, 3, 4)}
    print('블루 시드 %d×%d' % make_kana(new[2]))
    print('쿠시나다 비록전 %d×%d' % make_kanji(new[4]))
    print('저작권 %d×%d' % make_copy(new[3]))
    for k, n in ((2, 'kana'), (3, 'copy'), (4, 'kanji')):
        to_png(new[k], os.path.join(OUT, n + '.png'), 3)
    before, after = screen(b, E, {}), screen(b, E, new)
    cmp_ = Image.new('RGB', (640, 224)); cmp_.paste(before, (0, 0)); cmp_.paste(after, (320, 0))
    cmp_ = cmp_.resize((1280, 448), Image.NEAREST); cmp_.save(os.path.join(OUT, 'compare2.png'))
    print('→', os.path.join(OUT, 'compare2.png'))
    if '--write' not in sys.argv:
        return
    for fn, d in build(b, E, new).items():
        print('→ work/kr/' + fn, len(d))


def build(b=None, E=None, new=None):
    """세 파일(TITLE·T·T2.BIN)에 새 그림을 제자리로 → {파일이름: 바이트} (work/kr 에도 씀)"""
    if b is None:
        b = open(os.path.join(SRC, 'TITLE.BIN'), 'rb').read(); E = entries(b)
        new = {k: pix(b, E[k]) for k in (2, 3, 4)}
        make_kana(new[2]); make_kanji(new[4]); make_copy(new[3])
    os.makedirs(os.path.join(ROOT, 'work', 'kr'), exist_ok=True)
    res = {}
    for fn in ('TITLE.BIN', 'T.BIN', 'T2.BIN'):
        d = bytearray(open(os.path.join(SRC, fn), 'rb').read())
        e = entries(d)
        for k, P in new.items():
            a, w, h = e[k]
            assert (w, h) == E[k][1:] and bytes(d[a:a + 2 * w * h]) == b[E[k][0]:E[k][0] + 2 * w * h]
            d[a:a + 2 * w * h] = b''.join(struct.pack('>%dH' % w, *row) for row in P)
        open(os.path.join(ROOT, 'work', 'kr', fn), 'wb').write(d)
        res[fn] = bytes(d)
    return res


if __name__ == '__main__':
    main()
