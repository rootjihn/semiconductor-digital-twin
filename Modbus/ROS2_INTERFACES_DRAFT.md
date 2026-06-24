# ROS2 메시지/서비스 인터페이스 초안

이 문서는 관통프로젝트의 `modbus_bridge_node`를 실제 ROS2 작업 컴퓨터에서 만들 때 참고할 인터페이스 초안이다. 아직 구현 파일은 만들지 않고, `.msg`/`.srv` 정의와 패키지 구성만 정리한다.

---

## 1. 조사 근거

확인한 ROS2 공식 문서 기준은 다음과 같다.

| 주제 | 확인 내용 | 출처 |
|---|---|---|
| ROS2 interface 종류 | ROS2 애플리케이션은 보통 topic, service, action 세 종류의 interface로 통신한다. | https://docs.ros.org/en/humble/Concepts/Basic/About-Interfaces.html |
| `.msg` 역할 | `.msg` 파일은 ROS message의 필드를 설명하는 단순 텍스트 파일이고, 여러 언어의 message 소스 생성에 사용된다. | https://docs.ros.org/en/humble/Concepts/Basic/About-Interfaces.html |
| `.srv` 역할 | `.srv` 파일은 request와 response 두 부분으로 구성되며, 두 부분은 `---`로 구분된다. | https://docs.ros.org/en/humble/Concepts/Basic/About-Interfaces.html |
| topic 용도 | topic은 센서 데이터, 로봇 상태 같은 연속 데이터 스트림에 사용한다. | https://docs.ros.org/en/humble/Concepts/Basic/About-Topics.html |
| service 용도 | service는 원격 프로시저 호출이며 빠르게 끝나는 요청/응답에 사용한다. 오래 걸리거나 중단이 필요한 작업은 action을 고려한다. | https://docs.ros.org/en/humble/Concepts/Basic/About-Services.html |
| service server 수 | 같은 service 이름에는 service server가 하나만 있어야 한다. 여러 server가 있으면 어떤 server가 요청을 받을지 정의되지 않는다. | https://docs.ros.org/en/humble/Concepts/Basic/About-Services.html |
| custom interface 패키지 | custom `.msg`/`.srv`는 `msg/`, `srv/` 디렉터리에 두고, `ament_cmake` interface 패키지에서 생성할 수 있다. | https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Custom-ROS2-Interfaces.html |
| 빌드 설정 | `CMakeLists.txt`에서 `rosidl_generate_interfaces(...)`를 사용하고, `package.xml`에 `rosidl_default_generators`, `rosidl_default_runtime`, `rosidl_interface_packages`를 선언한다. | https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Custom-ROS2-Interfaces.html |
| 생성 확인 | 빌드 후 `source install/setup.bash`를 하고 `ros2 interface show 패키지/msg/타입` 또는 `패키지/srv/타입`으로 확인한다. | https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Custom-ROS2-Interfaces.html |

적용 판단:

- `/cell/modbus/state`는 주기적으로 변하는 상태이므로 **topic + `.msg`**가 맞다.
- `conveyor_run`, `reset`, `write_register` 같은 짧은 명령은 빠르게 응답해야 하므로 **service + `.srv`**가 맞다.
- 장시간 동작 자체는 service가 기다리지 않는다. service는 명령 접수 여부만 돌려주고, 진행 상태는 `/cell/modbus/state`에서 본다.
- RoboDK 실제 제어는 `robodk_bridge_node -> Windows robodk_agent.py` 경로를 쓰고, Modbus에는 `HR114~HR117` 요약 상태만 mirror한다.

---

## 2. 권장 ROS2 패키지 구조

실제 작업 컴퓨터에서는 ROS2 workspace 안에 interface 전용 패키지를 먼저 둔다.

```text
throughline_ws/
└── src/
    └── throughline_interfaces/
        ├── CMakeLists.txt
        ├── package.xml
        ├── msg/
        │   └── CellModbusState.msg
        └── srv/
            ├── CellCommand.srv
            ├── PulseCoil.srv
            └── WriteHoldingRegister.srv
```

생성 예시:

```bash
cd ~/throughline_ws/src
ros2 pkg create --build-type ament_cmake --license Apache-2.0 throughline_interfaces
cd throughline_interfaces
mkdir -p msg srv
```

빌드/확인 예시:

```bash
cd ~/throughline_ws
colcon build --packages-select throughline_interfaces
source install/setup.bash
ros2 interface show throughline_interfaces/msg/CellModbusState
ros2 interface show throughline_interfaces/srv/CellCommand
ros2 interface show throughline_interfaces/srv/PulseCoil
ros2 interface show throughline_interfaces/srv/WriteHoldingRegister
```

---

## 3. Topic 설계

### 3-1. `/cell/modbus/state`

