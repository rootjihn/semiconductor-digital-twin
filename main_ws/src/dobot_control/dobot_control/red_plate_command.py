"""Convenience command sender for the red plate interactive calibrator."""

from __future__ import annotations

import json
import time
from typing import Any

import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from std_msgs.msg import String


COMMAND_HELPER_LAUNCH = "ros2 launch dobot_control red_plate_command.launch.py"
INTERACTIVE_LAUNCH = "ros2 launch dobot_control red_plate_interactive_calibrator.launch.py"
STATUS_TOPIC_DEFAULT = "/dobot_control/red_plate_calibration/status"


class RedPlateCommand(Node):
    """Publish one interactive command and echo the calibrator's next prompt."""

    def __init__(self) -> None:
        super().__init__("red_plate_command")
        dynamic_descriptor = ParameterDescriptor(dynamic_typing=True)
        self.declare_parameter("command", "", descriptor=dynamic_descriptor)
        self.declare_parameter(
            "command_topic",
            "/dobot_control/red_plate_calibration/command",
        )
        self.declare_parameter("status_topic", STATUS_TOPIC_DEFAULT)
        self.declare_parameter("status_wait_sec", "2.0", descriptor=dynamic_descriptor)
        self._command = str(self.get_parameter("command").value).strip()
        self._command_topic = str(self.get_parameter("command_topic").value)
        self._status_topic = str(self.get_parameter("status_topic").value)
        self._status_messages: list[dict[str, Any]] = []
        self._publisher = self.create_publisher(String, self._command_topic, 10)
        self.create_subscription(String, self._status_topic, self._status_callback, 10)

    def run_once(self) -> None:
        """Print help when command is empty; otherwise publish and show next step."""
        if not self._command:
            self._print_help()
            return

        # Give ROS discovery a short moment after pub/sub creation.
        self._spin_for(0.5)
        self._status_messages.clear()

        msg = String()
        msg.data = self._command
        self._publisher.publish(msg)

        followup = self._wait_for_followup_status()
        self._print_panel("전송 완료", [f"command:={self._command}"])
        if followup is None:
            self._print_panel(
                "다음 단계",
                [
                    "보정 노드 터미널의 다음 선택 안내를 확인하세요.",
                    "응답이 없으면 보정 노드 실행/토픽 연결 상태를 확인하세요.",
                ],
            )
            return
        self._print_status(followup)

    def _status_callback(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError:
            payload = {"event": "status", "title": "상태", "lines": [msg.data]}
        if isinstance(payload, dict):
            self._status_messages.append(payload)

    def _status_wait_sec(self) -> float:
        try:
            return max(0.0, float(str(self.get_parameter("status_wait_sec").value)))
        except ValueError:
            return 2.0

    def _spin_for(self, seconds: float) -> None:
        end_time = time.monotonic() + seconds
        while time.monotonic() < end_time:
            rclpy.spin_once(self, timeout_sec=0.05)

    def _wait_for_followup_status(self) -> dict[str, Any] | None:
        deadline = time.monotonic() + self._status_wait_sec()
        latest: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            while self._status_messages:
                latest = self._status_messages.pop(0)
                if latest.get("event") == "prompt":
                    return latest
        return latest

    def _print_panel(self, title: str, lines: list[str]) -> None:
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
        print(f"▶ {title}", flush=True)
        for line in lines:
            print(f"  {line}", flush=True)
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)

    def _print_status(self, payload: dict[str, Any]) -> None:
        event = str(payload.get("event", "status"))
        title = str(payload.get("title", "상태"))
        raw_lines = payload.get("lines", [])
        if isinstance(raw_lines, list):
            lines = [str(line) for line in raw_lines]
        else:
            lines = [str(raw_lines)]
        if event == "prompt":
            self._print_panel("다음 단계", lines)
            return
        self._print_panel(title, lines)

    def _print_help(self) -> None:
        self._print_panel(
            "red plate command",
            [
                f"먼저 실행: {INTERACTIVE_LAUNCH}",
                f"선택 보내기: {COMMAND_HELPER_LAUNCH} command:=1",
                "다른 선택: command:=2 또는 command:=3",
                "기준: 보정 노드의 '다음 선택' 번호",
            ],
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = RedPlateCommand()
    try:
        node.run_once()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
