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
