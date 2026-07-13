from pathlib import Path

from robodk import robolink
from robodk.robomath import Mat, pi, rotx, transl


RDK = robolink.Robolink()
RDK.setSimulationSpeed(10)


def robot_by_base(base_name):
    for station_item in RDK.ItemList():
        if station_item.Type() == 2 and station_item.Parent().Valid() and station_item.Parent().Name() == base_name:
            return station_item
    raise Exception("Robot under " + base_name + " not found")


# Robot declaration
RB1_Base = RDK.Item("RB1 Base", 3)
RB2_Base = RDK.Item("RB2 Base", 3)
RB3_Base = RDK.Item("RB3 Base", 3)
RB1 = robot_by_base("RB1 Base")
RB2 = robot_by_base("RB2 Base")
RB3 = robot_by_base("RB3 Base")
AUTONOX = RDK.Item("RBX", 2)
AUTONOX_BASE = RDK.Item("RBX Base", 3)
AUTONOX_TOOL = RDK.Item("Aim Robotics FD 400 Dispenser", 4)

# Conveyor declaration
CON1 = RDK.Item("CON1", 2)
CON2 = RDK.Item("CON2", 2)
CON5 = robot_by_base("CON5 Base")

# Conveyor frame declaration
CONV1 = RDK.Item("CONV1", 3)
CONV2 = RDK.Item("CONV2", 3)

# Process object declaration
Wafer_Cutting_Box = RDK.Item("Wafer_Cutting_Box", 5)

# Tool declaration
Tool1 = RDK.Item("Tool1", 4)
Tool2 = RDK.Item("Tool2", 4)
Tool3 = RDK.Item("Tool3", 4)
RB3.setPoseTool(Tool3)
if AUTONOX.Valid() and AUTONOX_TOOL.Valid():
    AUTONOX.setPoseFrame(AUTONOX_BASE)
    AUTONOX.setPoseTool(AUTONOX_TOOL)

# Wafer declaration
Wafer1 = RDK.Item("Wafer1", 5)
Wafer2 = RDK.Item("Wafer2", 5)
Wafer3 = RDK.Item("Wafer3", 5)
Wafer4 = RDK.Item("Wafer4", 5)
Wafer5 = RDK.Item("Wafer5", 5)
Wafer6 = RDK.Item("Wafer6", 5)
Wafer7 = RDK.Item("Wafer7", 5)
Wafer8 = RDK.Item("Wafer8", 5)

WAFER_Total = [
    "Wafer1",
    "Wafer2",
    "Wafer3",
    "Wafer4",
    "Wafer5",
    "Wafer6",
    "Wafer7",
    "Wafer8",
]

WAFER_Items = [
    Wafer1,
    Wafer2,
    Wafer3,
    Wafer4,
    Wafer5,
    Wafer6,
    Wafer7,
    Wafer8,
]

