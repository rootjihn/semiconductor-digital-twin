"""Throughline WebSocket MVP CLI client."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, List
from urllib.parse import urlparse

from .ws_protocol import encode_frame, make_accept_key, make_client_key, read_frame


async def connect(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in {"ws", "wss"}:
        raise ValueError("only ws:// URLs are supported in the stdlib MVP client")
    if parsed.scheme == "wss":
        raise ValueError("wss:// requires TLS support and is intentionally excluded from MVP 01")

    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    path = parsed.path or "/ws"
    if parsed.query:
        path += "?" + parsed.query

    reader, writer = await asyncio.open_connection(host, port)
    key = make_client_key()
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    writer.write(request.encode("ascii"))
    await writer.drain()

    raw_response = await reader.readuntil(b"\r\n\r\n")
    response_text = raw_response.decode("iso-8859-1")
    if "101 Switching Protocols" not in response_text:
        raise RuntimeError(f"websocket handshake failed: {response_text!r}")
    expected = make_accept_key(key)
    if expected not in response_text:
        raise RuntimeError("websocket accept key mismatch")
    return reader, writer


async def send_json(writer, message: Dict[str, Any]) -> None:
    writer.write(encode_frame(json.dumps(message, ensure_ascii=False), mask=True))
    await writer.drain()


async def receive_json(reader) -> Dict[str, Any]:
    opcode, payload = await read_frame(reader)
    if opcode == 0x8:
        raise EOFError("server closed websocket")
    return json.loads(payload.decode("utf-8"))


async def exchange(url: str, message: Dict[str, Any], receive_count: int = 2, timeout: float = 1.0) -> List[Dict[str, Any]]:
    reader, writer = await connect(url)
    received: List[Dict[str, Any]] = []
    try:
        # 서버가 연결 직후 welcome을 보낸다.
        received.append(await asyncio.wait_for(receive_json(reader), timeout=timeout))
        await send_json(writer, message)
        for _ in range(receive_count - 1):
            try:
                received.append(await asyncio.wait_for(receive_json(reader), timeout=timeout))
            except asyncio.TimeoutError:
                break
    finally:
        writer.write(encode_frame(b"", opcode=0x8, mask=True))
        await writer.drain()
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
    return received


async def listen(url: str) -> None:
    reader, writer = await connect(url)
    try:
        while True:
            print(json.dumps(await receive_json(reader), ensure_ascii=False), flush=True)
    finally:
        writer.close()
        await writer.wait_closed()


def parse_payload(payload: str) -> Dict[str, Any]:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("payload must be a JSON object")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Throughline WebSocket MVP client")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_url(p):
        p.add_argument("--url", default="ws://127.0.0.1:8765/ws")

    p_echo = sub.add_parser("echo")
    add_url(p_echo)
    p_echo.add_argument("--text", default="hello")

    p_publish = sub.add_parser("publish")
    add_url(p_publish)
    p_publish.add_argument("--topic", required=True)
    p_publish.add_argument("--payload", required=True)
    p_publish.add_argument("--source", default="cli")

    p_command = sub.add_parser("command")
    add_url(p_command)
    p_command.add_argument("--command", required=True)
    p_command.add_argument("--target", default="process_manager")
    p_command.add_argument("--source", default="cli")
    p_command.add_argument("--request-id", default=None)

    p_listen = sub.add_parser("listen")
    add_url(p_listen)

    args = parser.parse_args()

    if args.cmd == "listen":
        asyncio.run(listen(args.url))
        return
    if args.cmd == "echo":
        message = {"type": "echo", "source": "cli", "payload": {"text": args.text}}
        responses = asyncio.run(exchange(args.url, message, receive_count=2))
    elif args.cmd == "publish":
        message = {"type": "publish", "source": args.source, "topic": args.topic, "payload": parse_payload(args.payload)}
        responses = asyncio.run(exchange(args.url, message, receive_count=2))
    else:
        message = {"type": "command", "source": args.source, "target": args.target, "command": args.command, "request_id": args.request_id}
        responses = asyncio.run(exchange(args.url, message, receive_count=3))

    for response in responses:
        print(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
