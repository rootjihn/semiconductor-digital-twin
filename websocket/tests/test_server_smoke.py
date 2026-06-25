import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request

from throughline_ws.client import exchange


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class ServerSmokeTests(unittest.TestCase):
    def setUp(self):
        self.port = free_port()
        env = os.environ.copy()
        src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
        env["PYTHONPATH"] = src
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "throughline_ws.server", "--host", "127.0.0.1", "--port", str(self.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=0.2) as res:
                    body = json.loads(res.read().decode("utf-8"))
                    if body["ok"]:
                        return
            except Exception:
                time.sleep(0.05)
        self.fail("server did not become healthy")

    def tearDown(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)
        finally:
            if self.proc.stdout:
                self.proc.stdout.close()
            if self.proc.stderr:
                self.proc.stderr.close()

    def test_echo_exchange(self):
        responses = asyncio.run(exchange(
            f"ws://127.0.0.1:{self.port}/ws",
            {"type": "echo", "source": "test", "payload": {"text": "hello"}},
            receive_count=2,
        ))
        self.assertEqual(responses[0]["type"], "welcome")
        self.assertEqual(responses[1]["type"], "echo")
        self.assertEqual(responses[1]["payload"]["text"], "hello")

    def test_publish_updates_state_snapshot(self):
        responses = asyncio.run(exchange(
            f"ws://127.0.0.1:{self.port}/ws",
            {
                "type": "publish",
                "source": "test",
                "topic": "/cell/modbus/state",
                "payload": {"process_state": 70},
            },
            receive_count=2,
        ))
        state = responses[-1]["snapshot"]["topics"]["/cell/modbus/state"]
        self.assertEqual(state["payload"]["process_state"], 70)

    def test_command_ack(self):
        responses = asyncio.run(exchange(
            f"ws://127.0.0.1:{self.port}/ws",
            {"type": "command", "source": "test", "target": "process_manager", "command": "start", "request_id": "r1"},
            receive_count=3,
        ))
        ack = next(item for item in responses if item["type"] == "command_ack")
        self.assertTrue(ack["accepted"])
        self.assertEqual(ack["request_id"], "r1")


if __name__ == "__main__":
    unittest.main()
