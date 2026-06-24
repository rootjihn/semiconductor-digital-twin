# modbus_bridge_node 인터페이스 전용 구현 초안

이 디렉터리는 실제 Modbus I/O 구현 전, ROS2 작업 컴퓨터에서 노드 이름·topic·service·parameter를 먼저 고정하기 위한 `ament_python` 패키지 초안이다.

```text
throughline_modbus_bridge/
├── config/modbus_bridge.yaml
├── launch/modbus_bridge.launch.py
├── package.xml
├── setup.cfg
├── setup.py
└── throughline_modbus_bridge/
    ├── __init__.py
    └── modbus_bridge_node.py
```

## 현재 구현 범위

구현함:

- node name: `modbus_bridge_node`
- publisher: `/cell/modbus/state`
- service: `/cell/modbus/command`
- service: `/cell/modbus/pulse_coil`
- service: `/cell/modbus/write_register`
- parameter 선언
- launch/config 파일 초안
- interface 확인용 stub state publish

아직 구현하지 않음:

- `pymodbus` TCP client 연결
- mock server/PLC polling
- holding register/discrete input 읽기
- coil pulse write
- holding register write
- reconnect/backoff
- heartbeat stale 판정 실제값
- 공정 판단 로직

공정 판단은 계속 `process_manager_node`가 맡는다.

## 실제 ROS2 컴퓨터에서 배치

예시:

```bash
mkdir -p ~/throughline_ws/src
cp -r Modbus/ros2_interfaces_draft/throughline_interfaces ~/throughline_ws/src/
cp -r Modbus/ros2_nodes_draft/throughline_modbus_bridge ~/throughline_ws/src/
cd ~/throughline_ws
colcon build --packages-select throughline_interfaces throughline_modbus_bridge
source install/setup.bash
```

## interface 확인

```bash
ros2 interface show throughline_interfaces/msg/CellModbusState
ros2 interface show throughline_interfaces/srv/CellCommand
ros2 interface show throughline_interfaces/srv/PulseCoil
ros2 interface show throughline_interfaces/srv/WriteHoldingRegister
```

## 노드 실행

```bash
ros2 launch throughline_modbus_bridge modbus_bridge.launch.py
```

또는:

```bash
ros2 run throughline_modbus_bridge modbus_bridge_node --ros-args \
  -p host:=127.0.0.1 \
  -p port:=15020 \
  -p unit_id:=1 \
  -p poll_hz:=5.0
```

## topic/service 확인

```bash
ros2 topic echo /cell/modbus/state

ros2 service list | grep /cell/modbus
ros2 service type /cell/modbus/command
ros2 service type /cell/modbus/pulse_coil
ros2 service type /cell/modbus/write_register
```

현재는 interface-only stub이므로 service 호출은 성공하더라도 실제 PLC/Modbus write는 하지 않고 `accepted: false` 또는 `ok: false`를 반환한다.

예시:

```bash
ros2 service call /cell/modbus/command throughline_interfaces/srv/CellCommand \
  "{command: 6, command_seq: 1, arg0: 0, arg1: 0}"
```

## 다음 구현 단계

1. `register_client.py`의 읽기/write 구조를 ROS2 node 내부 client 계층으로 이식
2. 주기 polling 결과를 `CellModbusState`로 채워 publish
3. `CellCommand`를 `CO0~CO7` pulse로 매핑
4. `PulseCoil`, `WriteHoldingRegister`에 whitelist와 safety guard 적용
5. mock server와 붙여 `ros2 topic echo`/`ros2 service call`로 실제 검증
