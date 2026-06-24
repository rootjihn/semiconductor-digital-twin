from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'base_frame',
            default_value='magician_base_link',
            description='Dobot base frame to publish final 3D coordinates in.',
        ),
        DeclareLaunchArgument(
            'camera_link_frame',
            default_value='camera_link',
            description=(
                'RealSense wrapper root frame. Do not use '
                'camera_color_optical_frame here.'
            ),
        ),
        DeclareLaunchArgument(
            'x', default_value='0.435', description='initial camera_link x in base_frame [m]'
        ),
        DeclareLaunchArgument(
            'y', default_value='-0.02', description='initial camera_link y in base_frame [m]'
        ),
        DeclareLaunchArgument(
            'z', default_value='0.3', description='initial camera_link z in base_frame [m]'
        ),
        DeclareLaunchArgument(
            'roll',
            default_value='0.0',
            description='camera_link roll in base_frame [rad]',
        ),
        DeclareLaunchArgument(
            'pitch',
            default_value='1.0472',
            description='initial camera_link pitch in base_frame [rad]',
        ),
        DeclareLaunchArgument(
            'yaw',
            default_value='3.14159',
            description='initial camera_link yaw in base_frame [rad]',
        ),
        DeclareLaunchArgument(
            'pixel_u', default_value='320', description='Target RGB pixel column.'
        ),
        DeclareLaunchArgument(
            'pixel_v', default_value='240', description='Target RGB pixel row.'
        ),
        DeclareLaunchArgument(
            'aligned_depth_topic',
            default_value='/camera/camera/aligned_depth_to_color/image_raw',
            description='RealSense aligned depth image topic.',
        ),
        DeclareLaunchArgument(
            'camera_info_topic',
            default_value='/camera/camera/aligned_depth_to_color/camera_info',
            description='CameraInfo matching aligned depth/color pixels.',
        ),
        DeclareLaunchArgument(
            'color_image_topic',
            default_value='/camera/camera/color/image_raw',
            description='Color image topic used for grid corner detection.',
        ),
        DeclareLaunchArgument(
            'color_camera_info_topic',
            default_value='/camera/camera/color/camera_info',
            description='CameraInfo matching color_image_topic.',
        ),
        DeclareLaunchArgument(
            'grid_columns',
            default_value='7',
            description='Checkerboard inner-corner columns.',
        ),
        DeclareLaunchArgument(
            'grid_rows',
            default_value='5',
            description='Checkerboard inner-corner rows.',
        ),
        DeclareLaunchArgument(
            'grid_square_size',
            default_value='0.025',
            description='Checkerboard square size in meters.',
        ),
        DeclareLaunchArgument(
            'grid_origin_xyz',
            default_value='0.0,0.0,0.0',
            description='First detected grid corner in base-frame meters, comma-separated.',
        ),
        DeclareLaunchArgument(
            'grid_axes',
            default_value='xy',
            description='Base-frame plane for object points: xy, xz, or yz.',
        ),
        DeclareLaunchArgument(
            'publish_calibrated_tf',
            default_value='false',
            description='Publish base_frame -> calibrated_camera_frame from PnP.',
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='dobot_to_realsense_static_tf',
            arguments=[
                '--x', LaunchConfiguration('x'),
                '--y', LaunchConfiguration('y'),
                '--z', LaunchConfiguration('z'),
                '--roll', LaunchConfiguration('roll'),
                '--pitch', LaunchConfiguration('pitch'),
                '--yaw', LaunchConfiguration('yaw'),
                '--frame-id', LaunchConfiguration('base_frame'),
                '--child-frame-id', LaunchConfiguration('camera_link_frame'),
            ],
            output='screen',
        ),
        Node(
            package='dobot_control',
            executable='pixel_to_base',
            name='pixel_to_base_node',
            output='screen',
            parameters=[{
                'aligned_depth_topic': LaunchConfiguration('aligned_depth_topic'),
                'camera_info_topic': LaunchConfiguration('camera_info_topic'),
                'target_frame': LaunchConfiguration('base_frame'),
                'pixel_u': LaunchConfiguration('pixel_u'),
                'pixel_v': LaunchConfiguration('pixel_v'),
            }],
        ),
        Node(
            package='dobot_control',
            executable='grid_pnp_calibrator',
            name='grid_pnp_calibrator_node',
            output='screen',
            parameters=[{
                'image_topic': LaunchConfiguration('color_image_topic'),
                'camera_info_topic': LaunchConfiguration('color_camera_info_topic'),
                'base_frame': LaunchConfiguration('base_frame'),
                'grid_columns': LaunchConfiguration('grid_columns'),
                'grid_rows': LaunchConfiguration('grid_rows'),
                'grid_square_size': LaunchConfiguration('grid_square_size'),
                'grid_origin_xyz': LaunchConfiguration('grid_origin_xyz'),
                'grid_axes': LaunchConfiguration('grid_axes'),
                'publish_tf': LaunchConfiguration('publish_calibrated_tf'),
                'initial_x': LaunchConfiguration('x'),
                'initial_y': LaunchConfiguration('y'),
                'initial_z': LaunchConfiguration('z'),
                'initial_roll': LaunchConfiguration('roll'),
                'initial_pitch': LaunchConfiguration('pitch'),
                'initial_yaw': LaunchConfiguration('yaw'),
            }],
        ),
    ])
