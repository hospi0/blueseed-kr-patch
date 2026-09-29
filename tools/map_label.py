# -*- coding: utf-8 -*-
r"""지도 화면 지명 상자 35장 → 한글 (2026-09-29)
  LOCAL/*.LOC 11개: 머리 = (오프셋, 크기) u32 쌍 표. 항목 0 = 배경(320×224 8bpp, ⛔안 건드림),
  항목 2‥36 = 지명 상자, 항목 37 = 손가락 커서. 지명 상자 35장은 11개 파일에 똑같이 들어 있다.
  상자 항목 = 16B 머리(0x10, 폭, 높이, 픽셀 오프셋 0x30, 픽셀 크기) + 16색 팔레트 + 4bpp 픽셀(압축 없음).
  상자 모양: 바깥 테두리 2 · 안 테두리 1(흰) · 3(어둠) · 안쪽 = 줄마다 한 색 세로 그라데이션(9→4),
  글자 = 1(흰) + 둘레 1px 테두리 3.  → 상자 테두리는 두고 안쪽만 다시 그린다(크기 그대로 제자리).
  python tools/map_label.py          → work/maplabel/*.png 미리보기 + my files/그래픽/지명상자_비교.png
  build()                            → {LOC 파일이름: 바이트} (build.py 의 write_disc 가 부름)
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
GAL = r'C:\claude\utils\font\Galmuri-v2.40.3'
SRC = os.path.join(ROOT, 'work', 'disc', 'LOCAL')
OUT = os.path.join(ROOT, 'work', 'maplabel')
LOCS = ['FUJISAN', 'HOKKAID', 'KUMAMO1', 'KUMAMO2', 'NAGATAC', 'NIKKO', 'SHIBUY1', 'SHIBUY2',
        'SHINJUK', 'SHIZUOK', 'UENO']

# 항목 번호 → (원문, 한글). 이름은 대사 번역과 같게(거센소리·용어 결정 따름).
NAMES = {
    2: ('藁科茶畑', '와라시나 차밭'),
    3: ('静岡駅', '시즈오카역'),
    4: ('登呂遺跡', '토로 유적'),
    5: ('華厳の滝', '케곤 폭포'),
    6: ('日光東照宮', '닛코 토쇼구'),
    7: ('日光駅', '닛코역'),
    8: ('上野動物園', '우에노 동물원'),
    9: ('上野駅', '우에노역'),
    10: ('アメ横(上野側)', '아메요코(우에노 쪽)'),
    11: ('アメ横(御徒町側)', '아메요코(오카치마치 쪽)'),
    12: ('阿蘇火口', '아소 화구'),
    13: ('草千里', '쿠사센리'),
    14: ('上通り', '카미토리'),
    15: ('下通り', '시모토리'),
    16: ('熊本駅', '쿠마모토역'),
    17: ('層雲峡', '소운쿄'),
    18: ('大雪山', '다이세츠산'),
    19: ('札幌駅', '삿포로역'),
    20: ('ハチ公前', '하치코 앞'),
    21: ('渋谷駅', '시부야역'),
    22: ('スペイン坂下', '스페인 언덕 아래'),
    23: ('スペイン坂上', '스페인 언덕 위'),
    24: ('赤坂プリンスホテル', '아카사카 프린스 호텔'),
    25: ('永田町駅', '나가타초역'),
    26: ('国会議事堂', '국회의사당'),
    27: ('銀座(←有楽町)', '긴자(←유라쿠초)'),
    28: ('銀座(→数寄屋橋)', '긴자(→스키야바시)'),
    29: ('青木ヶ原樹海', '아오키가하라 수해'),
    30: ('富士山山頂', '후지산 정상'),
    31: ('御殿場駅', '고텐바역'),
    32: ('富士演習場', '후지 연습장'),
    33: ('富士五湖', '후지 오호'),
    34: ('新宿駅', '신주쿠역'),
    35: ('歌舞伎町', '가부키초'),
    36: ('都庁', '도청'),
}
# 글꼴: 보통 갈무리11 → 안 들어가면 콘덴스드(좁은 글꼴). 둘 다 12px 로 찍으면 한글 높이 = 원본 한자 높이.
# 칸이 남으면 글자 사이 1px(테두리끼리 붙지 않게) → 안 되면 0px → 콘덴스드 1px → 0px.
FONTS = [('Galmuri11.ttf', 12, 1), ('Galmuri11.ttf', 12, 0),
         ('Galmuri11-Condensed.ttf', 12, 1), ('Galmuri11-Condensed.ttf', 12, 0)]
SAME = {23: 2}   # 짝 맞춤: «스페인 언덕 위» 는 «…아래»(콘덴스드)와 같은 글꼴부터
TEXT, EDGE = 1, 3


def table(d):
    n = struct.unpack_from('>I', d, 0)[0] // 8
    return [struct.unpack_from('>II', d, i * 8) for i in range(n)]


def load(e):
    kind, w, h, po, sz = struct.unpack_from('>IHHII', e, 0)
    assert kind == 0x10 and po == 0x30 and sz == w * h // 2, (kind, w, h, po, sz)
    px = e[po:po + sz]
    return w, h, [[(px[(y * w + x) >> 1] >> 4) if x % 2 == 0 else px[(y * w + x) >> 1] & 15
                   for x in range(w)] for y in range(h)]


def store(e, g):
    w, h = len(g[0]), len(g)
    out = bytearray(e)
    for y in range(h):
        for x in range(0, w, 2):
            out[0x30 + (y * w + x) // 2] = (g[y][x] << 4) | g[y][x + 1]
    return bytes(out)


def box(g):
    """바깥 테두리(2) 가로 범위 = 0행의 2 → (x0, x1). 안쪽 글자 칸 = x0+3‥x1-3, 3‥16행."""
    xs = [x for x, v in enumerate(g[0]) if v == 2]
    x0, x1 = xs[0] - 1, xs[-1] + 1
    assert g[1][x0] == 2 and g[1][x1] == 2 and g[19][x0 + 1] == 2, (x0, x1)
    return x0, x1


def grad(g, x0, x1):
    """줄마다 그라데이션 색 = 그 줄 안쪽에서 1·3 이 아닌 값 중 가장 많은 것"""
    col = {}
    for y in range(3, 17):
        cnt = {}
        for v in g[y][x0 + 3:x1 - 2]:
            if v not in (1, 3):
                cnt[v] = cnt.get(v, 0) + 1
        col[y] = max(cnt, key=cnt.get)
    return col


def mask(text, font, size, sp):
    f = ImageFont.truetype(os.path.join(GAL, font), size)
    im = Image.new('L', (len(text) * (size + sp) + 8, 24), 0)
    dr, x = ImageDraw.Draw(im), 2
    for ch in text:
        dr.text((x, 0), ch, font=f, fill=255)
        x += round(f.getlength(ch)) + (sp if ch != ' ' else 0)
    w, h = im.size
    rows = [[im.getpixel((x, y)) >= 128 for x in range(w)] for y in range(h)]
    ys = [y for y in range(h) if any(rows[y])]; xs = [x for x in range(w) if any(r[x] for r in rows)]
    return [r[xs[0]:xs[-1] + 1] for r in rows[ys[0]:ys[-1] + 1]]


def draw(g, text, first=0):
    x0, x1 = box(g)
    col = grad(g, x0, x1)
    ax0, ax1, ay0, ay1 = x0 + 3, x1 - 3, 4, 15          # 글자(테두리 뺀) 들어갈 칸
    aw, ah = ax1 - ax0 + 1, ay1 - ay0 + 1
    for font, size, sp in FONTS[first:]:
        m = mask(text, font, size, sp)
        if len(m[0]) <= aw and len(m) <= ah:
            break
    else:
        raise SystemExit('안 들어감: %s (%dpx > %dpx)' % (text, len(m[0]), aw))
    for y in range(3, 17):                               # 안쪽을 그라데이션으로 비움
        for x in range(x0 + 3, x1 - 2):
            g[y][x] = col[y]
    mh, mw = len(m), len(m[0])
    ox = ax0 + (aw - mw) // 2; oy = ay0 + (ah - mh + 1) // 2
    on = {(oy + y, ox + x) for y in range(mh) for x in range(mw) if m[y][x]}
    for (y, x) in on:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (y + dy, x + dx) not in on and 3 <= y + dy <= 16 and x0 + 2 <= x + dx <= x1 - 2:
                    g[y + dy][x + dx] = EDGE
    for (y, x) in on:
        g[y][x] = TEXT
    return '%s+%d' % (font, sp), mw, aw


def rgb(e):
    pal = struct.unpack_from('>16H', e, 16)
    return [((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3) for c in pal]


def img(g, pal):
    im = Image.new('RGB', (len(g[0]), len(g)))
    im.putdata([pal[v] if v else (255, 0, 255) for r in g for v in r])
    return im


def make():
    d = open(os.path.join(SRC, 'SHIZUOK.LOC'), 'rb').read()
    T = table(d)
    new, rep = {}, []
    for k, (jp, kr) in NAMES.items():
        o, s = T[k]
        e = d[o:o + s]
        w, h, g = load(e)
        font, mw, aw = draw(g, kr, SAME.get(k, 0))
        new[k] = (e, store(e, g))
        rep.append((k, jp, kr, font, mw, aw))
    return d, T, new, rep


def build():
    """11개 LOC 에 같은 새 상자를 제자리로 → {파일이름: 바이트} (work/kr/LOCAL 에도 씀)"""
    _, _, new, _ = make()
    os.makedirs(os.path.join(ROOT, 'work', 'kr', 'LOCAL'), exist_ok=True)
    res = {}
    for n in LOCS:
        fn = n + '.LOC'
        d = bytearray(open(os.path.join(SRC, fn), 'rb').read())
        T = table(d)
        for k, (old, nb) in new.items():
            o, s = T[k]
            assert bytes(d[o:o + s]) == old, (fn, k)
            d[o:o + s] = nb
        open(os.path.join(ROOT, 'work', 'kr', 'LOCAL', fn), 'wb').write(d)
        res[fn] = bytes(d)
    return res


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True)
    d, T, new, rep = make()
    for k, jp, kr, font, mw, aw in rep:
        print('%2d %-12s → %-16s %s %d/%dpx' % (k, jp, kr, font.split('.')[0], mw, aw))
    rows = []
    for k in NAMES:
        old, nb = new[k]
        pal = rgb(old)
        rows.append((img(load(old)[2], pal), img(load(nb)[2], pal)))
    W = max(a.width for a, _ in rows)
    sheet = Image.new('RGB', (W * 2 + 8, 24 * len(rows)), (255, 0, 255))
    for i, (a, b) in enumerate(rows):
        sheet.paste(a, (0, 24 * i)); sheet.paste(b, (W + 8, 24 * i))
    sheet = sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST)
    p1 = os.path.join(OUT, 'compare.png'); sheet.save(p1)
    gdir = os.path.join(ROOT, 'my files', '그래픽'); os.makedirs(gdir, exist_ok=True)
    sheet.save(os.path.join(gdir, '지명상자_비교.png'))
    print('→', p1)
    if '--write' in sys.argv:
        for fn, b in build().items():
            print('→ work/kr/LOCAL/' + fn, len(b))


if __name__ == '__main__':
    main()
