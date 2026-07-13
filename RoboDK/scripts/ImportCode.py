from pathlib import Path

from robodk import robolink
from robodk.robomath import Mat


RDK = robolink.Robolink()
ROBODK_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROBODK_DIR / "assets"

STATION_DIR = ROBODK_DIR / "stations"
AGV_DIR = ASSETS_DIR / "AGV"
CONVEY_DIR = ASSETS_DIR / "Convey"
OBJECT_DIR = ASSETS_DIR / "Object"
ROBOT_DIR = ASSETS_DIR / "Robot"
TOOL_DIR = ASSETS_DIR / "Tool"


def pose(values):
    return Mat(values)


def item(name, item_type=None):
    obj = RDK.Item(name, item_type) if item_type is not None else RDK.Item(name)
    if not obj.Valid():
        raise Exception("RoboDK item not found: " + name)
    return obj


def item_or_load(name, item_type, file_path):
    obj = RDK.Item(name, item_type)
    if obj.Valid():
        return obj

    obj = RDK.AddFile(str(file_path))
    if not obj.Valid():
        raise Exception("RoboDK item not found and file load failed: " + name)

    obj.setName(name)
    return obj


def robot_base_or_load(base_name, robot_name, file_path):
    base = RDK.Item(base_name, 3)
    if base.Valid():
        return base

    robot = RDK.AddFile(str(file_path))
    if not robot.Valid():
        raise Exception("Robot file load failed: " + str(file_path))

    robot.setName(robot_name)
    base = robot.Parent()
    if base.Valid():
        base.setName(base_name)
        return base

    raise Exception("Robot base not found after load: " + robot_name)


def rename_item(old_name, new_name, item_type=None):
    obj = RDK.Item(new_name, item_type) if item_type is not None else RDK.Item(new_name)
    if obj.Valid():
        return obj

    obj = RDK.Item(old_name, item_type) if item_type is not None else RDK.Item(old_name)
    if obj.Valid():
        obj.setName(new_name)
        return obj

    return obj


def load_tool(tool_name, robot, file_name):
    existing_tool = RDK.Item(tool_name, 4)
    if existing_tool.Valid():
        existing_tool.Delete()

    tool = RDK.AddFile(str(TOOL_DIR / file_name), robot)
    if not tool.Valid():
        raise Exception("Tool file load failed: " + file_name)

    tool.setName(tool_name)
    return tool


def robot_by_base(base_name):
    for station_item in RDK.ItemList():
        if station_item.Type() == 2 and station_item.Parent().Valid() and station_item.Parent().Name() == base_name:
            return station_item
    raise Exception("Robot under " + base_name + " not found")


def robot_by_base_as(base_name, robot_name):
    robot = robot_by_base(base_name)
    robot.setName(robot_name)
    return robot


def normalize_robot_arm_table_names():
    tables = [station_item for station_item in RDK.ItemList() if station_item.Name() == "RobotArm_Table2"]
    if len(tables) > 1:
        tables.sort(key=lambda station_item: station_item.PoseAbs().Pos()[1], reverse=True)
        tables[0].setName("RobotArm_Table2")
        tables[1].setName("RobotArm_Table3")


def set_parent_abs(obj, parent, abs_pose):
    obj.setParentStatic(parent)
    obj.setPoseAbs(pose(abs_pose))


def set_parent_local(obj, parent, local_pose):
    obj.setParentStatic(parent)
    obj.setPose(pose(local_pose))


def numeric_suffix(name, prefix):
    if not name.startswith(prefix):
        return None

    suffix = name[len(prefix):]
    return int(suffix) if suffix.isdigit() else None


def clear_existing_wafers():
    delete_names = []
    for station_item in RDK.ItemList():
        if station_item.Valid() and numeric_suffix(station_item.Name(), "Wafer") is not None:
            delete_names.append(station_item.Name())

    for name in delete_names:
        station_item = RDK.Item(name, 5)
        if station_item.Valid():
            station_item.Delete()


