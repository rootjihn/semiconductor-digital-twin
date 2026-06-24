from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'image_topic',
            default_value='/camera/camera/color/image_raw',
            description='Image topic displayed by the crop viewer.',
        ),
        DeclareLaunchArgument(
            'crop_save_path',
            default_value='~/image_crop_viewer_crop.json',
            description='JSON file used to load/save the four-point crop setting.',
        ),
        DeclareLaunchArgument(
            'window_name',
            default_value='image_crop_viewer',
            description='OpenCV window name.',
        ),
        DeclareLaunchArgument(
            'auto_load_crop',
            default_value='true',
            description='Load an existing crop_save_path setting on startup.',
        ),
        Node(
            package='dobot_control',
            executable='image_crop_viewer',
            name='image_crop_viewer',
            output='screen',
            emulate_tty=True,
            parameters=[{
                'image_topic': LaunchConfiguration('image_topic'),
                'crop_save_path': LaunchConfiguration('crop_save_path'),
                'window_name': LaunchConfiguration('window_name'),
                'auto_load_crop': LaunchConfiguration('auto_load_crop'),
            }],
        ),
    ])
