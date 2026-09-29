# -*- coding: utf-8 -*-
r"""화 제목 화면 13장(TITLE/S_T*.BIN) → 한글 (2026-09-27)
  파일 = 머리 16B + 팔레트 256×u16(파일마다 다름) + 320×224 8bpp 무압축. 색 255 = 바탕 0x421.
  바탕 = 13장 다수결로 복원한 «씨앗만 있는 그림»(work/st_clean.pkl, 219색)
  글자 = 흰색 부드러운 가장자리(원본처럼), 세 줄 가운데 정렬
  팔레트 = 바탕 색 전부 + 남는 칸은 바탕(0x421)→흰색 회색 단계, 섞인 색은 가장 가까운 팔레트 색
  python tools/ep_title.py          → work/eptitle/*.png 미리보기
  python tools/ep_title.py --write  → work/kr/S_T*.BIN
"""
import os, pickle, struct, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'work', 'disc', 'TITLE')
OUT = os.path.join(ROOT, 'work', 'eptitle')
FONT = r'C:\claude\utils\font\logo\malgun.ttf'
SIZE = 30
W, H = 320, 224
BG = 0x421
LINE_TOP = (38, 91, 127)          # 원본 세 줄의 윗선(흰 글자 측정)
LINE_H = 27                        # 원본 글자 높이

def _titles():
    """화 제목 문구 = 실행 파일 번역 X0008‥X0020(사용자 번역 — 2026-09-27 «나타났다» 쪽으로 통일).
    «제N화　　앞줄\\n　　…　뒷줄» → (제N화, 앞줄, 뒷줄), 부호 뒤 띄어쓰기는 빌더 규칙대로 뺀다"""
    import build
    rows = {l.split('\t')[0]: l.split('\t')[5] for l in open(build.EXE_TSV, encoding='utf-8').read().split('\n')[1:] if l}
    files = ['S_T01', 'S_T02', 'S_T03', 'S_T04', 'S_T06', 'S_T07', 'S_T08', 'S_T11', 'S_T12', 'S_T13', 'S_T14', 'S_T15', 'S_T16']
    out = {}
    for k, fn in enumerate(files):
        a, b = rows['X%04d' % (8 + k)].split(chr(92) + 'n')
        head, first = a.split('　', 1)
        out[fn] = (head, build.squeeze(first.strip('　 ')), build.squeeze(b.strip('　 ')))
    return out


sys.path.insert(0, HERE)
TITLES = _titles()                  # 파일: (1줄, 2줄, 3줄)


def rgb(c):
    return ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)


def c15(r, g, b):
    return (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10


def alpha_mask():
    """글자 알파(0‥255) 한 장 — 한글 높이(«한» 기준)를 원본 글자 높이에 맞춘다"""
    f = ImageFont.truetype(FONT, SIZE)
    return f


def compose(clean, lines):
    f = alpha_mask()
    a = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(a)
    ref = f.getbbox('한')                         # 한글 윗선·아랫선 기준
    for top, text in zip(LINE_TOP, lines):
        g, sz = f, SIZE
        while g.getbbox(text)[2] - g.getbbox(text)[0] > W - 16:    # 넘치는 줄만 크기를 줄인다(좌우 8px 여백)
            sz -= 1; g = ImageFont.truetype(FONT, sz)
        l, t, r, b = g.getbbox(text); rf = g.getbbox('한')
        x = (W - (r - l)) // 2 - l
        y = top + (LINE_H - (rf[3] - rf[1])) // 2 - rf[1]
        dr.text((x, y), text, font=g, fill=255)
    A = list(a.getdata())
    out = []
    for i, c in enumerate(clean):
        k = A[i] / 255
        if not k:
            out.append(c); continue
        br, bg_, bb = rgb(c)
        out.append(c15(int(248 * k + br * (1 - k)), int(248 * k + bg_ * (1 - k)), int(248 * k + bb * (1 - k))))
    return out


def palette(clean):
    cols = sorted(set(clean) - {BG})
    n = 255 - len(cols)
    b0 = rgb(BG)
    ramp = [c15(*(int(b0[j] + (248 - b0[j]) * (s + 1) / n) for j in range(3))) for s in range(n)]
    pal = cols + [c for c in ramp if c not in cols]
    pal = (pal + [0x7fff] * 255)[:255] + [BG]
    return pal


def index(img, pal):
    P = [rgb(c) for c in pal]; exact = {c: i for i, c in enumerate(pal)}; cache = {}
    out = bytearray()
    for c in img:
        if c in exact:
            out.append(exact[c]); continue
        if c not in cache:
            r, g, b = rgb(c)
            cache[c] = min(range(256), key=lambda i: (P[i][0] - r) ** 2 + (P[i][1] - g) ** 2 + (P[i][2] - b) ** 2)
        out.append(cache[c])
    return bytes(out)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True)
    clean = pickle.load(open(os.path.join(ROOT, 'work', 'st_clean.pkl'), 'rb'))
    pal = palette(clean)
    assert pal[255] == BG and len(pal) == 256
    sheet = Image.new('RGB', (W * 2, H * 7), (0, 0, 0))
    res = {}
    for k, (fn, lines) in enumerate(TITLES.items()):
        src = open(os.path.join(SRC, fn + '.BIN'), 'rb').read()
        img = compose(clean, lines)
        px = index(img, pal)
        d = src[:16] + b''.join(struct.pack('>H', c) for c in pal) + px + src[0x210 + W * H:]
        assert len(d) == len(src)
        res[fn] = d
        im = Image.new('RGB', (W, H)); im.putdata([rgb(pal[i]) for i in px])
        im.save(os.path.join(OUT, fn + '.png'))
        sheet.paste(im, (W * (k % 2), H * (k // 2)))
        print(fn, ' / '.join(lines))
    sheet.save(os.path.join(OUT, 'sheet.png'))
    if '--write' in sys.argv:
        os.makedirs(os.path.join(ROOT, 'work', 'kr'), exist_ok=True)
        for fn, d in res.items():
            open(os.path.join(ROOT, 'work', 'kr', fn + '.BIN'), 'wb').write(d)
    return res


if __name__ == '__main__':
    main()
