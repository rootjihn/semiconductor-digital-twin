"""Throughline WebSocket Gateway MVP server."""
from __future__ import annotations

import argparse
import asyncio
import json
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Set

from .event_log import EventLog
from .ws_protocol import (
    handshake_response,
    http_response,
    is_websocket_request,
    read_frame,
    read_http_request,
    encode_frame,
)

ALLOWED_COMMANDS = {
    "start",
    "stop",
    "pause",
    "reset",
    "ack_alarm",
    "conveyor_run",
    "conveyor_stop",
    "manual_mode",
}
ALLOWED_TARGETS = {"process_manager", "dashboard", "modbus_bridge", "robodk_bridge"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class StateHub:
    """연결 client와 최신 topic snapshot을 관리한다."""

    def __init__(self, event_log: EventLog | None = None) -> None:
        self.clients: Set[Any] = set()
        self.state: Dict[str, Any] = {
            "topics": {},
            "commands": [],
            "events": [],
            "server_started_at": utc_now(),
        }
        self._lock = asyncio.Lock()
        self.event_log = event_log

    async def register(self, writer) -> None:
        async with self._lock:
            self.clients.add(writer)
        await self.send_json(writer, {"type": "welcome", "snapshot": self.state})

    async def unregister(self, writer) -> None:
        async with self._lock:
            self.clients.discard(writer)

    async def send_json(self, writer, message: Dict[str, Any]) -> None:
        writer.write(encode_frame(json.dumps(message, ensure_ascii=False)))
        await writer.drain()

    async def broadcast(self, message: Dict[str, Any]) -> None:
        dead = []
        async with self._lock:
            clients = list(self.clients)
        for writer in clients:
            try:
                await self.send_json(writer, message)
            except Exception:
                dead.append(writer)
        if dead:
            async with self._lock:
                for writer in dead:
                    self.clients.discard(writer)

    def _append_event(self, event: Dict[str, Any]) -> None:
        self.state["events"].append(event)
        self.state["events"] = self.state["events"][-50:]

    async def handle_message(self, writer, text: str) -> None:
        try:
            message = json.loads(text)
        except json.JSONDecodeError as exc:
            await self.send_json(writer, {"type": "error", "error": f"invalid json: {exc}"})
            return

        msg_type = message.get("type")
        if msg_type == "ping":
            await self.send_json(writer, {"type": "pong", "ts": utc_now()})
            return
        if msg_type == "hello":
            await self.send_json(writer, {"type": "welcome", "snapshot": self.state})
            return
        if msg_type == "echo":
            await self.send_json(writer, {"type": "echo", "payload": message.get("payload"), "ts": utc_now()})
            return
        if msg_type == "publish":
            await self._handle_publish(message)
            return
        if msg_type == "command":
            await self._handle_command(writer, message)
            return

        await self.send_json(writer, {"type": "error", "error": f"unsupported type: {msg_type}"})

    async def _handle_publish(self, message: Dict[str, Any]) -> None:
        topic = message.get("topic")
        if not isinstance(topic, str) or not topic.startswith("/"):
            await self.broadcast({"type": "error", "error": "publish requires absolute topic"})
            return

        source = message.get("source", "unknown")
        payload = message.get("payload", {})
        now = utc_now()
        self.state["topics"][topic] = {
            "source": source,
            "payload": payload,
            "updated_at": now,
        }
        event = {"type": "publish", "topic": topic, "source": source, "ts": now}
        self._append_event(event)
        if self.event_log:
            self.event_log.record(now, "publish", {**event, "payload": payload})
        await self.broadcast({"type": "state", "snapshot": self.state})

    async def _handle_command(self, writer, message: Dict[str, Any]) -> None:
        command = message.get("command")
        target = message.get("target", "process_manager")
        request_id = message.get("request_id")

        if command not in ALLOWED_COMMANDS:
            await self.send_json(writer, {"type": "command_ack", "accepted": False, "error": "unsupported command", "request_id": request_id})
            return
        if target not in ALLOWED_TARGETS:
            await self.send_json(writer, {"type": "command_ack", "accepted": False, "error": "unsupported target", "request_id": request_id})
            return

        command_event = {
            "command": command,
            "target": target,
            "source": message.get("source", "unknown"),
            "args": message.get("args", {}),
            "request_id": request_id,
            "created_at": utc_now(),
            "status": "accepted_by_gateway",
        }
        self.state["commands"].append(command_event)
        self.state["commands"] = self.state["commands"][-50:]
        now = utc_now()
        event = {"type": "command", "command": command, "target": target, "ts": now}
        self._append_event(event)
        if self.event_log:
            self.event_log.record(now, "command", {**event, "request_id": request_id, "args": message.get("args", {})})

        ack = {"type": "command_ack", "accepted": True, "request_id": request_id, "command": command, "target": target}
        await self.send_json(writer, ack)
        await self.broadcast({"type": "state", "snapshot": self.state})


async def handle_ws_connection(reader, writer, hub: StateHub) -> None:
    await hub.register(writer)
    try:
        while True:
            opcode, payload = await read_frame(reader)
            if opcode == 0x8:  # close
                break
            if opcode == 0x9:  # ping
                writer.write(encode_frame(payload, opcode=0xA))
                await writer.drain()
                continue
            if opcode != 0x1:
                await hub.send_json(writer, {"type": "error", "error": f"unsupported opcode: {opcode}"})
                continue
            await hub.handle_message(writer, payload.decode("utf-8"))
    except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
        pass
    finally:
        await hub.unregister(writer)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


def browser_client_html() -> bytes:
    html_path = Path(__file__).resolve().parents[2] / "clients" / "browser_client.html"
    if html_path.exists():
        return html_path.read_bytes()
    return b"Throughline WebSocket Gateway"


async def handle_http_or_ws(reader, writer, hub: StateHub) -> None:
    try:
        request = await read_http_request(reader)
        if is_websocket_request(request):
            key = request.headers.get("sec-websocket-key")
            if not key:
                writer.write(http_response("400 Bad Request", b'{"error":"missing websocket key"}'))
                await writer.drain()
                return
            writer.write(handshake_response(key))
            await writer.drain()
            await handle_ws_connection(reader, writer, hub)
            return

        if request.path == "/health":
            body = json.dumps({"ok": True, "service": "throughline_ws", "clients": len(hub.clients)}, ensure_ascii=False).encode("utf-8")
            writer.write(http_response("200 OK", body))
        elif request.path in {"/", "/client"}:
            writer.write(http_response("200 OK", browser_client_html(), content_type="text/html"))
        else:
            writer.write(http_response("404 Not Found", b'{"error":"not found"}'))
        await writer.drain()
    finally:
        if not writer.is_closing():
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


async def run_server(host: str, port: int, sqlite_path: str | None = None) -> None:
    event_log = EventLog(sqlite_path) if sqlite_path else None
    hub = StateHub(event_log=event_log)
    server = await asyncio.start_server(lambda r, w: handle_http_or_ws(r, w, hub), host, port)
    sockets = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Throughline WebSocket Gateway listening on {sockets}", flush=True)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    async with server:
        await stop_event.wait()
        server.close()
        await server.wait_closed()


def main() -> None:
    parser = argparse.ArgumentParser(description="Throughline WebSocket Gateway MVP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--sqlite-path", default=None, help="MVP 05 event log SQLite path")
    args = parser.parse_args()
    asyncio.run(run_server(args.host, args.port, sqlite_path=args.sqlite_path))


if __name__ == "__main__":
    main()