PICK_JOINTS = [-84.025012, -3.864646, 93.723260, 0.141386, 90.000000, 84.025012]
PLACE_JOINTS = [6.878823, 11.073185, 77.769176, 1.157639, 90.000000, -6.878823]
TRAY_PICK_JOINTS = [16.318388, 6.239284, 132.437571, -48.676855, 90.000000, -16.318388]
TRAY_PLACE_JOINTS = [-105.642558, 31.334877, 78.812888, -20.147764, 90.000000, 105.642558]
RB2_WAIT_JOINTS = [16.318388, -11.366844, 94.170554, 7.196290, 90.000000, -16.318388]
ONEDIE_PICK_JOINTS = [101.566384, 8.952323, 110.595080, -29.547403, 90.000000, -101.566384]
RB3_WAIT_JOINTS = [177.802177, 1.938327, 83.083117, 4.978556, 90.000000, -177.802177]
TRAY_PICK_POSE = Mat([
    [0.000000, -1.000000, -0.000000, -1300.208000],
    [1.000000, 0.000000, -0.000000, 7068.951000],
    [-0.000000, 0.000000, 1.000000, 1015.400000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
DIE_TRAY_TOOL2_POSE = Mat([
    [1.000000, -0.000000, 0.000000, 0.000000],
    [0.000000, -1.000000, -0.000000, 0.000000],
    [-0.000000, 0.000000, -1.000000, 117.500000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
ONEDIE_TOOL3_POSE = Mat([
    [1.000000, 0.000000, -0.000000, 0.000000],
    [0.000000, 1.000000, -0.000000, 0.000000],
    [0.000000, -0.000000, 1.000000, 4.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])

CONVEYOR_STEP = 500
CON2_PREFILL_COUNT = len(WAFER_Items)
WAFER_FEED_INDEX = len(WAFER_Items)
WAFER_START_Z = 750
WAFER_FEED_POSE = Mat([
    [0.000000, 1.000000, 0.000000, -2390.000000],
    [-1.000000, 0.000000, 0.000000, 340.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])

ROBODK_DIR = Path(__file__).resolve().parents[1]
OBJECT_DIR = ROBODK_DIR / "assets" / "Object"

WAFER_FILE = OBJECT_DIR / "Wafer.step"
DIE_FILE = OBJECT_DIR / "DIE.step"
DIE_TRAY_FILE = OBJECT_DIR / "DIE_Tray.step"
ONEDIE_FILE = OBJECT_DIR / "ONEDIE.step"
SEMICONDUCTOR_FILE = OBJECT_DIR / "semiconductor.step"

DIE_Y = 212.132
APPROACH_DISTANCE = 150
TRAY_APPROACH_DISTANCE = APPROACH_DISTANCE * 3
RB3_ONEDIE_APPROACH_Z_OFFSET = 100
AUTONOX_APPROACH_Z_OFFSET = 40
AUTONOX_WAIT_Z = -386.0
AUTONOX_CON5_START_COUNT = 2
RB3_ONEDIE_WORK_Z = 260.877258
ONEDIE_Z_OFFSET = 3.5
RB3_PICK_POINTS = [
    (-17.5, 37.5, 0.0), (17.5, 37.5, 0.0),
    (-52.5, 12.5, 0.0), (-17.5, 12.5, 0.0), (17.5, 12.5, 0.0), (52.5, 12.5, 0.0),
    (-52.5, -12.5, 0.0), (-17.5, -12.5, 0.0), (17.5, -12.5, 0.0), (52.5, -12.5, 0.0),
    (-17.5, -37.5, 0.0), (17.5, -37.5, 0.0),
]
ONEDIE_SLOT_OFFSETS = [
    [-100.0, 16.5],
    [-60.0, 16.5],
    [-20.0, 16.5],
    [20.0, 16.5],
    [60.0, 16.5],
    [100.0, 16.5],
    [-100.0, -16.5],
    [-60.0, -16.5],
    [-20.0, -16.5],
    [20.0, -16.5],
    [60.0, -16.5],
    [100.0, -16.5],
]
AUTONOX_WAIT_JOINTS = [-7.947787, 4.126018, -21.287847]
AUTONOX_WAIT_POSE = Mat([
    [1.000000, 0.000000, 0.000000, -2.000000],
    [0.000000, -1.000000, -0.000000, 77.000000],
    [0.000000, 0.000000, -1.000000, -386.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
SEMICONDUCTOR_BASE_POSE = Mat([
    [1.000000, 0.000000, 0.000000, -100.000000],
    [0.000000, 1.000000, -0.000000, -16.500000],
    [0.000000, -0.000000, 1.000000, 4.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
SEMI_TRAY_POINTS_OFFSET = [
    (18.0, -114.0, -446.0),
    (18.0, -74.0, -446.0),
    (18.0, -34.0, -446.0),
    (18.0, 6.0, -446.0),
    (18.0, 46.0, -446.0),
    (18.0, 86.0, -446.0),
    (-15.0, 86.0, -446.0),
    (-15.0, 46.0, -446.0),
    (-15.0, 6.0, -446.0),
    (-15.0, -34.0, -446.0),
    (-15.0, -74.0, -446.0),
    (-15.0, -114.0, -446.0),
]
SEMI_SMALL_SQUARE_POINTS_OFFSET = [
    (10.0, -12.0, 0.0),
    (10.0, -9.0, 0.0),
    (10.0, -6.0, 0.0),
    (10.0, -3.0, 0.0),
    (10.0, 0.0, 0.0),
    (10.0, 3.0, 0.0),
    (10.0, 6.0, 0.0),
    (10.0, 9.0, 0.0),
    (10.0, 12.0, 0.0),
    (-10.0, -12.0, 0.0),
    (-10.0, -9.0, 0.0),
    (-10.0, -6.0, 0.0),
    (-10.0, -3.0, 0.0),
    (-10.0, 0.0, 0.0),
    (-10.0, 3.0, 0.0),
    (-10.0, 6.0, 0.0),
    (-10.0, 9.0, 0.0),
    (-10.0, 12.0, 0.0),
]
SEMICONDUCTOR_SLOT_OFFSETS = [
    (-100.0, -16.5, 0.0), (-60.0, -16.5, 0.0), (-20.0, -16.5, 0.0),
    (20.0, -16.5, 0.0), (60.0, -16.5, 0.0), (100.0, -16.5, 0.0),
    (-100.0, 16.5, 0.0), (-60.0, 16.5, 0.0), (-20.0, 16.5, 0.0),
    (20.0, 16.5, 0.0), (60.0, 16.5, 0.0), (100.0, 16.5, 0.0),
]


def numeric_suffix(name, prefix):
    if not name.startswith(prefix):
        return None

    suffix = name[len(prefix):]
    return int(suffix) if suffix.isdigit() else None


def prefill_wafer_feed():
    CON1.MoveJ([0])
    CON2.MoveJ([0])
    CON5.MoveJ([0])

    for index, wafer in enumerate(WAFER_Items):
        spawn_wafer_at_feed(index)
        CON2.MoveJ([index * CONVEYOR_STEP])
        CON2.MoveJ([(index + 1) * CONVEYOR_STEP])


def spawn_wafer_at_feed(index):
    wafer = get_wafer(index)
    set_wafer_feed_position(wafer, index)
    return wafer


def wafer_feed_pose(index):
    rows = [row[:] for row in WAFER_FEED_POSE.Rows()]
    rows[0][3] = rows[0][3] - (index * CONVEYOR_STEP)
    return Mat(rows)


def set_wafer_feed_position(wafer, index):
    wafer.setParentStatic(CON2)
    wafer.setPose(wafer_feed_pose(index))


def clear_existing_dies():
    for station_item in RDK.ItemList():
        name = station_item.Name()
        if name == "DIE" or numeric_suffix(name, "DIE") is not None:
            station_item.Delete()


def clear_existing_die_tray():
    for station_item in RDK.ItemList():
        name = station_item.Name()
        if name == "DIE_Tray" or numeric_suffix(name, "DIE_TRAY") is not None:
            station_item.Delete()


def clear_existing_onedies():
    for station_item in RDK.ItemList():
        if station_item.Name().startswith("ONEDIE"):
            station_item.Delete()


def clear_existing_semis():
    for station_item in RDK.ItemList():
        name = station_item.Name()
        if name == "SEMI_CURRENT" or name.startswith("semi"):
            station_item.Delete()


def clear_generated_wafers():
    for station_item in RDK.ItemList():
        wafer_index = numeric_suffix(station_item.Name(), "Wafer")
        if wafer_index is not None:
            station_item.Delete()


def pose_with_z_offset(pose, z_offset):
    rows = [row[:] for row in pose.Rows()]
    rows[2][3] = rows[2][3] + z_offset
    return Mat(rows)


def pose_with_world_z(pose, world_z):
    rows = [row[:] for row in pose.Rows()]
    rows[2][3] = world_z
    return Mat(rows)


def pose_with_local_z(pose, local_z):
    rows = [row[:] for row in pose.Rows()]
    rows[2][3] = local_z
    return Mat(rows)


def pose_with_local_offset(pose, x_offset, y_offset, z_offset):
    rows = [row[:] for row in pose.Rows()]
    rows[0][3] = rows[0][3] + x_offset
    rows[1][3] = rows[1][3] + y_offset
    rows[2][3] = rows[2][3] + z_offset
    return Mat(rows)


def nearest_joints(joints, seed_joints):
    values = joints.list()
    seed = seed_joints.list() if hasattr(seed_joints, "list") else seed_joints
    adjusted = []
    for value, seed_value in zip(values, seed):
        while value - seed_value > 180:
            value = value - 360
        while value - seed_value < -180:
            value = value + 360
        adjusted.append(value)
    return adjusted


def movej_pose(robot, pose, seed_joints):
    joints = robot.SolveIK(pose, seed_joints)
    joint_values = joints.list()
    seed_values = seed_joints.list() if hasattr(seed_joints, "list") else seed_joints
    if not joint_values or len(joint_values) < len(seed_values):
        raise Exception("Target cannot be reached")
    adjusted_joints = nearest_joints(joints, seed_joints)
    robot.MoveJ(adjusted_joints)
    return adjusted_joints


def joints_for_pose(robot, pose, seed_joints):
    joints = robot.SolveIK(pose, seed_joints)
    joint_values = joints.list()
    seed_values = seed_joints.list() if hasattr(seed_joints, "list") else seed_joints
    if not joint_values or len(joint_values) < len(seed_values):
        raise Exception("Target cannot be reached")
    return nearest_joints(joints, seed_joints)


def onedie_slot_pose(tray_pose, slot_num):
    dx, dy = ONEDIE_SLOT_OFFSETS[slot_num]
    return tray_pose * transl(dx, dy, ONEDIE_Z_OFFSET) * rotx(pi)


def tool3_pose_for_onedie(onedie_pose):
    tool_z = RB3.PoseTool().Pos()[2]
    onedie_z = ONEDIE_TOOL3_POSE.Pos()[2]
    return pose_with_z_offset(onedie_pose, tool_z - onedie_z)


def rb3_pick_pose(pick_index):
    base_pick_pose = pose_with_local_z(RB3.SolveFK(ONEDIE_PICK_JOINTS), RB3_ONEDIE_WORK_Z)
    x_offset, y_offset, z_offset = RB3_PICK_POINTS[pick_index % len(RB3_PICK_POINTS)]
    return pose_with_local_offset(base_pick_pose, x_offset, y_offset, z_offset)


def get_die(num):
    die_name = "DIE" + str(num + 1)
    die = RDK.Item(die_name, 5)

    if die.Valid():
        return die

    die = RDK.AddFile(str(DIE_FILE))
    if not die.Valid():
        raise Exception("DIE file load failed: " + str(DIE_FILE))

    die.setName(die_name)
    return die


def get_wafer(num):
    wafer_name = "Wafer" + str(num + 1)
    wafer = RDK.Item(wafer_name, 5)

    if wafer.Valid():
        return wafer

    wafer = RDK.AddFile(str(WAFER_FILE))
    if not wafer.Valid():
        raise Exception("Wafer file load failed: " + str(WAFER_FILE))

    wafer.setName(wafer_name)
    set_wafer_feed_position(wafer, num)
    return wafer


def replace_wafer_with_die(num):
    wafer = get_wafer(num)
    die = get_die(num)
    wafer_local_pose = wafer.PoseWrt(CON1)
    x, y, z = wafer_local_pose.Pos()
    wafer_local_pose.setPos([x, DIE_Y, z])

    die.setParentStatic(CON1)
    die.setPose(wafer_local_pose)

    wafer.setParentStatic(Wafer_Cutting_Box)
    wafer.setPoseAbs(Wafer_Cutting_Box.PoseAbs() * transl(0, 0, 100 + (num * 30)))


def create_die_tray_at_tool(num):
    tray_name = "DIE_TRAY" + str(num + 1)
    tray = RDK.AddFile(str(DIE_TRAY_FILE))
    if not tray.Valid():
        raise Exception("DIE_Tray file load failed: " + str(DIE_TRAY_FILE))

    tray.setName(tray_name)
    tray.setPoseAbs(TRAY_PICK_POSE)
    return tray


def create_onedie_at_tool(tray_num, slot_num):
    onedie_name = "ONEDIE" + str(tray_num + 1) + "_" + str(slot_num + 1)
    onedie = RDK.AddFile(str(ONEDIE_FILE))
    if not onedie.Valid():
        raise Exception("ONEDIE file load failed: " + str(ONEDIE_FILE))

    onedie.setName(onedie_name)
    onedie.setPoseAbs(Tool3.PoseAbs() * ONEDIE_TOOL3_POSE)
    return onedie


def place_onedie(tray_num, slot_num, tray_pose):
    pick_index = (tray_num * len(ONEDIE_SLOT_OFFSETS)) + slot_num
    pick_pose = rb3_pick_pose(pick_index)
    pick_approach_pose = pose_with_local_z(
        pick_pose,
        RB3_ONEDIE_WORK_Z + RB3_ONEDIE_APPROACH_Z_OFFSET,
    )
    RB3.MoveL(pick_approach_pose)
    RB3.MoveL(pick_pose)

    onedie = create_onedie_at_tool(tray_num, slot_num)
    onedie.setParentStatic(Tool3)
    onedie.setPose(ONEDIE_TOOL3_POSE)
    RB3.MoveL(pick_approach_pose)

    place_pose = onedie_slot_pose(tray_pose, slot_num)
    approach_pose = pose_with_z_offset(place_pose, RB3_ONEDIE_APPROACH_Z_OFFSET)
    rb3_approach_pose = RB3_Base.PoseAbs().inv() * tool3_pose_for_onedie(approach_pose)
    rb3_place_pose = RB3_Base.PoseAbs().inv() * tool3_pose_for_onedie(place_pose)
    rb3_place_pose = pose_with_local_z(rb3_place_pose, RB3_ONEDIE_WORK_Z)
    rb3_approach_pose = pose_with_local_z(
        rb3_place_pose,
        RB3_ONEDIE_WORK_Z + RB3_ONEDIE_APPROACH_Z_OFFSET,
    )
    RB3.MoveL(rb3_approach_pose)
    RB3.MoveL(rb3_place_pose)
    onedie.setParentStatic(CON1)
    onedie.setPoseAbs(place_pose)
    RB3.MoveL(rb3_approach_pose)


def fill_die_tray(tray_num, die_tray):
    tray_pose = die_tray.PoseAbs()
    for slot_num in range(len(ONEDIE_SLOT_OFFSETS)):
        place_onedie(tray_num, slot_num, tray_pose)
    RB3.MoveJ(RB3_WAIT_JOINTS)
    die = RDK.Item("DIE" + str(tray_num + 1), 5)
    if die.Valid():
        die.Delete()


def move_conveyor(conveyor, step_mm):
    joints = conveyor.Joints().list()
    current = joints[0] if joints else 0
    conveyor.MoveJ([current + step_mm])


def tray_move_param(tray_number):
    return "AUTONOX_TRAY_MOVE_COUNT_" + str(tray_number)


def advance_con5_with_con1():
    con5_trays = []
    for station_item in RDK.ItemList():
        tray_number = numeric_suffix(station_item.Name(), "DIE_TRAY")
        if (
            tray_number is not None
            and station_item.Parent().Valid()
            and station_item.Parent().Name() == CON5.Name()
        ):
            con5_trays.append((tray_number, station_item))

    if not con5_trays:
        return

    move_conveyor(CON5, CONVEYOR_STEP)
    for tray_number, station_item in con5_trays:
        move_count = int(RDK.getParam(tray_move_param(tray_number)) or "0")
        RDK.setParam(tray_move_param(tray_number), str(move_count + 1))


def apply_con5_local_x_delta(item_to_move, x_delta):
    item_to_move.setPose(
        pose_with_local_offset(
            item_to_move.Pose(),
            x_delta,
            0,
            0,
        )
    )


def con5_tray_tail_x(exclude_tray_number):
    tray_positions = []
    for station_item in RDK.ItemList():
        tray_number = numeric_suffix(station_item.Name(), "DIE_TRAY")
        if (
            tray_number is not None
            and tray_number != exclude_tray_number
            and station_item.Parent().Valid()
            and station_item.Parent().Name() == CON5.Name()
        ):
            tray_positions.append(station_item.Pose().Pos()[0])

    if not tray_positions:
        return None

    return min(tray_positions)


def move_completed_tray_to_con5(tray_num):
    tray_number = tray_num + 1
    die_tray = RDK.Item("DIE_TRAY" + str(tray_num + 1), 5)
    if die_tray.Valid():
        die_tray.setParentStatic(CON5)
        tail_x = con5_tray_tail_x(tray_number)
        x_delta = 0 if tail_x is None else (tail_x - CONVEYOR_STEP) - die_tray.Pose().Pos()[0]
        apply_con5_local_x_delta(die_tray, x_delta)
    else:
        x_delta = 0

    for slot_num in range(len(ONEDIE_SLOT_OFFSETS)):
        onedie = RDK.Item("ONEDIE" + str(tray_num + 1) + "_" + str(slot_num + 1), 5)
        if onedie.Valid():
            onedie.setParentStatic(CON5)
            apply_con5_local_x_delta(onedie, x_delta)

    RDK.setParam(tray_move_param(tray_number), "0")


def move_con5_payload(step_mm):
    return


def autonox_tcp_pose_from_xyz(x, y, z):
    rows = [row[:] for row in AUTONOX_WAIT_POSE.Rows()]
    rows[0][3] = x
    rows[1][3] = y
    rows[2][3] = z
    return Mat(rows)


def autonox_wait_pose():
    return AUTONOX_WAIT_POSE


def move_autonox_to_wait():
    if AUTONOX.Valid():
        AUTONOX.MoveJ(AUTONOX_WAIT_JOINTS)


def autonox_tray_center_pose(stage_index):
    tray_x, tray_y, tray_z = SEMI_TRAY_POINTS_OFFSET[stage_index]
    return autonox_tcp_pose_from_xyz(tray_x, tray_y, tray_z)


def semiconductor_place_pose(stage_index):
    slot_x, slot_y, slot_z = SEMICONDUCTOR_SLOT_OFFSETS[stage_index]
    return pose_with_local_offset(SEMICONDUCTOR_BASE_POSE, slot_x + 100.0, slot_y + 16.5, slot_z)


def semiconductor_slot_index(stage_index):
    if stage_index < 6:
        return stage_index
    return len(SEMICONDUCTOR_SLOT_OFFSETS) - 1 - (stage_index - 6)


def create_autonox_semiconductor(tray_number, target_tray, stage_index):
    slot_index = semiconductor_slot_index(stage_index)
    semiconductor_name = "semiconductor" + str(tray_number) + "_" + str(stage_index + 1)
    existing = RDK.Item(semiconductor_name, 5)
    if existing.Valid():
        existing.Delete()

    semiconductor = RDK.AddFile(str(SEMICONDUCTOR_FILE))
    if not semiconductor.Valid():
        raise Exception("semiconductor file load failed: " + str(SEMICONDUCTOR_FILE))

    semiconductor.setName(semiconductor_name)
    semiconductor.setParentStatic(target_tray)
    semiconductor.setPose(semiconductor_place_pose(slot_index))
    return semiconductor


def autonox_stage_pose(stage_index, point_offset):
    tray_x, tray_y, tray_z = SEMI_TRAY_POINTS_OFFSET[stage_index]
    point_x, point_y, point_z = point_offset
    return autonox_tcp_pose_from_xyz(tray_x + point_x, tray_y + point_y, tray_z + point_z)


def move_autonox_to_process_point(target_pose):
    if not AUTONOX.Valid():
        raise Exception("Autonox robot not found")

    approach_pose = pose_with_z_offset(target_pose, AUTONOX_APPROACH_Z_OFFSET)
    seed_joints = AUTONOX.Joints()
    movej_pose(AUTONOX, approach_pose, seed_joints)
    AUTONOX.MoveL(target_pose)
    try:
        AUTONOX.MoveL(approach_pose)
    except robolink.TargetReachError:
        movej_pose(AUTONOX, approach_pose, AUTONOX.Joints())


def run_autonox_tray_stage(target_tray, stage_index):
    for point_offset in SEMI_SMALL_SQUARE_POINTS_OFFSET:
        move_autonox_to_process_point(autonox_stage_pose(stage_index, point_offset))


def next_autonox_tray():
    last_processed_tray = int(RDK.getParam("AUTONOX_LAST_PROCESSED_TRAY") or "0")
    all_trays = []
    unprocessed_trays = []
    for station_item in RDK.ItemList():
        tray_index = numeric_suffix(station_item.Name(), "DIE_TRAY")
        if (
            tray_index is not None
            and station_item.Parent().Valid()
            and station_item.Parent().Name() == CON5.Name()
        ):
            all_trays.append((tray_index, station_item))
            move_count = int(RDK.getParam(tray_move_param(tray_index)) or "0")
            if tray_index > last_processed_tray and move_count >= 2:
                unprocessed_trays.append((tray_index, station_item))

    if len(all_trays) < AUTONOX_CON5_START_COUNT or not unprocessed_trays:
        return None, None

    unprocessed_trays.sort(key=lambda item: item[0])
    return unprocessed_trays[0]


def autonox_semi_process_update():
    tray_number, target_tray = next_autonox_tray()
    if target_tray is None:
        move_autonox_to_wait()
        return

    for stage_index in range(len(SEMI_TRAY_POINTS_OFFSET)):
        run_autonox_tray_stage(target_tray, stage_index)
        create_autonox_semiconductor(tray_number, target_tray, stage_index)

    move_autonox_to_wait()
    move_con5_payload(CONVEYOR_STEP)
    RDK.setParam("AUTONOX_TRAY_COUNT", "0")
    RDK.setParam("AUTONOX_LAST_PROCESSED_TRAY", str(tray_number))


def place_die_tray_on_con1(num):
    pick_pose = RB2.SolveFK(TRAY_PICK_JOINTS)
    pick_approach_pose = pose_with_z_offset(pick_pose, TRAY_APPROACH_DISTANCE)
    pick_approach_joints = movej_pose(RB2, pick_approach_pose, TRAY_PICK_JOINTS)
    RB2.MoveL(pick_pose)

    die_tray = create_die_tray_at_tool(num)
    die_tray.setParentStatic(Tool2)
    die_tray.setPose(DIE_TRAY_TOOL2_POSE)
    RB2.MoveL(pick_approach_pose)

    place_pose = RB2.SolveFK(TRAY_PLACE_JOINTS)
    place_approach_pose = pose_with_z_offset(place_pose, TRAY_APPROACH_DISTANCE)
    movej_pose(RB2, place_approach_pose, TRAY_PLACE_JOINTS)
    RB2.MoveL(place_pose)

    die_ref = RDK.Item("DIE1", 5)
    die_z = die_ref.PoseAbs().Pos()[2] if die_ref.Valid() else WAFER_START_Z
    tray_pose = pose_with_world_z(die_tray.PoseAbs(), die_z)

    Tool2.DetachAll(CON1)
    die_tray.setParentStatic(CON1)
    die_tray.setPoseAbs(tray_pose)
    RB2.MoveL(place_approach_pose)
    RB2.MoveJ(RB2_WAIT_JOINTS)
    return die_tray


def job1(num):
    wafer = get_wafer(num)
    RB1.MoveJ(PICK_JOINTS)

    RB1.MoveL(RB1.Pose() * transl(0, 0, 270))
    Tool1.AttachClosest(wafer.Name(), 2000)
    RB1.MoveL(RB1.Pose() * transl(0, 0, -270))

    spawn_wafer_at_feed(num + WAFER_FEED_INDEX)
    job2(num)

    RB1.MoveJ(PLACE_JOINTS)
    RB1.MoveL(RB1.Pose() * transl(0, 0, 270))
    place_pose = wafer.PoseAbs()
    Tool1.DetachAll(CON1)
    wafer.setParentStatic(CON1)
    wafer.setPoseAbs(place_pose)
    RB1.MoveL(RB1.Pose() * transl(0, 0, -270))


def job2(num):
    start = (num + CON2_PREFILL_COUNT) * CONVEYOR_STEP
    CON2.MoveJ([start])
    CON2.MoveJ([start + CONVEYOR_STEP])


def job3(num):
    start = num * CONVEYOR_STEP
    CON1.MoveJ([start])
    CON1.MoveJ([start + CONVEYOR_STEP])
    advance_con5_with_con1()


clear_existing_dies()
clear_existing_die_tray()
clear_existing_onedies()
clear_existing_semis()
clear_generated_wafers()
RDK.setParam("AUTONOX_TRAY_COUNT", "0")
RDK.setParam("AUTONOX_LAST_PROCESSED_TRAY", "0")
move_autonox_to_wait()
prefill_wafer_feed()

for i in range(len(WAFER_Total)):
    job1(i)
    if i < len(WAFER_Total) - 1:
        job3(i)
        if i >= 3:
            replace_wafer_with_die(i - 3)

tray_index = 0
while True:
    die_tray = place_die_tray_on_con1(tray_index)
    job3(7 + tray_index)
    replace_wafer_with_die(tray_index + 4)
    fill_die_tray(tray_index, die_tray)
    if tray_index >= 4:
        move_completed_tray_to_con5(tray_index - 4)
        autonox_semi_process_update()
    job1(tray_index + len(WAFER_Total))
    tray_index = tray_index + 1
