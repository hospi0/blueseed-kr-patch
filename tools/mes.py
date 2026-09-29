# -*- coding: utf-8 -*-
r"""블루 시드 대사 파일 MES/S*.MES (2026-09-27 초기 조사)
  머리 = u32 BE 오프셋 목록 … FFFFFFFF   → 7번째 칸(hdr[6]) = 메시지 표
  메시지 표 = [u32 오프셋][u32 크기] × N (오프셋은 «표 시작» 기준, 첫 오프셋/8 = N, 조각은 2바이트 정렬)
  본문 = FF xx 제어 · 80..FF xx 2바이트 글자((c&0x7F)<<8|b)+0x80 · 00..7F 1바이트 글자
  글꼴 = 파일 끝, 그 장면 글자만 빈도순 16×16 1bpp(32 B) — 앞에 8×16 반각 구역(머리 8·16·16 …)
  python tools/mes.py stats
"""
import os, struct, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MES = os.path.join(ROOT, 'work', 'disc', 'MES')


def header(d):
    h = []; i = 0
    while True:
        v = struct.unpack_from('>I', d, i)[0]
        if v == 0xFFFFFFFF:
            return h
        h.append(v); i += 4


def messages(d):
    """[(표 시작 기준 오프셋, 바이트)]"""
    t = header(d)[6]
    n = struct.unpack_from('>I', d, t)[0] // 8
    out = []
    for k in range(n):
        o, s = struct.unpack_from('>II', d, t + 8 * k)
        out.append((o, d[t + o:t + o + s]))
    return out


def codes(b):
    """[('c', 글자번호) | ('f', 제어 xx)]"""
    out = []; i = 0
    while i < len(b):
        c = b[i]
        if c == 0xFF:
            out.append(('f', b[i + 1])); i += 2
        elif c >= 0x80:
            out.append(('c', ((c & 0x7F) << 8 | b[i + 1]) + 0x80)); i += 2
        else:
            out.append(('c', c)); i += 1
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:] == ['stats']:
        nm = ch = 0; top = []
        for f in sorted(glob.glob(os.path.join(MES, 'S*.MES'))):
            d = open(f, 'rb').read(); m = messages(d); mc = 0
            for o, b in m:
                for k, v in codes(b):
                    if k == 'c':
                        ch += 1; mc = max(mc, v)
            nm += len(m); top.append((mc, os.path.basename(f)))
        print('메시지', nm, '글자(제어 제외, 1·2번 포함)', ch, '파일당 최대 글자 번호', sorted(top)[-3:])