def clear_process_outputs():
    delete_names = []
    for station_item in RDK.ItemList():
        if not station_item.Valid():
            continue

        name = station_item.Name()
        if (
            name == "DIE"
            or name == "DIE_Tray"
            or numeric_suffix(name, "DIE") is not None
            or numeric_suffix(name, "DIE_TRAY") is not None
            or name.startswith("ONEDIE")
            or name == "SEMI_CURRENT"
            or name.startswith("semi")
            or name.startswith("semiconductor")
        ):
            delete_names.append(name)

    for name in delete_names:
        station_item = RDK.Item(name, 5)
        if station_item.Valid():
            station_item.Delete()


normalize_robot_arm_table_names()
rename_item("autonox Robotics DELTA RL3-600-1kg (A_00072-02) Base", "RBX Base", 3)
rename_item("autonox Robotics DELTA RL3-600-1kg (A_00072-02)", "RBX", 2)

# Items
Station = item("Penetrate_PJT", 1)
Die_Tray_Dummy = item('DIE_Tray_Dummy', 5)
Wafer_Cutting_Box = item('Wafer_Cutting_Box', 5)
Floor_Plate = item('Floor_Plate', 5)
RobotArm_Table = item('RobotArm_Table', 5)
RobotArm_Table2 = item_or_load('RobotArm_Table2', 5, OBJECT_DIR / "RobotArm_Table.step")
RobotArm_Table3 = item_or_load('RobotArm_Table3', 5, OBJECT_DIR / "RobotArm_Table.step")
RobotArm_Table4 = item_or_load('RobotArm_Table4', 5, OBJECT_DIR / "RobotArm_Table.step")
Conveyor_Table = item('Conveyor_Table', 5)
Conveyor_Table2 = item('Conveyor_Table2', 5)
Conveyor_Table3 = item('Conveyor_Table3', 5)
Conveyor_Table4 = item('Conveyor_Table4', 5)
pre_Wafer_machine = item('pre_Wafer_machine', 5)
RBX_Base = robot_base_or_load('RBX Base', 'RBX', ROBOT_DIR / "RBX.robot")
RB1_Base = item('RB1 Base', 3)
RB2_Base = item('RB2 Base', 3)
RB3_Base = item('RB3 Base', 3)
AGV1_Base = robot_base_or_load('AGV1 Base', 'AGV1', AGV_DIR / "AGV1.robot")
RB4_Base = robot_base_or_load('RB4 Base', 'RB4', ROBOT_DIR / "RB1.robot")
CONV1 = item('CONV1', 3)
CON1_Base = item('CON1 Base', 3)
CONV2 = item('CONV2', 3)
CON2_Base = item('CON2 Base', 3)
CONV3 = item('CONV3', 3)
CON3_Base = item('CON3 Base', 3)
CONV4 = item('CONV4', 3)
CON4_Base = item('CON4 Base', 3)
CONV5 = item('CONV5', 3)
CON5_Base = item('CON5 Base', 3)
CONV6 = item('CONV6', 3)
CON6_Base = item('CON6 Base', 3)
CON1 = robot_by_base_as("CON1 Base", "CON1")
CON2 = robot_by_base_as("CON2 Base", "CON2")
CON3 = robot_by_base_as("CON3 Base", "CON3")
CON4 = robot_by_base_as("CON4 Base", "CON4")
CON5 = robot_by_base_as("CON5 Base", "CON5")
CON6 = robot_by_base_as("CON6 Base", "CON6")
Tool1 = item('Tool1', 4)
Tool2 = item('Tool2', 4)
RBX_Tool = item('Aim Robotics FD 400 Dispenser', 4)
RBX = robot_by_base_as("RBX Base", "RBX")
AGV1 = robot_by_base_as("AGV1 Base", "AGV1")
RB4 = robot_by_base_as("RB4 Base", "RB4")
RB1 = robot_by_base("RB1 Base")
RB2 = robot_by_base("RB2 Base")
RB2.setName("RB2")
RB3 = robot_by_base("RB3 Base")
RB3.setName("RB3")
Tool3 = load_tool("Tool3", RB3, "one_tool.tool")

