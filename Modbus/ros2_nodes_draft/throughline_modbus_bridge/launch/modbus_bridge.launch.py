"""Launch file for the interface-only Modbus bridge node draft."""

from __future__ import annotations

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    package_share = Path(get_package_share_directory("throughline_modbus_bridge"))
    default_config = package_share / "config" / "modbus_bridge.yaml"

    config_file_arg = DeclareLaunchArgument(
        "config_file",
        default_value=str(default_config),
        description="YAML config file for modbus_bridge_node.",
    )

    node = Node(
        package="throughline_modbus_bridge",
        executable="modbus_bridge_node",
        name="modbus_bridge_node",
        output="screen",
        parameters=[LaunchConfiguration("config_file")],
    )

    return LaunchDescription([config_file_arg, node])
