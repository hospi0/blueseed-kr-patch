# -*- coding: utf-8 -*-
r"""Windows OCR(일본어)용 대사 줄 그림 (2026-09-27, 사립 저스티스 학원 tools/ocrprep.py 방식)
  MES 메시지 = «FF FE» 로 나뉜 구간: «FF FF xx …» 명령 / 그 밖 = 글 줄
  글자 번호: 1바이트 00‥7F, 2바이트 ((c&0x7F)<<8|b)+0x80 · 반각 수 N(파일마다 다름! S01_001 50 · S01_006 47):
    ★번호 1‥N = 반각 칸(번호 − 1) · > N = 전각 칸(번호 − N − 1) · 0 은 글 줄에 안 나옴   ⛔0x33 고정으로 풀면 파일 절반이 통째로 밀린다
    (2026-09-27 정정: 예전엔 «< N 반각, N 공백»으로 풀었는데 실기에서 한 칸씩 밀렸다 — 「紅葉、[2][6]才」 = 15才. 띄어쓰기는 빈 반각 글리프)
  반각(16B)·전각(32B) 그림 모두 판독 대상(반각 글자도 파일마다 다름)
  전각 그림(32B)을 전역 키로 삼아, 키마다 최대 --per 번 나오도록 줄을 골라 3배(칸 50px)로 흰 바탕에 검게 그린다.
  → work/ocr/img_NNNN.png + layout.json (줄마다 y·칸 = 그림 키 번호 또는 None, known = 반각 글자)
  python tools/ocrprep.py [--per 6]
"""
import argparse, glob, json, os, struct, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import mes

SC, PITCH, X0, Y0 = 3, 50, 30, 30
LINEH = 16 * SC + 36


def font(d):
    fo = mes.header(d)[8]
    N = struct.unpack_from('>H', d, fo + 12)[0]
    half = [d[fo + 14 + k * 16:fo + 14 + k * 16 + 16] for k in range(N)]
    F = fo + 14 + N * 16
    full = [d[F + k * 32:F + k * 32 + 32] for k in range((len(d) - F) // 32)]
    return half, full


def glyph(c, half, full):
    """글자 번호 → 그림 바이트(반각 16B / 전각 32B) · 범위 밖이면 None"""
    N = len(half)
    if 1 <= c <= N:
        return half[c - 1]
    if c == 0:
        return None
    k = c - N - 1
    return full[k] if k < len(full) else None


def segments(b):
    out = []; cur = bytearray(); i = 0
    while i < len(b):
        if b[i] == 0xFF and i + 1 < len(b) and b[i + 1] == 0xFE:
            out.append(bytes(cur)); cur = bytearray(); i += 2
        else:
            cur.append(b[i]); i += 1
    if cur:
        out.append(bytes(cur))
    return out


def chars(seg):
    out = []; i = 0
    while i < len(seg):
        c = seg[i]
        if c == 0:                                     # 글자 경계의 00 = 메시지 끝
            break
        if c >= 0x80:
            out.append(((c & 0x7F) << 8 | seg[i + 1]) + 0x80); i += 2
        else:
            out.append(c); i += 1
    return out


def text_lines(d):
    """[(메시지 번호, 줄 번호, [글자 번호…])]"""
    out = []
    for mi, (o, b) in enumerate(mes.messages(d)):
        li = 0
        for seg in segments(b):
            if seg[:2] == b'\xff\xff' or not seg or seg == b'\x00':
                continue
            cs = chars(seg)
            if cs:
                out.append((mi, li, cs)); li += 1
    return out


def draw_glyph(im, x, y, bits, w):
    for r in range(16):
        v = bits[r * (w // 8)] if w == 8 else (bits[2 * r] << 8 | bits[2 * r + 1])
        for c in range(w):
            if v >> (w - 1 - c) & 1:
                for dy in range(SC):
                    for dx in range(SC):
                        im.putpixel((x + c * SC + dx, y + r * SC + dy), 0)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(); ap.add_argument('--per', type=int, default=6); ap.add_argument('--out', default=os.path.join(ROOT, 'work', 'ocr'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    keys = {}; keylist = []; count = {}; chosen = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc', 'MES', 'S*.MES'))):
        d = open(f, 'rb').read(); half, full = font(d)
        for mi, li, cs in text_lines(d):
            cells = []; known = []; need = False
            for c in cs:
                g = glyph(c, half, full)
                if g:
                    if g not in keys:
                        keys[g] = len(keylist); keylist.append(g)
                    k = keys[g]; cells.append(('F', k)); known.append(None)
                    if count.get(k, 0) < a.per:
                        need = True
                else:
                    cells.append(None); known.append(' ')
            if need:
                for cl in cells:
                    if cl and cl[0] == 'F':
                        count[cl[1]] = count.get(cl[1], 0) + 1
                chosen.append((os.path.basename(f), mi, li, cells, known))
    per_img = (9000 - 2 * Y0) // LINEH
    images = []
    for n in range(0, len(chosen), per_img):
        part = chosen[n:n + per_img]
        W = X0 * 2 + PITCH * max(len(c[3]) for c in part)
        im = Image.new('L', (W, Y0 * 2 + LINEH * len(part)), 255)
        lines = []
        for r, (fn, mi, li, cells, known) in enumerate(part):
            y = Y0 + r * LINEH
            for j, cl in enumerate(cells):
                if cl is None:
                    continue
                g = keylist[cl[1]]
                if len(g) == 32:
                    draw_glyph(im, X0 + j * PITCH, y, g, 16)
                else:
                    draw_glyph(im, X0 + j * PITCH + 12, y, g, 8)
            lines.append({'y': y, 'src': '%s:%d:%d' % (fn, mi, li),
                          'cells': [cl[1] if cl and cl[0] == 'F' else None for cl in cells], 'known': known})
        name = 'img_%04d.png' % (len(images) + 1)
        im.save(os.path.join(a.out, name)); images.append({'img': name, 'lines': lines})
    json.dump({'pitch': PITCH, 'x0': X0, 'lineh': LINEH, 'glyph': 16 * SC, 'images': images},
              open(os.path.join(a.out, 'layout.json'), 'w', encoding='utf-8'))
    import pickle
    pickle.dump(keylist, open(os.path.join(ROOT, 'work', 'glyphkeys.pkl'), 'wb'))
    print('글리프 %d · 고른 줄 %d · 그림 %d장 → %s' % (len(keylist), len(chosen), len(images), a.out))


if __name__ == '__main__':
    main()