clear_existing_wafers()
clear_process_outputs()

# Restore parent tree and absolute poses
set_parent_abs(Die_Tray_Dummy, Station, [
    [0.000000, -1.000000, 0.000000, -1590.000000],
    [1.000000, 0.000000, 0.000000, 7150.000000],
    [0.000000, 0.000000, 1.000000, 400.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(Wafer_Cutting_Box, Station, [
    [0.000000, -1.000000, 0.000000, -3990.000000],
    [1.000000, 0.000000, 0.000000, 6270.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(Floor_Plate, Station, [
    [1.000000, 0.000000, 0.000000, 0.000000],
    [0.000000, 1.000000, 0.000000, 0.000000],
    [0.000000, 0.000000, 1.000000, -51.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(RobotArm_Table, Station, [
    [1.000000, 0.000000, 0.000000, -6700.000000],
    [0.000000, 1.000000, 0.000000, 6280.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(RobotArm_Table2, Station, [
    [1.000000, 0.000000, 0.000000, -2050.000000],
    [0.000000, 1.000000, 0.000000, 7090.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(RobotArm_Table3, Station, [
    [1.000000, 0.000000, 0.000000, -2050.000000],
    [0.000000, 1.000000, 0.000000, 5600.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(Conveyor_Table, CONV1, [
    [1.000000, 0.000000, 0.000000, -5150.000000],
    [0.000000, 1.000000, 0.000000, 6270.000000],
    [0.000000, 0.000000, 1.000000, 625.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(Conveyor_Table2, CONV2, [
    [0.000000, -1.000000, 0.000000, -6750.000000],
    [1.000000, 0.000000, 0.000000, 4920.000000],
    [0.000000, 0.000000, 1.000000, 625.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(Conveyor_Table3, CONV3, [
    [0.000000, -1.000000, 0.000000, -6750.000000],
    [1.000000, 0.000000, 0.000000, 2900.000000],
    [0.000000, 0.000000, 1.000000, 625.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(Conveyor_Table4, CONV4, [
    [1.000000, 0.000000, 0.000000, -3130.000000],
    [0.000000, 1.000000, 0.000000, 6270.000000],
    [0.000000, 0.000000, 1.000000, 625.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(pre_Wafer_machine, Station, [
    [-1.000000, -0.000000, 0.000000, -5250.000000],
    [0.000000, -1.000000, 0.000000, -1170.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(RB1_Base, Station, [
    [1.000000, 0.000000, 0.000000, -6700.000000],
    [0.000000, 1.000000, 0.000000, 6280.000000],
    [0.000000, 0.000000, 1.000000, 500.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(RB2_Base, Station, [
    [1.000000, 0.000000, 0.000000, -2050.000000],
    [0.000000, 1.000000, 0.000000, 7090.000000],
    [0.000000, 0.000000, 1.000000, 500.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(RB3_Base, Station, [
    [1.000000, 0.000000, 0.000000, -2050.000000],
    [0.000000, 1.000000, 0.000000, 5600.000000],
    [0.000000, 0.000000, 1.000000, 500.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(RobotArm_Table4, Station, RobotArm_Table4.PoseAbs().Rows())
set_parent_abs(AGV1_Base, Station, AGV1_Base.PoseAbs().Rows())
set_parent_abs(RB4_Base, Station, RB4_Base.PoseAbs().Rows())
set_parent_abs(RBX_Base, Station, [
    [1.000000, 0.000000, 0.000000, 100.000000],
    [0.000000, 1.000000, 0.000000, 5197.000000],
    [0.000000, 0.000000, 1.000000, 1350.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CONV1, Station, [
    [1.000000, 0.000000, 0.000000, -5150.000000],
    [0.000000, 1.000000, 0.000000, 6270.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CON1_Base, CONV1, [
    [1.000000, 0.000000, 0.000000, -6140.000000],
    [0.000000, 1.000000, 0.000000, 6050.000000],
    [0.000000, 0.000000, 1.000000, 750.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CONV2, Station, [
    [0.000000, -1.000000, 0.000000, -6750.000000],
    [1.000000, 0.000000, 0.000000, 4920.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CON2_Base, CONV2, [
    [0.000000, -1.000000, 0.000000, -6530.000000],
    [1.000000, 0.000000, 0.000000, 3930.000000],
    [0.000000, 0.000000, 1.000000, 750.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CONV3, Station, [
    [0.000000, -1.000000, 0.000000, -6750.000000],
    [1.000000, 0.000000, 0.000000, 2900.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CON3_Base, CONV3, [
    [0.000000, -1.000000, 0.000000, -6530.000000],
    [1.000000, 0.000000, 0.000000, 1910.000000],
    [0.000000, 0.000000, 1.000000, 750.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CONV4, Station, [
    [1.000000, 0.000000, 0.000000, -3130.000000],
    [0.000000, 1.000000, 0.000000, 6270.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CON4_Base, CONV4, [
    [1.000000, 0.000000, 0.000000, -4120.000000],
    [0.000000, 1.000000, 0.000000, 6050.000000],
    [0.000000, 0.000000, 1.000000, 750.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CONV5, Station, [
    [1.000000, 0.000000, 0.000000, 880.000000],
    [0.000000, 1.000000, 0.000000, 6270.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CON5_Base, CONV5, [
    [0.000000, 1.000000, 0.000000, -110.000000],
    [-1.000000, 0.000000, 0.000000, 6480.000000],
    [0.000000, 0.000000, 1.000000, 750.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CONV6, Station, [
    [1.000000, 0.000000, 0.000000, -1130.000000],
    [0.000000, 1.000000, 0.000000, 6270.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_abs(CON6_Base, CONV6, [
    [1.000000, 0.000000, 0.000000, -2120.000000],
    [0.000000, 1.000000, 0.000000, 6050.000000],
    [0.000000, 0.000000, 1.000000, 750.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_local(Tool1, RB1, [
    [1.000000, 0.000000, 0.000000, 0.000000],
    [0.000000, 1.000000, 0.000000, 0.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_local(Tool2, RB2, [
    [1.000000, 0.000000, 0.000000, 0.000000],
    [0.000000, 1.000000, 0.000000, 0.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
set_parent_local(Tool3, RB3, [
    [1.000000, 0.000000, 0.000000, 0.000000],
    [0.000000, 1.000000, 0.000000, 0.000000],
    [0.000000, 0.000000, 1.000000, 0.000000],
    [0.000000, 0.000000, 0.000000, 1.000000],
])
RB3.setPoseTool(Tool3)
RBX.setPoseFrame(RBX_Base)
RBX.setPoseTool(RBX_Tool)

RBX_WAIT_JOINTS = [-7.947787, 4.126018, -21.287847]
AGV1_JOINTS = AGV1.Joints()
RB4_JOINTS = RB4.Joints()

# Restore robot/conveyor joints
CON1.setJoints([0.000000])
CON2.setJoints([0.000000])
CON3.setJoints([0.000000])
CON4.setJoints([0.000000])
CON5.setJoints([0.000000])
CON6.setJoints([0.000000])
RBX.setJoints(RBX_WAIT_JOINTS)
AGV1.setJoints(AGV1_JOINTS)
RB4.setJoints(RB4_JOINTS)
RB1.setJoints([-84.025012, -3.864646, 93.723260, 0.141386, 90.000000, 84.025012])
RB2.setJoints([16.318388, -11.366844, 94.170554, 7.196290, 90.000000, -16.318388])
RB3.setJoints([177.802177, 1.938327, 83.083117, 4.978556, 90.000000, -177.802177])

RDK.Render()
