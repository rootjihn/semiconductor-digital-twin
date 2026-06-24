from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'command',
            default_value='',
            description='Interactive choice to send. Empty prints usage only.',
        ),
        DeclareLaunchArgument(
            'command_topic',
            default_value='/dobot_control/red_plate_calibration/command',
            description='Command topic consumed by red_plate_interactive_calibrator.',
        ),
        DeclareLaunchArgument(
            'status_topic',
            default_value='/dobot_control/red_plate_calibration/status',
            description='Status/prompt topic published by red_plate_interactive_calibrator.',
        ),
        DeclareLaunchArgument(
            'status_wait_sec',
            default_value='2.0',
            description='Seconds to wait for the calibrator next-step prompt after sending.',
        ),
        Node(
            package='dobot_control',
            executable='red_plate_command',
            name='red_plate_command',
            output='screen',
            parameters=[{
                'command': LaunchConfiguration('command'),
                'command_topic': LaunchConfiguration('command_topic'),
                'status_topic': LaunchConfiguration('status_topic'),
                'status_wait_sec': LaunchConfiguration('status_wait_sec'),
            }],
        ),
    ])
