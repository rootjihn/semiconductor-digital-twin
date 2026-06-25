from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _declare(name, default, description):
    return DeclareLaunchArgument(name, default_value=default, description=description)


def generate_launch_description():
    return LaunchDescription([
        _declare('ax', '', 'Attach/pick X in base-frame meters. Empty means omitted.'),
        _declare('ay', '', 'Attach/pick Y in base-frame meters. Empty means omitted.'),
        _declare('az', '', 'Attach/pick Z in base-frame meters. Empty means omitted.'),
        _declare('dx', '', 'Detach/place X in base-frame meters. Empty means omitted.'),
        _declare('dy', '', 'Detach/place Y in base-frame meters. Empty means omitted.'),
        _declare('dz', '', 'Detach/place Z in base-frame meters. Empty means omitted.'),
        _declare(
            'dry_run',
            'false',
            'If true, log the planned PTP/suction sequence without moving.',
        ),
        _declare('ptp_action_name', 'PTP_action', 'Dobot PointToPoint action name.'),
        _declare(
            'suction_service_name',
            'dobot_suction_cup_service',
            'Dobot suction service name using dobot_msgs/srv/SuctionCupControl.',
        ),
        _declare(
            'validation_service_name',
            'dobot_PTP_validation_service',
            'Dobot PTP validation service name using dobot_msgs/srv/EvaluatePTPTrajectory.',
        ),
        _declare('velocity_ratio', '0.3', 'PointToPoint action velocity ratio.'),
        _declare('acceleration_ratio', '0.3', 'PointToPoint action acceleration ratio.'),
        _declare(
            'action_server_timeout_sec',
            '5.0',
            'Seconds to wait for PointToPoint action server.',
        ),
        _declare(
            'motion_goal_timeout_sec',
            '5.0',
            'Seconds to wait for PointToPoint goal acceptance.',
        ),
        _declare('motion_result_timeout_sec', '120.0', 'Seconds to wait for Dobot action result.'),
        _declare('suction_service_timeout_sec', '5.0', 'Seconds to wait for suction service.'),
        _declare(
            'suction_response_timeout_sec',
            '10.0',
            'Seconds to wait for suction service response.',
        ),
        _declare(
            'validation_service_timeout_sec',
            '10.0',
            'Seconds to wait for PTP validation service.',
        ),
        _declare(
            'validation_response_timeout_sec',
            '10.0',
            'Seconds to wait for PTP validation response.',
        ),
        Node(
            package='dobot_control',
            executable='param_ptp_pick_place',
            name='param_ptp_pick_place',
            output='screen',
            emulate_tty=True,
            parameters=[{
                'ax': LaunchConfiguration('ax'),
                'ay': LaunchConfiguration('ay'),
                'az': LaunchConfiguration('az'),
                'dx': LaunchConfiguration('dx'),
                'dy': LaunchConfiguration('dy'),
                'dz': LaunchConfiguration('dz'),
                'dry_run': LaunchConfiguration('dry_run'),
                'ptp_action_name': LaunchConfiguration('ptp_action_name'),
                'suction_service_name': LaunchConfiguration('suction_service_name'),
                'validation_service_name': LaunchConfiguration('validation_service_name'),
                'velocity_ratio': LaunchConfiguration('velocity_ratio'),
                'acceleration_ratio': LaunchConfiguration('acceleration_ratio'),
                'action_server_timeout_sec': LaunchConfiguration('action_server_timeout_sec'),
                'motion_goal_timeout_sec': LaunchConfiguration('motion_goal_timeout_sec'),
                'motion_result_timeout_sec': LaunchConfiguration('motion_result_timeout_sec'),
                'suction_service_timeout_sec': LaunchConfiguration('suction_service_timeout_sec'),
                'suction_response_timeout_sec': LaunchConfiguration(
                    'suction_response_timeout_sec'
                ),
                'validation_service_timeout_sec': LaunchConfiguration(
                    'validation_service_timeout_sec'
                ),
                'validation_response_timeout_sec': LaunchConfiguration(
                    'validation_response_timeout_sec'
                ),
            }],
        ),
    ])
