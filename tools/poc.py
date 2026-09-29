# -*- coding: utf-8 -*-
r"""첫 PoC — S01_001.MES 메시지 34‥39(모미지 자기소개 독백)를 한글로 (2026-09-27)
  · 글꼴: 기존 반각 N·전각 글리프는 번호 그대로 두고, 한글 음절을 전각 끝에 덧붙인다(갈무리14 를 위로 4줄 — 원본 글자 0‥13행)
    새 전각 칸 k → 글자 번호 N+1+k, 0x80 이상이면 2바이트 (0x80 | v>>8, v & 0xFF), v = 번호 − 0x80
    부호·공백은 원문 글리프를 재사용(판독표로 찾음), 없으면 갈무리로 새로
  · 메시지: 글 줄(FF FE 로 나뉜 구간 중 명령 아닌 것)을 차례로 번역 줄로 바꿈 — 줄 수는 원문과 같게
  · 파일: 메시지 표 오프셋 다시 계산, 메시지 구역이 D 만큼 길어지면 글꼴 시작(hdr[8]) 등 그 뒤 머리 값 +D
    ⚠️hdr[23](0x2710d)은 메시지 8 안을 가리키는 값 — 34번 이후만 바꾸므로 그 앞은 한 바이트도 안 움직인다
  · 디스크: tools/iso.py (넘치면 파일 영역 끝으로, CDDA 항목 LBA 도 밀기)
  python tools/poc.py [--write]
"""
import hashlib, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import mes, ocrprep, bdf, disc

GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
FILE = 'S01_001.MES'
MSG0 = 34
LINES = {
    34: ['난 후지미야 모미지!', '신화의 고향,', '이즈모에서 태어난', '평범한 고교 1학년!'],
    35: ['……이었어야 했는데', '아라가미라는', '괴물들이 내 목숨을', '노려서 마치', '소설 속 주인공 같아.'],
    36: ['우리 조상님들은', '쿠시나다의 피를 이어', '대대로 아라가미들을', '“제물”이 되어', '봉인해 왔어.'],
    37: ['그런데 아라가미들이', '우리의 힘을', '막아낼 수 있게', '되어 버렸으니', '완전 큰일이야!'],
    38: ['야마타노오로치에', '거대한 까마귀,', '도깨비, 갓파, 노즈치', '요괴 대행진 같아서', '정신이 하나도 없어!'],
    39: ['한 번은 죽을 뻔도', '했지만……', '그래도 그럴 때면', '늘 도와주는', '동료들이 있어.'],
}
BOX_PX = 160
FULLW = {chr(c): chr(c + 0xFEE0) for c in range(0x21, 0x7F)}


def squeeze(s):
    """부호 뒤 공백 삭제(전프로젝트 규칙)"""
    import re
    return re.sub(r'([,.!?…、。！？，．」』”])[ 　]+', r'\1', s)


