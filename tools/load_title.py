# -*- coding: utf-8 -*-
r"""불러오기 화면 그림 → 한글 (2026-09-27)
  TITLE/D.BIN        «データの読み込み» 제목 136×16
  TITLE/N01‥N13.BIN  화 제목(1‥13화) 폭 128‥192 × 56, 3줄(윗선 0·19·38, 글자 높이 15)
  파일 = u32 팔레트 오프셋(0x10) · u16 폭 · u16 높이 · u32 데이터 오프셋(0x30) · u32 화소 수 + 팔레트 16색(0 검정=투명, 나머지 흰색) + 4bpp
  글자 = 갈무리14(비트맵, 1비트 흰색 1번 색) — 원본도 1비트
  화 제목 문구 = 화 제목 화면(ep_title.TITLES, 사용자 확정)과 같게
  폭: 글자가 넓으면 8의 배수로 늘림(최대 192 = 원본 N08) — VDP1 스프라이트 폭은 8의 배수
  python tools/load_title.py → work/loadtitle/*.png 미리보기, build() 는 {파일: 바이트}
"""
import os, struct, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import bdf, ep_title
SRC = os.path.join(ROOT, 'work', 'disc', 'TITLE')
OUT = os.path.join(ROOT, 'work', 'loadtitle')
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
HEAD = '데이터 불러오기'
MAXW = 192


def read(fn):
    b = open(os.path.join(SRC, fn + '.BIN'), 'rb').read()
    po, w, h, do, n = struct.unpack_from('>IHHII', b, 0)
    return b, w, h, do


def pack(b, w, h, rows):
    """rows = [[0/1…]…] → 같은 머리·팔레트, 폭·화소 수만 새로"""
    po, _, _, do, _ = struct.unpack_from('>IHHII', b, 0)
    px = bytearray()
    for r in rows:
        for x in range(0, w, 2):
            px.append(r[x] << 4 | r[x + 1])
    hb = bytearray(b[:do]); struct.pack_into('>IHHII', hb, 0, po, w, h, do, w * h)
    return bytes(hb) + bytes(px)


def draw(F, lines, tops, w0, h):
    ink = [F.draw(t)[0] for t in lines]
    wid = [max((x for x, y in p), default=-1) + 1 for p in ink]
    w = max(w0, -(-max(wid) // 8) * 8)
    assert w <= MAXW, (lines, max(wid))
    rows = [[0] * w for _ in range(h)]
    ys = [min(y for x, y in p) for p in ink if p]
    for p, ww, top in zip(ink, wid, tops):
        if not p:
            continue
        dx = (w - ww) // 2; dy = top - min(y for x, y in p)
        for x, y in p:
            rows[y + dy][x + dx] = 1
    return w, rows


def build():
    F = bdf.Font(GALMURI)
    res = {}
    b, w, h, do = read('D')
    ww, rows = draw(F, [HEAD], [1], w, h)
    res['D.BIN'] = (pack(b, ww, h, rows), rows)
    for k, (fn, t) in enumerate(ep_title.TITLES.items()):
        b, w, h, do = read('N%02d' % (k + 1))
        tops = [0, 19, 38] if h == 56 else [8, 27, 47]      # N10 만 높이 64·윗선 8·27·47(원본 측정)
        ww, rows = draw(F, list(t), tops, w, h)
        res['N%02d.BIN' % (k + 1)] = (pack(b, ww, h, rows), rows)
    return res


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True)
    res = build()
    ims = []
    for fn, (d, rows) in res.items():
        w, h = len(rows[0]), len(rows)
        im = Image.new('L', (w, h)); im.putdata([255 if v else 0 for r in rows for v in r])
        ims.append((fn, im)); print(fn, w, h, len(d))
    W = MAXW; H = sum(i.height + 4 for _, i in ims)
    sh = Image.new('L', (W, H), 60); y = 0
    for _, i in ims:
        sh.paste(i, ((W - i.width) // 2, y)); y += i.height + 4
    sh.resize((W * 2, H * 2)).save(os.path.join(OUT, 'sheet.png'))
    return {fn: d for fn, (d, _) in res.items()}


if __name__ == '__main__':
    main()
