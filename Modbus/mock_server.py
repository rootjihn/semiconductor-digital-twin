#!/usr/bin/env python3
"""관통프로젝트 Modbus mock server 골격.

목적:
- 실제 PLC/컨베이어 보드가 없을 때 Ubuntu에서 가짜 Modbus Server를 띄운다.
- process_manager_node / modbus_bridge_node / dashboard가 붙을 상태 저장소를 제공한다.
- register map과 상태 흐름을 실제 장비 전에 먼저 검증한다.

주의:
- 기본 포트는 15020이다.
- Linux에서 502 포트는 보통 root 권한이 필요하므로 개발 단계 기본값으로 쓰지 않는다.
- 실제 장비 연동 단계에서만 502 또는 장비 명세 포트로 맞춘다.
"""

from __future__ import annotations

import argparse
import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

from modbus_map import COMMAND_COILS, RegisterMap

PYMODBUS_IMPORT_ERROR: Optional[Exception] = None

try:
    from pymodbus.server import StartTcpServer
    from pymodbus.datastore import (
        ModbusSequentialDataBlock,
        ModbusServerContext,
        ModbusSlaveContext,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - 설치 전에도 스크립트 자체는 읽혀야 함
    StartTcpServer = None
    ModbusSequentialDataBlock = None
    ModbusServerContext = None
    ModbusSlaveContext = None
    PYMODBUS_IMPORT_ERROR = exc

LOGGER = logging.getLogger("throughline.modbus.mock_server")


# pymodbus datastore function code 매핑
FC_COILS = 1
FC_DISCRETE_INPUTS = 2
FC_HOLDING_REGISTERS = 3
FC_INPUT_REGISTERS = 4

# client pulse-coil 기본 hold_sec=0.1보다 짧게 잡아 command를 놓치지 않게 한다.
COMMAND_POLL_INTERVAL_SEC = 0.05


class ProcessState:
    IDLE = 0
    INIT = 10
    CAMERA_READY = 20
    DOBOT_READY = 30
    PICK_TARGET_DETECTED = 40
    DOBOT_PICKING = 50
    PICK_DONE = 60
    CONVEYOR_MOVING = 70
    CONVEYOR_STOPPED_AT_ZONE = 80
    PACKAGING_SIM_RUNNING = 90
    POST_PACKAGING_RECOGNITION = 100
    RE_PICK_READY = 110
    DOBOT_RE_PICKING = 120
    LOAD_TO_TURTLEBOT_READY = 130
    TURTLEBOT_LOADING = 140
    TURTLEBOT_DISPATCHED = 150
    COMPLETE = 900
    ERROR = 999


class DeviceState:
    OFFLINE = 0
    READY = 1
    BUSY = 2
    PAUSED = 3
    LOADED = 3
    MOVING = 4
    WAITING_TRIGGER = 6
    FAULT = 9


@dataclass
class MockServerConfig:
    host: str = "0.0.0.0"
    port: int = 15020
    unit_id: int = 1
    debug: bool = False
    demo_mode: bool = True
    heartbeat_interval_sec: float = 1.0
    demo_step_interval_sec: float = 3.0


class MockCellStore:
    """datastore 접근을 감싸는 얇은 헬퍼.

    모든 레지스터 접근을 여기로 모아두면 나중에 로그/검증/변환을 붙이기 쉽다.
    """

    def __init__(self, context: "ModbusServerContext", unit_id: int) -> None:
        self.context = context
        self.unit_id = unit_id
        self._lock = threading.Lock()

    @property
    def slave(self):
        return self.context[self.unit_id]

    def get_values(self, fc: int, address: int, count: int = 1):
        with self._lock:
            return self.slave.getValues(fc, address, count=count)

    def set_values(self, fc: int, address: int, values: list[int]) -> None:
        with self._lock:
            self.slave.setValues(fc, address, values)

    def write_coil(self, address: int, value: int) -> None:
        self.set_values(FC_COILS, address, [value])

    def write_di(self, address: int, value: int) -> None:
        self.set_values(FC_DISCRETE_INPUTS, address, [value])

    def write_hr(self, address: int, value: int) -> None:
        self.set_values(FC_HOLDING_REGISTERS, address, [value])

    def write_ir(self, address: int, value: int) -> None:
        self.set_values(FC_INPUT_REGISTERS, address, [value])

    def read_hr(self, address: int) -> int:
        return int(self.get_values(FC_HOLDING_REGISTERS, address, 1)[0])

    def read_coil(self, address: int) -> int:
        return int(self.get_values(FC_COILS, address, 1)[0])

    def pulse_coil(self, address: int, hold_sec: float = 0.1) -> None:
        self.write_coil(address, 1)
        time.sleep(hold_sec)
        self.write_coil(address, 0)


class DemoSimulator:
    """README에 적어둔 상태 흐름을 흉내 내는 최소 시뮬레이터.

    현재는 골격만 제공한다. 실제 프로젝트 로직이 확정되면 아래 메서드만 보강하면 된다.
    """

    def __init__(self, store: MockCellStore, config: MockServerConfig) -> None:
        self.store = store
        self.config = config
        self.stop_event = threading.Event()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._command_thread: Optional[threading.Thread] = None
        self._demo_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self.seed_initial_state()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="modbus-heartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()

        self._command_thread = threading.Thread(
            target=self._command_loop,
            name="modbus-command",
            daemon=True,
        )
        self._command_thread.start()

        if self.config.demo_mode:
            self._demo_thread = threading.Thread(
                target=self._demo_loop,
                name="modbus-demo",
                daemon=True,
            )
            self._demo_thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def seed_initial_state(self) -> None:
        # 기본 공정 상태
        self.store.write_hr(RegisterMap.HR_PROCESS_STATE, ProcessState.IDLE)
        self.store.write_hr(RegisterMap.HR_PROCESS_SUBSTATE, 0)
        self.store.write_hr(RegisterMap.HR_COMMAND_SEQ, 0)
        self.store.write_hr(RegisterMap.HR_LAST_ACK_SEQ, 0)
        self.store.write_hr(RegisterMap.HR_ERROR_CODE, 0)
        self.store.write_hr(RegisterMap.HR_WARN_CODE, 0)
        self.store.write_hr(RegisterMap.HR_HEARTBEAT_PC, 0)
        self.store.write_hr(RegisterMap.HR_HEARTBEAT_PLC, 0)

        # 장치 상태
        self.store.write_hr(RegisterMap.HR_DOBOT_STATE, DeviceState.READY)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_STATE, DeviceState.READY)
        self.store.write_hr(RegisterMap.HR_CAMERA_STATE, DeviceState.READY)
        self.store.write_hr(RegisterMap.HR_TURTLEBOT_STATE, DeviceState.READY)
        self.store.write_hr(RegisterMap.HR_ROBODK_STATE, DeviceState.READY)
        self.store.write_hr(RegisterMap.HR_ROBODK_LAST_CMD, 0)
        self.store.write_hr(RegisterMap.HR_ROBODK_LAST_ACK_SEQ, 0)
        self.store.write_hr(RegisterMap.HR_ROBODK_ERROR_CODE, 0)

        # 운전/카운트/속도
        self.store.write_hr(RegisterMap.HR_OPERATION_MODE, 1)  # auto
        self.store.write_hr(RegisterMap.HR_TARGET_COUNT_TOTAL, 0)
        self.store.write_hr(RegisterMap.HR_TARGET_COUNT_DONE, 0)
        self.store.write_hr(RegisterMap.HR_TARGET_COUNT_NG, 0)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_SPEED_SET, 0)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_SPEED_ACTUAL, 0)

        # 센서/측정값
        self.store.write_di(RegisterMap.DI_SENSOR_INFEED, 0)
        self.store.write_di(RegisterMap.DI_SENSOR_PICK_ZONE, 0)
        self.store.write_di(RegisterMap.DI_SENSOR_PACKAGING_ZONE, 0)
        self.store.write_di(RegisterMap.DI_SENSOR_OUTFEED, 0)
        self.store.write_di(RegisterMap.DI_ESTOP, 0)
        self.store.write_di(RegisterMap.DI_DOOR_OPEN, 0)

        self.store.write_ir(RegisterMap.IR_SENSOR_DISTANCE_MM, 250)
        self.store.write_ir(RegisterMap.IR_CYCLE_TIME_MS, 0)
        self.store.write_ir(RegisterMap.IR_ALARM_ACTIVE_CODE, 0)
        self.store.write_ir(RegisterMap.IR_BOARD_TEMPERATURE, 32)

        LOGGER.info("초기 Modbus mock 상태를 적재했습니다.")

    def _heartbeat_loop(self) -> None:
        while not self.stop_event.is_set():
            current = self.store.read_hr(RegisterMap.HR_HEARTBEAT_PLC)
            next_value = (current + 1) % 65535
            self.store.write_hr(RegisterMap.HR_HEARTBEAT_PLC, next_value)
            time.sleep(self.config.heartbeat_interval_sec)

    def _command_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                for coil_address in COMMAND_COILS:
                    if self.stop_event.is_set():
                        return
                    if self.store.read_coil(coil_address):
                        try:
                            self._handle_command_coil(coil_address)
                        finally:
                            self.store.write_coil(coil_address, 0)
            except Exception:  # pragma: no cover - background thread 안전망
                LOGGER.exception("command loop 처리 중 오류")

            time.sleep(COMMAND_POLL_INTERVAL_SEC)

    def _handle_command_coil(self, coil_address: int) -> None:
        if coil_address == RegisterMap.CO_CMD_START:
            self._handle_start()
        elif coil_address == RegisterMap.CO_CMD_STOP:
            self._handle_stop()
        elif coil_address == RegisterMap.CO_CMD_PAUSE:
            self._handle_pause()
        elif coil_address == RegisterMap.CO_CMD_RESET:
            self._handle_reset()
        elif coil_address == RegisterMap.CO_CMD_ACK_ALARM:
            self._handle_ack_alarm()
        elif coil_address == RegisterMap.CO_CMD_CONVEYOR_RUN:
            self._handle_conveyor_run()
        elif coil_address == RegisterMap.CO_CMD_CONVEYOR_STOP:
            self._handle_conveyor_stop()
        elif coil_address == RegisterMap.CO_CMD_MANUAL_MODE:
            self._handle_manual_mode()
        else:
            LOGGER.warning("알 수 없는 coil command: CO%s", coil_address)
            return

        self._ack_command()
        LOGGER.info("coil command 처리 완료: CO%s", coil_address)

    def _ack_command(self) -> None:
        current = self.store.read_hr(RegisterMap.HR_LAST_ACK_SEQ)
        self.store.write_hr(RegisterMap.HR_LAST_ACK_SEQ, (current + 1) % 65535)

    def _handle_start(self) -> None:
        self.store.write_hr(RegisterMap.HR_PROCESS_STATE, ProcessState.INIT)
        self.store.write_hr(RegisterMap.HR_PROCESS_SUBSTATE, 0)
        self.store.write_hr(RegisterMap.HR_OPERATION_MODE, 1)  # auto
        self.store.write_hr(RegisterMap.HR_ERROR_CODE, 0)
        self.store.write_hr(RegisterMap.HR_WARN_CODE, 0)

    def _handle_stop(self) -> None:
        self.store.write_hr(RegisterMap.HR_PROCESS_STATE, ProcessState.IDLE)
        self.store.write_hr(RegisterMap.HR_PROCESS_SUBSTATE, 0)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_STATE, DeviceState.READY)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_SPEED_ACTUAL, 0)
        self.store.write_hr(RegisterMap.HR_DOBOT_STATE, DeviceState.READY)
        self.store.write_hr(RegisterMap.HR_ROBODK_STATE, DeviceState.READY)

    def _handle_pause(self) -> None:
        self.store.write_hr(RegisterMap.HR_PROCESS_SUBSTATE, 1)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_STATE, DeviceState.PAUSED)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_SPEED_ACTUAL, 0)

    def _handle_reset(self) -> None:
        self.store.write_hr(RegisterMap.HR_ERROR_CODE, 0)
        self.store.write_hr(RegisterMap.HR_WARN_CODE, 0)
        self.store.write_ir(RegisterMap.IR_ALARM_ACTIVE_CODE, 0)
        self.store.write_hr(RegisterMap.HR_PROCESS_STATE, ProcessState.IDLE)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_STATE, DeviceState.READY)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_SPEED_ACTUAL, 0)

    def _handle_ack_alarm(self) -> None:
        self.store.write_hr(RegisterMap.HR_WARN_CODE, 0)
        self.store.write_ir(RegisterMap.IR_ALARM_ACTIVE_CODE, 0)

    def _handle_conveyor_run(self) -> None:
        speed_set = self.store.read_hr(RegisterMap.HR_CONVEYOR_SPEED_SET)
        speed = speed_set if speed_set > 0 else 100
        self.store.write_hr(RegisterMap.HR_CONVEYOR_STATE, DeviceState.MOVING)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_SPEED_ACTUAL, speed)
        self.store.write_hr(RegisterMap.HR_PROCESS_STATE, ProcessState.CONVEYOR_MOVING)

    def _handle_conveyor_stop(self) -> None:
        self.store.write_hr(RegisterMap.HR_CONVEYOR_STATE, DeviceState.READY)
        self.store.write_hr(RegisterMap.HR_CONVEYOR_SPEED_ACTUAL, 0)
        self.store.write_hr(RegisterMap.HR_PROCESS_STATE, ProcessState.CONVEYOR_STOPPED_AT_ZONE)

    def _handle_manual_mode(self) -> None:
        self.store.write_hr(RegisterMap.HR_OPERATION_MODE, 0)  # manual
        self.store.write_hr(RegisterMap.HR_PROCESS_SUBSTATE, 0)

    def _demo_loop(self) -> None:
        demo_states = [
            ProcessState.IDLE,
            ProcessState.INIT,
            ProcessState.CAMERA_READY,
            ProcessState.DOBOT_READY,
            ProcessState.PICK_TARGET_DETECTED,
            ProcessState.DOBOT_PICKING,
            ProcessState.PICK_DONE,
            ProcessState.CONVEYOR_MOVING,
            ProcessState.CONVEYOR_STOPPED_AT_ZONE,
            ProcessState.PACKAGING_SIM_RUNNING,
            ProcessState.POST_PACKAGING_RECOGNITION,
            ProcessState.RE_PICK_READY,
            ProcessState.DOBOT_RE_PICKING,
            ProcessState.LOAD_TO_TURTLEBOT_READY,
            ProcessState.TURTLEBOT_LOADING,
            ProcessState.TURTLEBOT_DISPATCHED,
            ProcessState.COMPLETE,
        ]

        while not self.stop_event.is_set():
            for state in demo_states:
                if self.stop_event.is_set():
                    return
                self._apply_demo_state(state)
                time.sleep(self.config.demo_step_interval_sec)

    def _apply_demo_state(self, state: int) -> None:
        self.store.write_hr(RegisterMap.HR_PROCESS_STATE, state)

        # 최소 데모용 mirror 상태
        if state == ProcessState.CONVEYOR_MOVING:
            self.store.write_hr(RegisterMap.HR_CONVEYOR_STATE, DeviceState.MOVING)
            self.store.write_hr(RegisterMap.HR_CONVEYOR_SPEED_ACTUAL, 100)
        elif state == ProcessState.CONVEYOR_STOPPED_AT_ZONE:
            self.store.write_hr(RegisterMap.HR_CONVEYOR_STATE, DeviceState.READY)
            self.store.write_hr(RegisterMap.HR_CONVEYOR_SPEED_ACTUAL, 0)
            self.store.write_di(RegisterMap.DI_SENSOR_PACKAGING_ZONE, 1)
        elif state == ProcessState.PACKAGING_SIM_RUNNING:
            self.store.write_hr(RegisterMap.HR_ROBODK_STATE, 3)
        elif state == ProcessState.POST_PACKAGING_RECOGNITION:
            self.store.write_hr(RegisterMap.HR_ROBODK_STATE, 5)
            self.store.write_di(RegisterMap.DI_SENSOR_PACKAGING_ZONE, 0)
        elif state == ProcessState.COMPLETE:
            done = self.store.read_hr(RegisterMap.HR_TARGET_COUNT_DONE)
            self.store.write_hr(RegisterMap.HR_TARGET_COUNT_DONE, done + 1)
        elif state == ProcessState.IDLE:
            self.store.write_hr(RegisterMap.HR_CONVEYOR_SPEED_ACTUAL, 0)
            self.store.write_hr(RegisterMap.HR_ROBODK_STATE, DeviceState.READY)

        LOGGER.info("demo state 적용: %s", state)


