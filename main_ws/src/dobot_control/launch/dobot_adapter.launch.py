from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'detection_topic',
            default_value='/detection_results',
            description='YOLO JSON-array detection result topic.',
        ),
        DeclareLaunchArgument(
            'status_topic',
            default_value='/dobot_control/dobot_adapter/status',
            description='Adapter JSON status topic.',
        ),
        DeclareLaunchArgument(
            'calibration_path',
            default_value='~/red_plate_pixel_to_base_calibration.json',
            description='Saved pixel-to-Dobot-base calibration JSON.',
        ),
        DeclareLaunchArgument(
            'target_label',
            default_value='',
            description='Optional YOLO label filter. Empty accepts all labels.',
        ),
        DeclareLaunchArgument(
            'min_confidence',
            default_value='0.25',
            description='Minimum detection confidence.',
        ),
        DeclareLaunchArgument(
            'mode',
            default_value='attach',
            description='Pick-place mode: attach or detach.',
        ),
        DeclareLaunchArgument(
            'auto_execute',
            default_value='false',
            description='When false, only publish/log the planned Dobot sequence.',
        ),
        DeclareLaunchArgument(
            'dry_run',
            default_value='true',
            description='When true, describe steps without robot action/service calls.',
        ),
        DeclareLaunchArgument('hover_z_m', default_value='0.06'),
        DeclareLaunchArgument('descend_distance_m', default_value='0.04'),
        DeclareLaunchArgument('r_deg', default_value='0.0'),
        DeclareLaunchArgument('return_to_hover', default_value='true'),
        DeclareLaunchArgument('movej_motion_type', default_value='1'),
        DeclareLaunchArgument('movel_motion_type', default_value='2'),
        DeclareLaunchArgument('ptp_action_name', default_value='PTP_action'),
        DeclareLaunchArgument('suction_service_name', default_value='dobot_suction_cup_service'),
        Node(
            package='dobot_control',
            executable='dobot_adapter',
            name='dobot_adapter',
            output='screen',
            parameters=[{
                'detection_topic': LaunchConfiguration('detection_topic'),
                'status_topic': LaunchConfiguration('status_topic'),
                'calibration_path': LaunchConfiguration('calibration_path'),
                'target_label': LaunchConfiguration('target_label'),
                'min_confidence': LaunchConfiguration('min_confidence'),
                'mode': LaunchConfiguration('mode'),
                'auto_execute': LaunchConfiguration('auto_execute'),
                'dry_run': LaunchConfiguration('dry_run'),
                'hover_z_m': LaunchConfiguration('hover_z_m'),
                'descend_distance_m': LaunchConfiguration('descend_distance_m'),
                'r_deg': LaunchConfiguration('r_deg'),
                'return_to_hover': LaunchConfiguration('return_to_hover'),
                'movej_motion_type': LaunchConfiguration('movej_motion_type'),
                'movel_motion_type': LaunchConfiguration('movel_motion_type'),
                'ptp_action_name': LaunchConfiguration('ptp_action_name'),
                'suction_service_name': LaunchConfiguration('suction_service_name'),
            }],
        ),
    ])
