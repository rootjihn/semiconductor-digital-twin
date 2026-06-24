"""Modbus bridge ROS2 node interface draft.

이 파일은 실제 Modbus I/O 구현 전, ROS2 topic/service 인터페이스를 먼저
고정하기 위한 노드 골격이다.

범위:
- /cell/modbus/state publisher 생성
- /cell/modbus/command service 생성
- /cell/modbus/pulse_coil service 생성
- /cell/modbus/write_register service 생성
- ROS2 parameter 이름 고정

비범위:
- 실제 pymodbus client 연결
- PLC/mock server polling
- coil/register write
- 공정 판단 또는 상태머신
"""

from __future__ import annotations

from typing import Final

import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from throughline_interfaces.msg import CellModbusState
from throughline_interfaces.srv import CellCommand, PulseCoil, WriteHoldingRegister


DEFAULT_NODE_NAME: Final[str] = "modbus_bridge_node"
DEFAULT_STATE_TOPIC: Final[str] = "/cell/modbus/state"
DEFAULT_COMMAND_SERVICE: Final[str] = "/cell/modbus/command"
DEFAULT_PULSE_COIL_SERVICE: Final[str] = "/cell/modbus/pulse_coil"
DEFAULT_WRITE_REGISTER_SERVICE: Final[str] = "/cell/modbus/write_register"


class ModbusBridgeNode(Node):
    """ROS2 인터페이스만 먼저 노출하는 Modbus bridge 노드 골격."""

    def __init__(self) -> None:
        super().__init__(DEFAULT_NODE_NAME)

        # 실제 I/O 구현 전에도 launch/config 이름을 고정하기 위해 parameter를 먼저 선언한다.
        self.declare_parameter("host", "127.0.0.1")
        self.declare_parameter("port", 15020)
        self.declare_parameter("unit_id", 1)
        self.declare_parameter("poll_hz", 5.0)
        self.declare_parameter("heartbeat_timeout_sec", 2.0)
        self.declare_parameter("reconnect_sec", 1.0)
        self.declare_parameter("default_pulse_ms", 100)
        self.declare_parameter("allow_low_level_write", False)
        self.declare_parameter("allowed_write_registers", [106, 130, 140, 141, 142, 150])

        state_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self._state_pub = self.create_publisher(CellModbusState, DEFAULT_STATE_TOPIC, state_qos)
        self._command_srv = self.create_service(
            CellCommand,
            DEFAULT_COMMAND_SERVICE,
            self._handle_command,
        )
        self._pulse_coil_srv = self.create_service(
            PulseCoil,
            DEFAULT_PULSE_COIL_SERVICE,
            self._handle_pulse_coil,
        )
        self._write_register_srv = self.create_service(
            WriteHoldingRegister,
            DEFAULT_WRITE_REGISTER_SERVICE,
            self._handle_write_register,
        )

        poll_hz = float(self.get_parameter("poll_hz").value)
        timer_period_sec = 1.0 / poll_hz if poll_hz > 0 else 0.2
        self._poll_count = 0
        self._error_count = 0
        self._timer = self.create_timer(timer_period_sec, self._publish_interface_stub_state)

        self.get_logger().info(
            "Modbus bridge interface-only stub started: "
            f"topic={DEFAULT_STATE_TOPIC}, "
            f"services=[{DEFAULT_COMMAND_SERVICE}, {DEFAULT_PULSE_COIL_SERVICE}, "
            f"{DEFAULT_WRITE_REGISTER_SERVICE}]"
        )

    def _publish_interface_stub_state(self) -> None:
        """실제 Modbus polling 전까지 interface 확인용 상태를 publish한다."""
        msg = CellModbusState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "modbus"
        msg.connected = False
        msg.stale_heartbeat = True
        msg.poll_count = self._poll_count
        msg.error_count = self._error_count

        # 나머지 register mirror 필드는 0 기본값을 유지한다.
        self._state_pub.publish(msg)
        self._poll_count += 1

    def _handle_command(self, request: CellCommand.Request, response: CellCommand.Response) -> CellCommand.Response:
        """상위 cell command service의 interface-only 응답."""
        self._error_count += 1
        response.accepted = False
        response.last_ack_seq = 0
        response.error_code = 1
        response.message = (
            "interface-only stub: Modbus command I/O is not implemented yet "
            f"(command={request.command}, command_seq={request.command_seq})"
        )
        return response

    def _handle_pulse_coil(self, request: PulseCoil.Request, response: PulseCoil.Response) -> PulseCoil.Response:
        """저수준 coil pulse service의 interface-only 응답."""
        self._error_count += 1
        response.ok = False
        response.last_ack_seq = 0
        response.error_code = 1
        response.message = (
            "interface-only stub: coil pulse I/O is not implemented yet "
            f"(address={request.address}, command_seq={request.command_seq}, pulse_ms={request.pulse_ms})"
        )
        return response

    def _handle_write_register(
        self,
        request: WriteHoldingRegister.Request,
        response: WriteHoldingRegister.Response,
    ) -> WriteHoldingRegister.Response:
        """저수준 holding register write service의 interface-only 응답."""
        self._error_count += 1
        response.ok = False
        response.last_ack_seq = 0
        response.error_code = 1
        response.message = (
            "interface-only stub: holding register write I/O is not implemented yet "
            f"(address={request.address}, value={request.value}, command_seq={request.command_seq})"
        )
        return response


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ModbusBridgeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