def build_context(unit_id: int):
    if PYMODBUS_IMPORT_ERROR is not None:
        raise RuntimeError(
            "pymodbus가 설치되어 있지 않습니다. "
            "`pip install -r requirements.txt` 후 다시 실행하세요."
        ) from PYMODBUS_IMPORT_ERROR

    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0] * 1000),
        co=ModbusSequentialDataBlock(0, [0] * 1000),
        ir=ModbusSequentialDataBlock(0, [0] * 1000),
        hr=ModbusSequentialDataBlock(0, [0] * 1000),
    )
    return ModbusServerContext(slaves={unit_id: store}, single=False)


def configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def parse_args() -> MockServerConfig:
    parser = argparse.ArgumentParser(description="관통프로젝트 PyModbus mock server")
    parser.add_argument("--host", default="0.0.0.0", help="bind host")
    parser.add_argument("--port", type=int, default=15020, help="bind port (개발 기본값: 15020)")
    parser.add_argument("--unit-id", type=int, default=1, help="Modbus unit/slave id")
    parser.add_argument("--debug", action="store_true", help="debug logging 활성화")
    parser.add_argument(
        "--no-demo",
        action="store_true",
        help="자동 상태 전이 데모를 끄고 heartbeat/초기 상태만 유지",
    )
    parser.add_argument(
        "--heartbeat-interval-sec",
        type=float,
        default=1.0,
        help="heartbeat_plc 증가 주기",
    )
    parser.add_argument(
        "--demo-step-interval-sec",
        type=float,
        default=3.0,
        help="demo 모드 단계 전이 간격",
    )
    args = parser.parse_args()
    return MockServerConfig(
        host=args.host,
        port=args.port,
        unit_id=args.unit_id,
        debug=args.debug,
        demo_mode=not args.no_demo,
        heartbeat_interval_sec=args.heartbeat_interval_sec,
        demo_step_interval_sec=args.demo_step_interval_sec,
    )


def main() -> int:
    config = parse_args()
    configure_logging(config.debug)

    context = build_context(config.unit_id)
    store = MockCellStore(context=context, unit_id=config.unit_id)
    simulator = DemoSimulator(store=store, config=config)
    simulator.start()

    LOGGER.info(
        "Modbus mock server 시작: host=%s port=%s unit_id=%s demo_mode=%s",
        config.host,
        config.port,
        config.unit_id,
        config.demo_mode,
    )

    try:
        StartTcpServer(context=context, address=(config.host, config.port))
    except KeyboardInterrupt:
        LOGGER.info("사용자 중단으로 mock server를 종료합니다.")
    finally:
        simulator.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