- publisher: `modbus_bridge_node`
- subscriber: `process_manager_node`, dashboard bridge, logger
- 목적: PLC/mock server에서 읽은 상태를 ROS2 쪽에 주기 publish
- 권장 주기: 개발 단계 5~10 Hz, 실장비에서는 장비 응답속도에 맞춰 조정

파일:

```text
msg/CellModbusState.msg
```

정의 초안:

```ros
# Cell/PLC/Mock Server 상태 snapshot.
# 값은 Modbus register map v0.1 기준의 16-bit 값을 그대로 반영한다.

std_msgs/Header header

# bridge 연결 상태
bool connected
bool stale_heartbeat
uint32 poll_count
uint32 error_count

# HR100~HR107: process/common state
uint16 process_state
uint16 process_substate
uint16 command_seq
uint16 last_ack_seq
uint16 error_code
uint16 warn_code
uint16 heartbeat_pc
uint16 heartbeat_plc

# HR110~HR117: device summary state
uint16 dobot_state
uint16 conveyor_state
uint16 camera_state
uint16 turtlebot_state
uint16 robodk_state
uint16 robodk_last_cmd
uint16 robodk_last_ack_seq
uint16 robodk_error_code

# HR120~HR122: counters
uint16 target_count_total
uint16 target_count_done
uint16 target_count_ng

# HR130~HR131: conveyor
uint16 conveyor_speed_set
uint16 conveyor_speed_actual

# HR150: operation mode
uint16 operation_mode

# DI0~DI5: discrete inputs
bool sensor_infeed
bool sensor_pick_zone
bool sensor_packaging_zone
bool sensor_outfeed
bool estop_input
bool door_open

# IR200~IR203: input registers
uint16 sensor_distance_mm
uint16 cycle_time_ms
uint16 alarm_active_code
uint16 board_temperature
```

메모:

- `std_msgs/Header`를 쓰므로 interface 패키지의 `CMakeLists.txt`와 `package.xml`에 `std_msgs` 의존성을 넣는다.
- enum 상수는 `.msg` 안에 모두 넣을 수도 있지만, 초기에는 `modbus_map.py`/README 표와 중복이 커진다. 우선 숫자값을 publish하고, dashboard/process_manager 쪽에서 이름 변환표를 쓰는 방식이 단순하다.
- `raw_holding_registers` 같은 원시 배열은 디버깅에는 편하지만 interface를 흐릴 수 있어 기본 초안에서는 제외한다. 필요하면 별도 debug topic으로 분리한다.

---

## 4. Service 설계

### 4-1. `/cell/modbus/command`

- server: `modbus_bridge_node`
- client: `process_manager_node`, dashboard backend
- 목적: 공정 수준의 안전한 추상 명령 요청
- 권장 사용: 일반 운전 로직에서는 이 service를 우선 사용

파일:

```text
srv/CellCommand.srv
```

정의 초안:

```ros
# High-level cell command.
# process_manager_node 또는 dashboard가 사용한다.

uint8 CMD_START=1
uint8 CMD_STOP=2
uint8 CMD_PAUSE=3
uint8 CMD_RESET=4
uint8 CMD_ACK_ALARM=5
uint8 CMD_CONVEYOR_RUN=6
uint8 CMD_CONVEYOR_STOP=7
uint8 CMD_MANUAL_MODE=8

uint8 command
uint16 command_seq
int32 arg0
int32 arg1
---
bool accepted
uint16 last_ack_seq
uint16 error_code
string message
```

`modbus_bridge_node` 내부 매핑:

| `CellCommand.command` | Modbus 동작 |
|---|---|
| `CMD_START` | `CO0` pulse |
| `CMD_STOP` | `CO1` pulse |
| `CMD_PAUSE` | `CO2` pulse |
| `CMD_RESET` | `CO3` pulse |
| `CMD_ACK_ALARM` | `CO4` pulse |
| `CMD_CONVEYOR_RUN` | `CO5` pulse |
| `CMD_CONVEYOR_STOP` | `CO6` pulse |
| `CMD_MANUAL_MODE` | `CO7` pulse 또는 `HR150` 갱신. 실제 정책 확정 필요 |

---

### 4-2. `/cell/modbus/pulse_coil`

- server: `modbus_bridge_node`
- client: 개발/디버깅 도구, dashboard backend
- 목적: 특정 coil 주소를 직접 pulse
- 주의: 일반 공정 로직에서는 `CellCommand.srv`를 우선 사용

파일:

```text
srv/PulseCoil.srv
```

정의 초안:

```ros
# Low-level Modbus coil pulse.
# 개발/디버깅용에 가깝다.

uint16 address
uint16 command_seq
uint16 pulse_ms
---
bool ok
uint16 last_ack_seq
uint16 error_code
string message
```

동작 메모:

