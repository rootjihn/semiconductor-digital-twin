"""ROS2/Modbus 연동 경계 skeleton.

이 파일은 MVP 03 산출물이다. 현재 원격 개발 환경에는 rclpy/pymodbus가 없으므로
실제 ROS2 node를 바로 띄우지 않고, WebSocket gateway가 어떤 topic/service와 연결될지
명확히 남긴다.

중요 정책:
- WebSocket gateway는 Modbus 서버/PLC를 직접 polling/write하지 않는다.
- Modbus 상태는 modbus_bridge_node가 ROS2 topic으로 publish한 요약 snapshot을 받는다.
- Dashboard 명령은 process_manager_node의 command service로 전달한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RosEndpointPlan:
    name: str
    direction: str
    ros_name: str
    websocket_topic: str
    note: str


ROS_ENDPOINTS: List[RosEndpointPlan] = [
    RosEndpointPlan(
        name="modbus_state",
        direction="subscribe",
        ros_name="/cell/modbus/state",
        websocket_topic="/cell/modbus/state",
        note="modbus_bridge_node가 PLC/mock 상태를 publish하면 Dashboard로 broadcast한다.",
    ),
    RosEndpointPlan(
        name="process_state",
        direction="subscribe",
        ros_name="/cell/process/state",
        websocket_topic="/cell/process/state",
        note="process_manager_node의 상태머신 요약을 Dashboard로 broadcast한다.",
    ),
    RosEndpointPlan(
        name="robodk_state",
        direction="subscribe",
        ros_name="/cell/robodk/state",
        websocket_topic="/cell/robodk/state",
        note="Windows RoboDK agent와 통신하는 robodk_bridge_node의 요약 상태다.",
    ),
    RosEndpointPlan(
        name="process_command",
        direction="service_client",
        ros_name="/cell/process/command",
        websocket_topic="command",
        note="Dashboard command를 실제 장비 명령으로 바꾸는 유일한 권장 경로다.",
    ),
]


@dataclass
class GatewayCommand:
    command: str
    target: str = "process_manager"
    args: Dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None


def build_publish_message(endpoint_name: str, payload: Dict[str, Any], source: str = "ros2_adapter") -> Dict[str, Any]:
    endpoint = next((item for item in ROS_ENDPOINTS if item.name == endpoint_name), None)
    if endpoint is None:
        raise ValueError(f"unknown endpoint: {endpoint_name}")
    if endpoint.direction != "subscribe":
        raise ValueError(f"endpoint is not subscribable: {endpoint_name}")
    return {
        "type": "publish",
        "source": source,
        "topic": endpoint.websocket_topic,
        "payload": payload,
    }


def map_gateway_command_to_ros_service(command: GatewayCommand) -> Dict[str, Any]:
    """향후 ROS2 service request로 변환될 중간 표현을 만든다."""
    return {
        "service": "/cell/process/command",
        "request": {
            "command": command.command,
            "target": command.target,
            "args": command.args,
            "request_id": command.request_id,
        },
    }
