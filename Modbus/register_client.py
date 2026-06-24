#!/usr/bin/env python3
"""관통프로젝트 Modbus register client 골격.

목적:
- mock_server.py 또는 실제 PLC/보드의 Modbus TCP register를 읽는다.
- raw register 값을 사람이 읽기 쉬운 CellSnapshot으로 디코딩한다.
- 개발 단계에서 read / watch / raw 명령으로 register map을 검증한다.

기본값은 mock_server.py와 맞춘다.
"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from modbus_map import RegisterMap

PYMODBUS_IMPORT_ERROR: Optional[Exception] = None

try:
    from pymodbus.client import ModbusTcpClient
except ModuleNotFoundError as exc:  # pragma: no cover - 설치 전에도 스크립트 자체는 읽혀야 함
    ModbusTcpClient = None
    PYMODBUS_IMPORT_ERROR = exc


LOGGER = logging.getLogger("throughline.modbus.register_client")


PROCESS_STATE_NAMES = {
    0: "IDLE",
    10: "INIT",
    20: "CAMERA_READY",
    30: "DOBOT_READY",
    40: "PICK_TARGET_DETECTED",
    50: "DOBOT_PICKING",
    60: "PICK_DONE",
    70: "CONVEYOR_MOVING",
    80: "CONVEYOR_STOPPED_AT_ZONE",
    90: "PACKAGING_SIM_RUNNING",
    100: "POST_PACKAGING_RECOGNITION",
    110: "RE_PICK_READY",
    120: "DOBOT_RE_PICKING",
    130: "LOAD_TO_TURTLEBOT_READY",
    140: "TURTLEBOT_LOADING",
    150: "TURTLEBOT_DISPATCHED",
    900: "COMPLETE",
    999: "ERROR",
}

DEVICE_STATE_NAMES = {
    0: "OFFLINE",
    1: "READY",
    2: "BUSY",
    3: "PAUSED_OR_LOADED",
    4: "MOVING",
    6: "WAITING_TRIGGER",
    9: "FAULT",
}

ROBODK_STATE_NAMES = {
    0: "OFFLINE",
    1: "READY",
    2: "STATION_LOADED",
    3: "SIM_RUNNING",
    4: "SIM_PAUSED",
    5: "SIM_DONE",
    6: "WAITING_TRIGGER",
    9: "FAULT",
}

OPERATION_MODE_NAMES = {
    0: "MANUAL",
    1: "AUTO",
    2: "MAINTENANCE",
}


@dataclass(frozen=True)
class ModbusClientConfig:
    host: str = "127.0.0.1"
    port: int = 15020
    unit_id: int = 1
    timeout_sec: float = 3.0
    poll_interval_sec: float = 1.0


@dataclass(frozen=True)
class CellSnapshot:
    process_state: int
    process_substate: int
    command_seq: int
    last_ack_seq: int
    error_code: int
    warn_code: int
    heartbeat_pc: int
    heartbeat_plc: int

    dobot_state: int
    conveyor_state: int
    camera_state: int
    turtlebot_state: int
    robodk_state: int

    target_total: int
    target_done: int
    target_ng: int

    conveyor_speed_set: int
    conveyor_speed_actual: int
    operation_mode: int

    sensor_distance_mm: int
    cycle_time_ms: int
    alarm_active_code: int
    board_temperature: int

    sensor_infeed: bool
    sensor_pick_zone: bool
    sensor_packaging_zone: bool
    sensor_outfeed: bool
    estop: bool
    door_open: bool


class ModbusReadError(RuntimeError):
    """Modbus 읽기/쓰기 실패를 CLI에서 명확히 보여주기 위한 예외."""


class ThroughlineModbusClient:
    """관통프로젝트용 얇은 Modbus TCP client wrapper."""

    def __init__(self, config: ModbusClientConfig) -> None:
        if PYMODBUS_IMPORT_ERROR is not None:
            raise RuntimeError(
                "pymodbus가 설치되어 있지 않습니다. "
                "`pip install -r requirements.txt` 후 다시 실행하세요."
            ) from PYMODBUS_IMPORT_ERROR

        self.config = config
        self.client = ModbusTcpClient(
            host=config.host,
            port=config.port,
            timeout=config.timeout_sec,
        )

    def connect(self) -> None:
        if not self.client.connect():
            raise ConnectionError(
                f"Modbus server 연결 실패: {self.config.host}:{self.config.port} "
                f"unit_id={self.config.unit_id}"
            )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "ThroughlineModbusClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.close()

    def read_holding(self, address: int, count: int = 1) -> list[int]:
        result = self.client.read_holding_registers(
            address,
            count=count,
            slave=self.config.unit_id,
        )
        return _extract_registers(result, f"HR{address}", count)

    def read_input_registers(self, address: int, count: int = 1) -> list[int]:
        result = self.client.read_input_registers(
            address,
            count=count,
            slave=self.config.unit_id,
        )
        return _extract_registers(result, f"IR{address}", count)

    def read_coils(self, address: int, count: int = 1) -> list[bool]:
        result = self.client.read_coils(
            address,
            count=count,
            slave=self.config.unit_id,
        )
        return _extract_bits(result, f"CO{address}", count)

    def read_discrete_inputs(self, address: int, count: int = 1) -> list[bool]:
        result = self.client.read_discrete_inputs(
            address,
            count=count,
            slave=self.config.unit_id,
        )
        return _extract_bits(result, f"DI{address}", count)

    def read_snapshot(self) -> CellSnapshot:
        """연속 주소 단위로 묶어 읽고 CellSnapshot으로 변환한다."""

        # HR100~HR107: 공정 상태/heartbeat
        process = self.read_holding(RegisterMap.HR_PROCESS_STATE, 8)

        # HR110~HR114: 장치 상태
        devices = self.read_holding(RegisterMap.HR_DOBOT_STATE, 5)

        # HR120~HR122: 대상 카운터
        counts = self.read_holding(RegisterMap.HR_TARGET_COUNT_TOTAL, 3)

        # HR130~HR131: 컨베이어 속도
        conveyor = self.read_holding(RegisterMap.HR_CONVEYOR_SPEED_SET, 2)

        # HR150: 운전 모드
        operation_mode = self.read_holding(RegisterMap.HR_OPERATION_MODE, 1)[0]

        # IR200~IR203: 측정값
        measurements = self.read_input_registers(RegisterMap.IR_SENSOR_DISTANCE_MM, 4)

        # DI0~DI5: 센서/안전 입력
        inputs = self.read_discrete_inputs(RegisterMap.DI_SENSOR_INFEED, 6)

        return CellSnapshot(
            process_state=process[0],
            process_substate=process[1],
            command_seq=process[2],
            last_ack_seq=process[3],
            error_code=process[4],
            warn_code=process[5],
            heartbeat_pc=process[6],
            heartbeat_plc=process[7],
            dobot_state=devices[0],
            conveyor_state=devices[1],
            camera_state=devices[2],
            turtlebot_state=devices[3],
            robodk_state=devices[4],
            target_total=counts[0],
            target_done=counts[1],
            target_ng=counts[2],
            conveyor_speed_set=conveyor[0],
            conveyor_speed_actual=conveyor[1],
            operation_mode=operation_mode,
            sensor_distance_mm=measurements[0],
            cycle_time_ms=measurements[1],
            alarm_active_code=measurements[2],
            board_temperature=measurements[3],
            sensor_infeed=inputs[0],
            sensor_pick_zone=inputs[1],
            sensor_packaging_zone=inputs[2],
            sensor_outfeed=inputs[3],
            estop=inputs[4],
            door_open=inputs[5],
        )

    # 아래 write 계열은 2단계 제어 검증용이다. 기본 CLI는 read-only 위주로 쓴다.
    def pulse_coil(self, address: int, hold_sec: float = 0.1) -> None:
        self.write_coil(address, True)
        time.sleep(hold_sec)
        self.write_coil(address, False)

    def write_coil(self, address: int, value: bool) -> None:
        result = self.client.write_coil(
            address,
            value,
            slave=self.config.unit_id,
        )
        _raise_if_error(result, f"CO{address} write")

    def write_holding_register(self, address: int, value: int) -> None:
        result = self.client.write_register(
            address,
            value,
            slave=self.config.unit_id,
        )
        _raise_if_error(result, f"HR{address} write")


def _raise_if_error(result, label: str) -> None:  # noqa: ANN001
    if result is None:
        raise ModbusReadError(f"{label} 실패: 응답 없음")
    if hasattr(result, "isError") and result.isError():
        raise ModbusReadError(f"{label} 실패: {result}")


def _extract_registers(result, label: str, expected_count: int) -> list[int]:  # noqa: ANN001
    _raise_if_error(result, label)
    registers = getattr(result, "registers", None)
    if registers is None:
        raise ModbusReadError(f"{label} 실패: registers 필드 없음: {result}")
    if len(registers) < expected_count:
        raise ModbusReadError(
            f"{label} 실패: 요청 {expected_count}개, 응답 {len(registers)}개: {registers}"
        )
    return [int(value) for value in registers[:expected_count]]


def _extract_bits(result, label: str, expected_count: int) -> list[bool]:  # noqa: ANN001
    _raise_if_error(result, label)
    bits = getattr(result, "bits", None)
    if bits is None:
        raise ModbusReadError(f"{label} 실패: bits 필드 없음: {result}")
    if len(bits) < expected_count:
        raise ModbusReadError(
            f"{label} 실패: 요청 {expected_count}개, 응답 {len(bits)}개: {bits}"
        )
    return [bool(value) for value in bits[:expected_count]]


def name_of(mapping: dict[int, str], value: int) -> str:
    return mapping.get(value, f"UNKNOWN({value})")


def format_snapshot_detail(snapshot: CellSnapshot) -> str:
    """read 명령용 상세 출력."""

    lines = [
        f"process_state: {snapshot.process_state} {name_of(PROCESS_STATE_NAMES, snapshot.process_state)}",
        f"process_substate: {snapshot.process_substate}",
        f"command_seq: {snapshot.command_seq}",
        f"last_ack_seq: {snapshot.last_ack_seq}",
        f"error_code: {snapshot.error_code}",
        f"warn_code: {snapshot.warn_code}",
        f"heartbeat_pc: {snapshot.heartbeat_pc}",
        f"heartbeat_plc: {snapshot.heartbeat_plc}",
        f"dobot_state: {snapshot.dobot_state} {name_of(DEVICE_STATE_NAMES, snapshot.dobot_state)}",
        f"conveyor_state: {snapshot.conveyor_state} {name_of(DEVICE_STATE_NAMES, snapshot.conveyor_state)}",
        f"camera_state: {snapshot.camera_state} {name_of(DEVICE_STATE_NAMES, snapshot.camera_state)}",
        f"turtlebot_state: {snapshot.turtlebot_state} {name_of(DEVICE_STATE_NAMES, snapshot.turtlebot_state)}",
        f"robodk_state: {snapshot.robodk_state} {name_of(ROBODK_STATE_NAMES, snapshot.robodk_state)}",
        f"target_total: {snapshot.target_total}",
        f"target_done: {snapshot.target_done}",
        f"target_ng: {snapshot.target_ng}",
        f"conveyor_speed_set: {snapshot.conveyor_speed_set}",
        f"conveyor_speed_actual: {snapshot.conveyor_speed_actual}",
        f"operation_mode: {snapshot.operation_mode} {name_of(OPERATION_MODE_NAMES, snapshot.operation_mode)}",
        f"sensor_distance_mm: {snapshot.sensor_distance_mm}",
        f"cycle_time_ms: {snapshot.cycle_time_ms}",
        f"alarm_active_code: {snapshot.alarm_active_code}",
        f"board_temperature: {snapshot.board_temperature}",
        f"sensor_infeed: {snapshot.sensor_infeed}",
        f"sensor_pick_zone: {snapshot.sensor_pick_zone}",
        f"sensor_packaging_zone: {snapshot.sensor_packaging_zone}",
        f"sensor_outfeed: {snapshot.sensor_outfeed}",
        f"estop: {snapshot.estop}",
        f"door_open: {snapshot.door_open}",
    ]
    return "\n".join(lines)


def format_snapshot_compact(snapshot: CellSnapshot, heartbeat_stale: bool = False) -> str:
    """watch 명령용 한 줄 출력."""

    now = datetime.now().strftime("%H:%M:%S")
    hb_suffix = " STALE" if heartbeat_stale else ""
    return (
        f"[{now}] "
        f"process={name_of(PROCESS_STATE_NAMES, snapshot.process_state)} "
        f"dobot={name_of(DEVICE_STATE_NAMES, snapshot.dobot_state)} "
        f"conveyor={name_of(DEVICE_STATE_NAMES, snapshot.conveyor_state)} "
        f"camera={name_of(DEVICE_STATE_NAMES, snapshot.camera_state)} "
        f"robodk={name_of(ROBODK_STATE_NAMES, snapshot.robodk_state)} "
        f"speed={snapshot.conveyor_speed_actual} "
        f"done={snapshot.target_done}/{snapshot.target_total} "
        f"alarm={snapshot.alarm_active_code} "
        f"hb_plc={snapshot.heartbeat_plc}{hb_suffix}"
    )


def parse_raw_type(raw_type: str) -> str:
    normalized = raw_type.lower()
    if normalized not in {"hr", "ir", "di", "co"}:
        raise argparse.ArgumentTypeError("raw type은 hr, ir, di, co 중 하나여야 합니다.")
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="관통프로젝트 Modbus register client")
    parser.add_argument("--host", default="127.0.0.1", help="Modbus TCP host")
    parser.add_argument("--port", type=int, default=15020, help="Modbus TCP port")
    parser.add_argument("--unit-id", type=int, default=1, help="Modbus unit/slave id")
    parser.add_argument("--timeout-sec", type=float, default=3.0, help="Modbus 요청 timeout")
    parser.add_argument("--debug", action="store_true", help="debug logging 활성화")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("read", help="현재 상태 snapshot을 1회 읽기")

    watch = subparsers.add_parser("watch", help="현재 상태 snapshot을 주기적으로 감시")
    watch.add_argument("--interval-sec", type=float, default=1.0, help="polling interval")
    watch.add_argument(
        "--stale-threshold",
        type=int,
        default=3,
        help="heartbeat_plc가 이 횟수 이상 그대로면 STALE 표시",
    )

    raw = subparsers.add_parser("raw", help="특정 register/input/coil을 raw로 읽기")
    raw.add_argument("--type", required=True, type=parse_raw_type, help="hr, ir, di, co")
    raw.add_argument("--address", required=True, type=int, help="시작 주소")
    raw.add_argument("--count", type=int, default=1, help="읽을 개수")

    pulse = subparsers.add_parser("pulse-coil", help="coil을 짧게 1로 썼다가 0으로 복귀")
    pulse.add_argument("--address", required=True, type=int, help="coil 주소")
    pulse.add_argument("--hold-sec", type=float, default=0.1, help="1 유지 시간")

    write_hr = subparsers.add_parser("write-hr", help="holding register 1개 쓰기")
    write_hr.add_argument("--address", required=True, type=int, help="HR 주소")
    write_hr.add_argument("--value", required=True, type=int, help="쓸 값")

    return parser


def make_config(args: argparse.Namespace) -> ModbusClientConfig:
    return ModbusClientConfig(
        host=args.host,
        port=args.port,
        unit_id=args.unit_id,
        timeout_sec=args.timeout_sec,
        poll_interval_sec=getattr(args, "interval_sec", 1.0),
    )


def configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def run_read(client: ThroughlineModbusClient) -> None:
    snapshot = client.read_snapshot()
    print(format_snapshot_detail(snapshot))


def run_watch(client: ThroughlineModbusClient, interval_sec: float, stale_threshold: int) -> None:
    last_heartbeat: Optional[int] = None
    stale_count = 0

    while True:
        snapshot = client.read_snapshot()
        if last_heartbeat == snapshot.heartbeat_plc:
            stale_count += 1
        else:
            stale_count = 0
        last_heartbeat = snapshot.heartbeat_plc

        print(format_snapshot_compact(snapshot, heartbeat_stale=stale_count >= stale_threshold), flush=True)
        time.sleep(interval_sec)


def run_raw(client: ThroughlineModbusClient, raw_type: str, address: int, count: int) -> None:
    if count <= 0:
        raise ValueError("count는 1 이상이어야 합니다.")

    if raw_type == "hr":
        values: Sequence[int | bool] = client.read_holding(address, count)
        label = "HR"
    elif raw_type == "ir":
        values = client.read_input_registers(address, count)
        label = "IR"
    elif raw_type == "di":
        values = client.read_discrete_inputs(address, count)
        label = "DI"
    elif raw_type == "co":
        values = client.read_coils(address, count)
        label = "CO"
    else:  # argparse에서 이미 검증하지만 타입 체커/안전용으로 남김
        raise ValueError(f"지원하지 않는 raw type: {raw_type}")

    end_address = address + count - 1
    print(f"{label}{address}..{label}{end_address} = {list(values)}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.debug)
    config = make_config(args)

    try:
        with ThroughlineModbusClient(config) as client:
            if args.command == "read":
                run_read(client)
            elif args.command == "watch":
                run_watch(client, args.interval_sec, args.stale_threshold)
            elif args.command == "raw":
                run_raw(client, args.type, args.address, args.count)
            elif args.command == "pulse-coil":
                client.pulse_coil(args.address, args.hold_sec)
                print(f"CO{args.address} pulse 완료")
            elif args.command == "write-hr":
                client.write_holding_register(args.address, args.value)
                print(f"HR{args.address} = {args.value} write 완료")
            else:
                parser.error(f"지원하지 않는 command: {args.command}")
    except KeyboardInterrupt:
        print("\n사용자 중단")
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI에서는 최종 오류 메시지를 짧게 보여준다.
        LOGGER.debug("client 실행 실패", exc_info=True)
        print(f"ERROR: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