def hangul_glyph(F, ch):
    pts, _ = F.draw(ch, 0, -4)
    g = bytearray(32)
    for x, y in pts:
        if 0 <= x < 16 and 0 <= y < 16:
            g[2 * y + x // 8] |= 0x80 >> (x % 8)
    return bytes(g)


def code_bytes(c):
    if c < 0x80:
        return bytes([c])
    v = c - 0x80
    assert v < 0x8000
    return bytes([0x80 | v >> 8, v & 0xFF])


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    F = bdf.Font(GALMURI)
    M = {l.split('\t')[0]: l.rstrip('\n').split('\t')[1] for l in list(open(os.path.join(ROOT, 'work', 'glyphfinal.tsv'), encoding='utf-8'))[1:]}
    d = open(os.path.join(ROOT, 'work', 'disc', 'MES', FILE), 'rb').read()
    h = mes.header(d); t, fo = h[6], h[8]
    half, full = ocrprep.font(d); N = len(half)
    # 이 파일 글꼴의 «글자 → 번호»(판독표)
    # ★반각 번호 = 글리프 번호 + 1 (1‥N; 원문 「紅葉、[2][6]才」= 15才, 「Ver[40][2][50][1]」= Ver 1.0 — 실기에서 +1 없이 넣으니 한 칸 앞 글리프가 찍혔다)
    have = {}
    for k, g in enumerate(half):
        have.setdefault(M.get(hashlib.sha1(g).hexdigest()[:16]), k + 1)
    for k, g in enumerate(full):
        have.setdefault(M.get(hashlib.sha1(g).hexdigest()[:16]), N + 1 + k)
    # 판독표가 «?» 로 잘못 붙인 반각 둘을 모양으로 직접 찾는다: 빈 글리프 = 띄어쓰기, 아래쪽 2×2 점 = 마침표
    blank = next(k for k, g in enumerate(half) if not any(g)) + 1
    dot = next(k for k, g in enumerate(half) if g == bytes(12) + bytes([0x18, 0x18]) + bytes(2)) + 1
    have['.'] = have['．'] = dot
    newg = []; newidx = {}

    def code_of(ch):
        if ch in ('　', ' '):
            return blank
        c2 = FULLW.get(ch, ch)
        for cand in (ch, c2):
            if cand in have and '가' > cand:
                return have[cand]
        if ch not in newidx:
            newidx[ch] = N + 1 + len(full) + len(newg)
            newg.append(hangul_glyph(F, ch))
        return newidx[ch]

    msgs = mes.messages(d)
    n = len(msgs)
    newm = []
    for mi, (o, b) in enumerate(msgs):
        if mi not in LINES:
            newm.append(b); continue
        tl = [squeeze(x) for x in LINES[mi]]
        segs = ocrprep.segments(b)
        textsegs = [i for i, s in enumerate(segs) if s[:2] != b'\xff\xff' and s and s[:1] != b'\x00']
        assert len(textsegs) == len(tl), (mi, len(textsegs), len(tl))
        for i, line in zip(textsegs, tl):
            codes = [code_of(ch) for ch in line]
            # 상자 폭 = 160px(원문 줄 폭 분포 10칸 2,209줄 → 11칸 594줄 벼랑). 넘치면 줄 첫머리로 되감겨 겹친다(실기 확인)
            px = sum(8 if 1 <= c <= N else 16 for c in codes)
            assert px <= BOX_PX, '%d번 «%s» %dpx > %dpx' % (mi, line, px, BOX_PX)
            segs[i] = b''.join(code_bytes(c) for c in codes)
        nb = b'\xff\xfe'.join(segs)
        assert ocrprep.segments(nb) == segs
        newm.append(nb)
        print(mi, ' / '.join(tl))
    # 메시지 표 다시 짜기(조각 4바이트 정렬, 오프셋 = 표 시작 기준)
    # 34번 앞은 원본 바이트 그대로(메시지 사이 채움이 0 이 아닌 쓰레기라 다시 짜면 달라진다), 34번부터 4바이트 정렬로 이어 붙임
    o_first = struct.unpack_from('>I', d, t + 8 * MSG0)[0]
    area = bytearray(d[t + 8 * n:t + o_first])
    offs = [struct.unpack_from('>II', d, t + 8 * k) for k in range(MSG0)]
    for b in newm[MSG0:]:
        offs.append((8 * n + len(area), len(b)))
        area += b + bytes(-len(b) % 4)
    table = b''.join(struct.pack('>II', o, s) for o, s in offs)
    newarea = table + bytes(area)
    newarea += bytes(-(t + len(newarea)) % 4)
    D = (t + len(newarea)) - fo
    # 머리 갱신: 글꼴 시작 이상인 값 +D
    hb = bytearray(d[:4 * (len(h) + 1)])
    for i, v in enumerate(h):
        if v >= fo:
            struct.pack_into('>I', hb, 4 * i, v + D)
    # ★원본 전각 뒤에 4바이트 맞춤 채움(S01_001 = 2B)이 붙어 있다 → 새 글리프는 그 채움 «앞»에 넣고 채움은 다시 뒤로
    #  (채움 뒤에 붙이면 새 글리프가 전부 2B = 한 줄 밀리고 앞 글리프 끝줄이 맨 위에 점으로 보인다 — 실기 «이» 왼쪽 위 점)
    fend = fo + 14 + N * 16 + len(full) * 32
    font = d[fo:fend] + b''.join(newg)
    font += bytes(-(fo + D + len(font)) % 4)
    nd = bytes(hb) + d[len(hb):t] + newarea + font
    # 되읽기 검사
    h2 = mes.header(nd); assert h2[8] == fo + D
    half2, full2 = ocrprep.font(nd)
    assert half2 == half and full2[:len(full)] == full and full2[len(full):len(full) + len(newg)] == newg
    m2 = mes.messages(nd); assert len(m2) == n and all(x[1] == y for x, y in zip(m2, newm))
    print('한글 새 글리프 %d · 전각 %d → %d · 파일 %d → %d B (버퍼 0x30000 여유 %d)'
          % (len(newg), len(full), len(full2), len(d), len(nd), 0x30000 - len(nd)))
    assert len(nd) <= 0x30000
    os.makedirs(os.path.join(ROOT, 'work', 'kr'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'kr', FILE), 'wb').write(nd)
    if '--write' not in sys.argv:
        print('예행 끝 — 쓰려면 --write'); return
    import iso
    out = os.path.join(ROOT, 'work', 'out'); os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, os.path.basename(disc.ROM))
    import title_art                     # 타이틀 그림 3장(사용자 확정 2026-09-27)도 같이
    files = {'/MES/' + FILE: nd}
    files.update({'/TITLE/' + fn: d for fn, d in title_art.build().items()})
    import ep_title                      # 화 제목 화면 13장(사용자 확인 2026-09-27)
    files.update({'/TITLE/' + fn + '.BIN': d for fn, d in ep_title.main().items()})
    iso.patch(disc.ROM, dst, files)
    iso.verify(dst, files)
    print('→', dst)


if __name__ == '__main__':
    main()
