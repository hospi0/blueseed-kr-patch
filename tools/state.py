import sys, struct
def wram(path):
    s = open(path, 'rb').read()
    def get(tag):
        i = s.find(tag); n = struct.unpack_from('<I', s, i + len(tag))[0]
        b = s[i + len(tag) + 4:i + len(tag) + 4 + n]
        a = bytearray(b); a[0::2], a[1::2] = b[1::2], b[0::2]
        return bytes(a)
    return get(b'WorkRAML'), get(b'WorkRAMH'), s
