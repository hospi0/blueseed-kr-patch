# -*- coding: utf-8 -*-
r"""트랙 01(MODE1/2352) 파일 바꿔 넣기 — 걸리버 보이 tools/iso.py 를 디렉터리 있는 디스크용으로 (2026-09-27)
  파일 이름은 경로(/MES/S01_001.MES). 디렉터리 기록 갱신은 그 파일이 든 디렉터리 섹터에서.
  원본 배치: LBA 30 부터 파일 466개가 빈틈없이 LBA 순으로 이어지고(디렉터리 순서와는 다름), 마지막 파일 뒤 150섹터 = 뒷간격(0 데이터).
  게임은 ISO 디렉터리(LBA 20‥29)로 파일을 찾는다(실행 파일 이름 표 = 파일 «번호», LBA 아님).
  규칙:
    · 새 파일이 원래 섹터 수 안에 들어가면 제자리(남는 곳은 0)
    · 넘치면 «파일 영역 맨 끝»(마지막 파일 뒤)으로 옮긴다 — 다른 파일은 한 섹터도 안 움직인다
      (옛 자리는 원래 내용 그대로 둔다 = 아무도 안 읽음)
    · 디렉터리 기록의 LBA·크기(양 엔디안), PVD 볼륨 크기, 뒷간격 150섹터(헤더 MSF 새로)
    · 쓴 섹터는 헤더(동기·MSF·모드 1) + EDC/ECC 재계산(tools cdmode1)
  from iso import patch; patch(src_bin, dst_bin, {'C03.BIN': bytes, …}, force_move=())
"""
import os, shutil, struct, sys
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import cdmode1

SYNC = b'\x00' + b'\xff' * 10 + b'\x00'


def bcd(n):
    return (n // 10) << 4 | n % 10


def header(lba):
    f = lba + 150
    return SYNC + bytes([bcd(f // 4500), bcd(f // 75 % 60), bcd(f % 75), 1])


def sector(lba, data):
    s = bytearray(2352)
    s[0:16] = header(lba)
    s[16:16 + len(data)] = data
    return bytes(cdmode1.fix(s))


def read_user(fh, lba, n=1):
    out = bytearray()
    for i in range(n):
        fh.seek((lba + i) * 2352 + 16); out += fh.read(2048)
    return bytes(out)


def entries(fh):
    """[(경로, LBA, 크기, 디렉터리 LBA, 디렉터리 안 오프셋)] — 하위 디렉터리까지"""
    pvd = read_user(fh, 16)
    root = pvd[156:190]
    out = []

    def walk(dl, ds, base):
        d = read_user(fh, dl, (ds + 2047) // 2048); i = 0
        while i < len(d):
            n = d[i]
            if n == 0:
                i = (i // 2048 + 1) * 2048; continue
            rec = d[i:i + n]; nl = rec[32]
            name = rec[33:33 + nl].decode('latin1').split(';')[0]
            l, s = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
            if name not in ('\x00', '\x01'):
                if rec[25] & 2:
                    walk(l, s, base + '/' + name)
                else:
                    out.append((base + '/' + name, l, s, dl, i))
            i += n
    walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '')
    return out


def patch(src, dst, files, force_move=(), log=print):
    shutil.copyfile(src, dst)
    total = os.path.getsize(src) // 2352
    with open(dst, 'r+b') as fh:
        ents = entries(fh)
        E = {nm: (l, s, dl, off) for nm, l, s, dl, off in ents}
        # ★CDDA 디렉터리 항목은 오디오 트랙 LBA 를 가리킨다 → 트랙 01 안의 파일만으로 끝을 잰다
        end = max(l + (s + 2047) // 2048 for _, l, s, _, _ in ents if l + (s + 2047) // 2048 <= total)
        post = total - end
        cur = end; moved = []
        dirs = {}
        for nm, data in files.items():
            l, s, dl, off = E[nm]
            have = (s + 2047) // 2048
            need = max(1, (len(data) + 2047) // 2048)
            if need <= have and nm not in force_move:
                lba = l; n = have
            else:
                lba = cur; n = need; cur += need; moved.append(nm)
            pad = data + bytes(n * 2048 - len(data))
            for k in range(n):
                fh.seek((lba + k) * 2352); fh.write(sector(lba + k, pad[k * 2048:(k + 1) * 2048]))
            sec_lba = dl + off // 2048; o = off % 2048
            if sec_lba not in dirs:
                dirs[sec_lba] = bytearray(read_user(fh, sec_lba))
            sec = dirs[sec_lba]
            struct.pack_into('<I', sec, o + 2, lba); struct.pack_into('>I', sec, o + 6, lba)
            struct.pack_into('<I', sec, o + 10, len(data)); struct.pack_into('>I', sec, o + 14, len(data))
            log('  %-20s %8d → %8d B  LBA %6d%s' % (nm, s, len(data), lba, ' (끝으로 옮김, 옛 LBA %d)' % l if lba != l else ''))
        grow = cur - end
        if grow:                                       # 트랙 01 이 길어지면 뒤 오디오 트랙 LBA 도 밀린다 → CDDA 항목 갱신
            for nm, l, s, dl, off in ents:
                if l + (s + 2047) // 2048 > total:
                    sl = dl + off // 2048; o = off % 2048
                    if sl not in dirs:
                        dirs[sl] = bytearray(read_user(fh, sl))
                    struct.pack_into('<I', dirs[sl], o + 2, l + grow); struct.pack_into('>I', dirs[sl], o + 6, l + grow)
        for sl, sec in dirs.items():
            fh.seek(sl * 2352); fh.write(sector(sl, bytes(sec)))
        if grow:
            pvd = bytearray(read_user(fh, 16))
            vs = struct.unpack_from('<I', pvd, 80)[0] + grow
            struct.pack_into('<I', pvd, 80, vs); struct.pack_into('>I', pvd, 84, vs)
            fh.seek(16 * 2352); fh.write(sector(16, pvd))
            for k in range(post):
                fh.seek((cur + k) * 2352); fh.write(sector(cur + k, bytes(2048)))
            fh.truncate((cur + post) * 2352)
        log('  옮긴 파일 %d개 %s · 트랙 01 %d → %d 섹터' % (len(moved), moved, total, cur + post))
    return moved


def verify(dst, files):
    with open(dst, 'rb') as fh:
        for nm, l, s, _, _ in entries(fh):
            if nm in files:
                got = read_user(fh, l, (s + 2047) // 2048)[:s]
                assert got == files[nm], ('되읽기 불일치', nm)
                for k in (0, (s - 1) // 2048):
                    fh.seek((l + k) * 2352); sec = fh.read(2352)
                    assert bytes(cdmode1.fix(bytearray(sec))) == sec, ('ECC', nm, k)
    return True
