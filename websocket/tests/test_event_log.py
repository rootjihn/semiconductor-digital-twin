import tempfile
import unittest
from pathlib import Path

from throughline_ws.event_log import EventLog


class EventLogTests(unittest.TestCase):
    def test_record_and_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = EventLog(Path(tmp) / "events.sqlite3")
            log.record("2026-01-01T00:00:00Z", "publish", {"topic": "/cell/process/state", "payload": {"process_state": 10}})
            log.record("2026-01-01T00:00:01Z", "command", {"command": "start"})
            self.assertEqual(log.count(), 2)


if __name__ == "__main__":
    unittest.main()