- `pulse_ms=0`이면 bridge 기본값을 사용한다.
- 현재 mock server는 command coil을 처리 후 0으로 복귀시킨다. 실제 PLC가 자동 복귀하지 않으면 bridge가 `true -> false`를 책임질지 정책을 정해야 한다.
- 이 service는 짧은 write 요청만 수행하고, 컨베이어가 실제로 움직였는지는 `/cell/modbus/state`의 `conveyor_state`, `conveyor_speed_actual`로 확인한다.

---

### 4-3. `/cell/modbus/write_holding_register`

- server: `modbus_bridge_node`
- client: 개발/디버깅 도구, dashboard backend
- 목적: 특정 holding register를 직접 write
- 주의: 공정 상태 소유권이 섞일 수 있으므로 허용 주소를 whitelist로 제한하는 것이 좋다.

파일:

```text
srv/WriteHoldingRegister.srv
```

정의 초안:

```ros
# Low-level Modbus holding register write.
# 주소 whitelist를 bridge 내부에 둘 것을 권장한다.

uint16 address
uint16 value
uint16 command_seq
---
bool ok
uint16 last_ack_seq
uint16 error_code
string message
```

권장 whitelist 초안:

```text
HR106 heartbeat_pc
HR130 conveyor_speed_set
HR140 manual_command_code
HR141 manual_command_arg0
HR142 manual_command_arg1
HR150 operation_mode
```

`HR100 process_state`, `HR110~HR117 device state`는 일반적으로 bridge/debug service가 마음대로 쓰지 않고, `process_manager_node` 또는 상태 mirror 정책에서만 갱신한다.

---

## 5. `CMakeLists.txt` 초안

```cmake
cmake_minimum_required(VERSION 3.8)
project(throughline_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/CellModbusState.msg"
  "srv/CellCommand.srv"
  "srv/PulseCoil.srv"
  "srv/WriteHoldingRegister.srv"
  DEPENDENCIES std_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
```

---

## 6. `package.xml` 의존성 초안

`<package>` 안에 다음 항목을 포함한다.

```xml
<depend>std_msgs</depend>
<buildtool_depend>rosidl_default_generators</buildtool_depend>
<exec_depend>rosidl_default_runtime</exec_depend>
<member_of_group>rosidl_interface_packages</member_of_group>
```

---

## 7. 이후 `modbus_bridge_node`에서 사용할 이름

`modbus_bridge_node`의 interface-only ROS2 패키지 초안은 [`ros2_nodes_draft/throughline_modbus_bridge`](./ros2_nodes_draft/throughline_modbus_bridge)에 둔다. 이 초안은 topic/service/parameter 이름을 고정하기 위한 골격이며, 실제 Modbus I/O는 아직 구현하지 않는다.

권장 노드/API 이름:

```text
node:     modbus_bridge_node
publish:  /cell/modbus/state              throughline_interfaces/msg/CellModbusState
service:  /cell/modbus/command            throughline_interfaces/srv/CellCommand
service:  /cell/modbus/pulse_coil         throughline_interfaces/srv/PulseCoil
service:  /cell/modbus/write_register     throughline_interfaces/srv/WriteHoldingRegister
```

`process_manager_node` 사용 방식:

```text
1. /cell/modbus/state 구독
2. 상태머신에서 다음 동작 판단
3. conveyor_run/reset 같은 요청은 /cell/modbus/command 호출
4. service 응답은 명령 접수 여부만 본다
5. 실제 장비 상태 변화는 다시 /cell/modbus/state에서 확인한다
```

---

## 8. RoboDK와의 경계

RoboDK는 Windows PC에서 실행하므로 ROS2 adapter를 Windows에 직접 붙이지 않는다.

```text
Ubuntu ROS2
  process_manager_node
    ├─ modbus_bridge_node
    └─ robodk_bridge_node

Windows PC
  robodk_agent.py
    └─ RoboDK Python API
```

Modbus interface가 담는 RoboDK 정보는 요약 상태뿐이다.

```text
HR114 robodk_state
HR115 robodk_last_cmd
HR116 robodk_last_ack_seq
HR117 robodk_error_code
```

실제 RoboDK 명령은 별도 경로를 쓴다.

```text
process_manager_node
-> robodk_bridge_node
-> TCP/JSON 또는 HTTP
-> Windows robodk_agent.py
-> RoboDK API
```

따라서 이 문서의 `.msg`/`.srv`는 Modbus bridge 기준이고, RoboDK 전용 service는 별도 문서에서 정의한다.

---

## 9. 미확정 항목

실제 장비 명세가 나오면 다음을 확정해야 한다.

- Modbus TCP/RTU 여부
- PLC/컨베이어 보드 IP, port, serial 설정
- unit id
- 실제 coil/register 주소
- 0-base/1-base 주소 표기 차이
- 16-bit/32-bit 값 처리
- signed/unsigned 처리
- endianness
- heartbeat timeout 기준
- command ack 기준
- fault/alarm code 목록
