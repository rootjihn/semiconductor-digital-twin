from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _declare(name, default, description):
    return DeclareLaunchArgument(name, default_value=default, description=description)


def generate_launch_description():
    return LaunchDescription([
        _declare(
            'image_topic',
            '/camera/camera/color/image_raw',
            'Image topic displayed and clicked by the OpenCV pick/place UI.',
        ),
        _declare(
            'calibration_path',
            '~/red_plate_pixel_to_base_calibration.json',
            'Saved red-plate pixel-to-base calibration JSON path.',
        ),
        _declare(
            'tcp_pose_topic',
            'dobot_pose_raw',
            'Current Dobot TCP pose topic; stored for diagnostics/future current-z use.',
        ),
        _declare('dry_run', 'true', 'If true, only log targets; do not move or use suction.'),
        _declare('window_name', 'click_pick_place', 'OpenCV window name.'),
        _declare('crop_x', '0', 'Preview crop left x in original image pixels.'),
        _declare('crop_y', '0', 'Preview crop top y in original image pixels.'),
        _declare('crop_w', '0', 'Preview crop width. 0 means full remaining width.'),
        _declare('crop_h', '0', 'Preview crop height. 0 means full remaining height.'),
        _declare('display_w', '0', 'Displayed preview width. 0 means crop width.'),
        _declare('display_h', '0', 'Displayed preview height. 0 means crop height.'),
        _declare(
            'crop_save_path',
            '~/image_crop_viewer_crop.json',
            'Persistent four-point perspective crop JSON. '
            'x key updates it; r clears runtime crop.',
        ),
        _declare('auto_load_crop', 'true', 'Load crop_save_path on startup when it exists.'),
        _declare('hover_z_m', '0.06', 'Hover Z in base frame meters.'),
        _declare(
            'descend_distance_m',
            '0.04',
            'Absolute Z descend distance from hover in meters. '
            'Negative values are treated as signed operator input and abs() is used. '
            'Final descend_z_m may be below 0.',
        ),
        _declare('r_deg', '0.0', 'Dobot R/yaw angle in degrees for target poses.'),
        _declare('return_to_hover', 'true', 'MoveL back to hover after suction command.'),
        _declare('movej_motion_type', '1', 'PointToPoint MOVJ_XYZ motion type.'),
        _declare('movel_motion_type', '2', 'PointToPoint MOVL_XYZ motion type.'),
        _declare('ptp_action_name', 'PTP_action', 'Dobot PointToPoint action name.'),
        _declare(
            'suction_service_name',
            'dobot_suction_cup_service',
            'Dobot suction service name using dobot_msgs/srv/SuctionCupControl.',
        ),
        _declare('velocity_ratio', '0.3', 'PointToPoint action velocity ratio.'),
        _declare('acceleration_ratio', '0.3', 'PointToPoint action acceleration ratio.'),
        _declare(
            'action_server_timeout_sec',
            '5.0',
            'Seconds to wait for PointToPoint action server on each real click.',
        ),
        _declare(
            'motion_goal_timeout_sec',
            '5.0',
            'Seconds to wait for PointToPoint goal acceptance.',
        ),
        _declare(
            'motion_result_timeout_sec',
            '120.0',
            'Seconds to wait for Dobot action result before treating sequence as incomplete.',
        ),
        _declare(
            'suction_service_timeout_sec',
            '5.0',
            'Seconds to wait for suction service on each real suction command.',
        ),
        _declare(
            'suction_response_timeout_sec',
            '10.0',
            'Seconds to wait for suction service response.',
        ),
        Node(
            package='dobot_control',
            executable='click_pick_place',
            name='click_pick_place',
            output='screen',
            emulate_tty=True,
            parameters=[{
                'image_topic': LaunchConfiguration('image_topic'),
                'calibration_path': LaunchConfiguration('calibration_path'),
                'tcp_pose_topic': LaunchConfiguration('tcp_pose_topic'),
                'dry_run': LaunchConfiguration('dry_run'),
                'window_name': LaunchConfiguration('window_name'),
                'crop_x': LaunchConfiguration('crop_x'),
                'crop_y': LaunchConfiguration('crop_y'),
                'crop_w': LaunchConfiguration('crop_w'),
                'crop_h': LaunchConfiguration('crop_h'),
                'display_w': LaunchConfiguration('display_w'),
                'display_h': LaunchConfiguration('display_h'),
                'crop_save_path': LaunchConfiguration('crop_save_path'),
                'auto_load_crop': LaunchConfiguration('auto_load_crop'),
                'hover_z_m': LaunchConfiguration('hover_z_m'),
                'descend_distance_m': LaunchConfiguration('descend_distance_m'),
                'r_deg': LaunchConfiguration('r_deg'),
                'return_to_hover': LaunchConfiguration('return_to_hover'),
                'movej_motion_type': LaunchConfiguration('movej_motion_type'),
                'movel_motion_type': LaunchConfiguration('movel_motion_type'),
                'ptp_action_name': LaunchConfiguration('ptp_action_name'),
                'suction_service_name': LaunchConfiguration('suction_service_name'),
                'velocity_ratio': LaunchConfiguration('velocity_ratio'),
                'acceleration_ratio': LaunchConfiguration('acceleration_ratio'),
                'action_server_timeout_sec': LaunchConfiguration('action_server_timeout_sec'),
                'motion_goal_timeout_sec': LaunchConfiguration('motion_goal_timeout_sec'),
                'motion_result_timeout_sec': LaunchConfiguration('motion_result_timeout_sec'),
                'suction_service_timeout_sec': LaunchConfiguration('suction_service_timeout_sec'),
                'suction_response_timeout_sec': LaunchConfiguration(
                    'suction_response_timeout_sec'
                ),
            }],
        ),
    ])
