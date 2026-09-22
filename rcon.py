"""Minegram — async RCON + server-list-ping (чистый stdlib)."""
import asyncio
import json
import secrets
import socket
import struct
import time


def _recvall(s, n):
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed mid-packet")
        buf += chunk
    return buf


def _recv_varint(s):
    n = shift = 0
    while shift < 35:  # ponytail: max 5 байт varint, дальше — мусор/атака
        d = _recvall(s, 1)[0]
        n |= (d & 0x7F) << shift
        shift += 7
        if not d & 0x80:
            return n, 0
    raise ValueError("varint too long")


def _parse_varint(b, i):
    n = shift = 0
    while shift < 35:
        if i >= len(b):
            raise ConnectionError("truncated packet")
        d = b[i]; i += 1
        n |= (d & 0x7F) << shift
        shift += 7
        if not d & 0x80:
            return n, i
    raise ValueError("varint too long")


async def rcon(host, port, password, command):
    def _call():
        s = socket.create_connection((host, port), timeout=10)
        try:
            def pkt(rid, ptype, body):
                data = struct.pack("<ii", rid, ptype) + body.encode() + b"\x00\x00"
                return struct.pack("<i", len(data)) + data

            def read_pkt():
                ln = struct.unpack("<i", _recvall(s, 4))[0]
                buf = _recvall(s, ln)
                rid, ptype = struct.unpack("<ii", buf[:8])
                return rid, ptype, buf[8:-2].decode(errors="replace")

            s.sendall(pkt(1, 3, password))
            rid, _, _ = read_pkt()
            if rid == -1:
                raise PermissionError("rcon: bad password")
            s.sendall(pkt(secrets.randbits(30), 2, command))
            _, _, body = read_pkt()
            return body
        finally:
            s.close()
    return await asyncio.to_thread(_call)


async def mcping(host, port=25565):
    """Server list ping (no deps). Returns dict or raises."""
    def _call():
        s = socket.create_connection((host, port), timeout=5)
        try:
            def vi(n):
                out = b""
                while True:
                    x = n & 0x7F
                    n >>= 7
                    if n:
                        out += bytes([x | 0x80])
                    else:
                        return out + bytes([x])

            host_b = host.encode()
            hs = b"\x00" + vi(774) + vi(len(host_b)) + host_b + struct.pack(">H", port) + b"\x01"
            s.sendall(vi(len(hs)) + hs)
            time.sleep(0.2)  # некоторые ядра дропают request, пришитый в тот же сегмент
            s.sendall(b"\x01\x00")
            plen, _ = _recv_varint(s)   # packet length из потока
            buf = _recvall(s, plen)
            if buf[0] != 0:
                raise ConnectionError(f"unexpected packet id {buf[0]}")
            jl, i = _parse_varint(buf, 1)
            return json.loads(buf[i:i + jl].decode(errors="replace"))
        finally:
            s.close()
    return await asyncio.to_thread(_call)
