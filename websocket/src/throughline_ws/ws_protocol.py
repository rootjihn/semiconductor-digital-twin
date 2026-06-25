"""최소 WebSocket protocol 구현.

운영용 고성능 구현이 아니라 MVP 검증용이다. 외부 패키지 설치가 불확실한
ROS2/Ubuntu 작업 PC에서 handshake, text frame, ping/pong을 먼저 검증하기 위해
Python 표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import base64
import hashlib
import os
import struct
from dataclasses import dataclass
from typing import Dict, Tuple

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


@dataclass
class HttpRequest:
    method: str
    path: str
    version: str
    headers: Dict[str, str]


def make_accept_key(sec_websocket_key: str) -> str:
    digest = hashlib.sha1((sec_websocket_key + GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def make_client_key() -> str:
    return base64.b64encode(os.urandom(16)).decode("ascii")


async def read_http_request(reader) -> HttpRequest:
    raw = await reader.readuntil(b"\r\n\r\n")
    text = raw.decode("iso-8859-1")
    lines = text.split("\r\n")
    request_line = lines[0]
    method, path, version = request_line.split(" ", 2)
    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return HttpRequest(method=method, path=path, version=version, headers=headers)


def is_websocket_request(request: HttpRequest) -> bool:
    upgrade = request.headers.get("upgrade", "").lower()
    connection = request.headers.get("connection", "").lower()
    return upgrade == "websocket" and "upgrade" in connection


def handshake_response(sec_websocket_key: str) -> bytes:
    accept = make_accept_key(sec_websocket_key)
    return (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        "\r\n"
    ).encode("ascii")


def http_response(status: str, body: bytes, content_type: str = "application/json") -> bytes:
    return (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii") + body


def encode_frame(payload: str | bytes, opcode: int = 0x1, mask: bool = False) -> bytes:
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    else:
        payload_bytes = payload

    first = 0x80 | (opcode & 0x0F)
    length = len(payload_bytes)
    mask_bit = 0x80 if mask else 0

    if length < 126:
        header = struct.pack("!BB", first, mask_bit | length)
    elif length < 65536:
        header = struct.pack("!BBH", first, mask_bit | 126, length)
    else:
        header = struct.pack("!BBQ", first, mask_bit | 127, length)

    if not mask:
        return header + payload_bytes

    mask_key = os.urandom(4)
    masked = bytes(byte ^ mask_key[i % 4] for i, byte in enumerate(payload_bytes))
    return header + mask_key + masked


async def read_frame(reader) -> Tuple[int, bytes]:
    first_two = await reader.readexactly(2)
    first, second = first_two
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F

    if length == 126:
        length = struct.unpack("!H", await reader.readexactly(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", await reader.readexactly(8))[0]

    mask_key = await reader.readexactly(4) if masked else b""
    payload = await reader.readexactly(length) if length else b""

    if masked:
        payload = bytes(byte ^ mask_key[i % 4] for i, byte in enumerate(payload))
    return opcode, payload
