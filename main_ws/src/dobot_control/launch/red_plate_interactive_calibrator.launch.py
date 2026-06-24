from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'image_topic',
            default_value='/camera/camera/color/image_raw',
            description='RGB/BGR camera image topic used for red plate detection.',
        ),
        DeclareLaunchArgument(
            'tcp_pose_topic',
            default_value='dobot_pose_raw',
            description='Current Dobot TCP pose Float64MultiArray topic.',
        ),
        DeclareLaunchArgument(
            'command_topic',
            default_value='/dobot_control/red_plate_calibration/command',
            description=(
                'std_msgs/String command topic for interactive choices when '
                'launch stdin is unavailable.'
            ),
        ),
        DeclareLaunchArgument(
            'status_topic',
            default_value='/dobot_control/red_plate_calibration/status',
            description='std_msgs/String prompt/status topic for red_plate_command.',
        ),
        DeclareLaunchArgument(
            'calibration_save_path',
            default_value='~/red_plate_pixel_to_base_calibration.json',
            description='JSON path written only after user approval.',
        ),
        DeclareLaunchArgument(
            'min_samples',
            default_value='4',
            description='Minimum samples before homography calibration.',
        ),
        DeclareLaunchArgument(
            'min_area_px',
            default_value='800.0',
            description='Minimum red plate contour area in pixels.',
        ),
        DeclareLaunchArgument(
            'min_quality',
            default_value='0.55',
            description='Minimum red plate detection quality.',
        ),
        DeclareLaunchArgument(
            'ambiguity_ratio',
            default_value='0.85',
            description='Reject if second candidate score is this fraction of best score.',
        ),
        DeclareLaunchArgument(
            'hsv_lower_red1',
            default_value='0,120,70',
            description='HSV lower bound for red range #1 (OpenCV H,S,V).',
        ),
        DeclareLaunchArgument(
            'hsv_upper_red1',
            default_value='10,255,255',
            description='HSV upper bound for red range #1 (OpenCV H,S,V).',
        ),
        DeclareLaunchArgument(
            'hsv_lower_red2',
            default_value='170,120,70',
            description='HSV lower bound for red range #2 (OpenCV H,S,V).',
        ),
        DeclareLaunchArgument(
            'hsv_upper_red2',
            default_value='180,255,255',
            description='HSV upper bound for red range #2 (OpenCV H,S,V).',
        ),
        DeclareLaunchArgument(
            'z_hover_offset_m',
            default_value='0.04',
            description='Move target z = sampled TCP plane z + this hover offset.',
        ),
        DeclareLaunchArgument(
            'target_r_deg',
            default_value='0.0',
            description='Fallback Dobot tool rotation if current TCP r is unavailable.',
        ),
        DeclareLaunchArgument(
            'velocity_ratio',
            default_value='0.3',
            description='PointToPoint action velocity ratio.',
        ),
        DeclareLaunchArgument(
            'acceleration_ratio',
            default_value='0.3',
            description='PointToPoint action acceleration ratio.',
        ),
        DeclareLaunchArgument(
            'dry_run',
            default_value='false',
            description='If true, compute target but do not send Dobot action goal.',
        ),
        DeclareLaunchArgument(
            'debug_publish_images',
            default_value='true',
            description='Publish red mask/red-only/overlay debug image topics.',
        ),
        DeclareLaunchArgument(
            'debug_mask_topic',
            default_value='/dobot_control/red_plate/debug_mask',
            description='mono8 red threshold mask debug topic.',
        ),
        DeclareLaunchArgument(
            'debug_red_only_topic',
            default_value='/dobot_control/red_plate/debug_red_only',
            description='bgr8 image with only red-thresholded pixels visible.',
        ),
        DeclareLaunchArgument(
            'debug_overlay_topic',
            default_value='/dobot_control/red_plate/debug_overlay',
            description='bgr8 original image with red mask highlighted green.',
        ),
        DeclareLaunchArgument(
            'action_name',
            default_value='PTP_action',
            description='Dobot PointToPoint action name.',
        ),
        Node(
            package='dobot_control',
            executable='red_plate_interactive_calibrator',
            name='red_plate_interactive_calibrator',
            output='screen',
            emulate_tty=True,
            parameters=[{
                'image_topic': LaunchConfiguration('image_topic'),
                'tcp_pose_topic': LaunchConfiguration('tcp_pose_topic'),
                'command_topic': LaunchConfiguration('command_topic'),
                'status_topic': LaunchConfiguration('status_topic'),
                'calibration_save_path': LaunchConfiguration('calibration_save_path'),
                'min_samples': LaunchConfiguration('min_samples'),
                'min_area_px': LaunchConfiguration('min_area_px'),
                'min_quality': LaunchConfiguration('min_quality'),
                'ambiguity_ratio': LaunchConfiguration('ambiguity_ratio'),
                'hsv_lower_red1': LaunchConfiguration('hsv_lower_red1'),
                'hsv_upper_red1': LaunchConfiguration('hsv_upper_red1'),
                'hsv_lower_red2': LaunchConfiguration('hsv_lower_red2'),
                'hsv_upper_red2': LaunchConfiguration('hsv_upper_red2'),
                'z_hover_offset_m': LaunchConfiguration('z_hover_offset_m'),
                'target_r_deg': LaunchConfiguration('target_r_deg'),
                'velocity_ratio': LaunchConfiguration('velocity_ratio'),
                'acceleration_ratio': LaunchConfiguration('acceleration_ratio'),
                'dry_run': LaunchConfiguration('dry_run'),
                'debug_publish_images': LaunchConfiguration('debug_publish_images'),
                'debug_mask_topic': LaunchConfiguration('debug_mask_topic'),
                'debug_red_only_topic': LaunchConfiguration('debug_red_only_topic'),
                'debug_overlay_topic': LaunchConfiguration('debug_overlay_topic'),
                'action_name': LaunchConfiguration('action_name'),
            }],
        ),
    ])
