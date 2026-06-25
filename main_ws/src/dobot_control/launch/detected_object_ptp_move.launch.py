from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _declare(name, default, description=''):
    return DeclareLaunchArgument(name, default_value=default, description=description)


def generate_launch_description():
    yolo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('yolo_v5'),
                'launch',
                'realsense_yolov5.launch.py',
            ])
        ),
        launch_arguments={
            'model_path': LaunchConfiguration('model_path'),
            'yolo_repo_path': LaunchConfiguration('yolo_repo_path'),
            'image_topic': LaunchConfiguration('image_topic'),
            'annotated_image_topic': LaunchConfiguration('annotated_image_topic'),
            'center_topic': LaunchConfiguration('center_topic'),
            'result_topic': LaunchConfiguration('detection_topic'),
            'conf_thres': LaunchConfiguration('conf_thres'),
            'iou_thres': LaunchConfiguration('iou_thres'),
            'imgsz': LaunchConfiguration('imgsz'),
            'device': LaunchConfiguration('device'),
            'target_class': LaunchConfiguration('target_class'),
        }.items(),
    )

    ptp_node = Node(
        package='dobot_control',
        executable='detected_object_ptp_move',
        name='detected_object_ptp_move',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'detection_topic': LaunchConfiguration('detection_topic'),
            'status_topic': LaunchConfiguration('status_topic'),
            'calibration_path': LaunchConfiguration('calibration_path'),
            'target_label': LaunchConfiguration('target_label'),
            'min_confidence': LaunchConfiguration('min_confidence'),
            'pick_hover_z_m': LaunchConfiguration('pick_hover_z_m'),
            'pick_descend_distance_m': LaunchConfiguration('pick_descend_distance_m'),
            'min_pick_z_m': LaunchConfiguration('min_pick_z_m'),
            'place_x_m': LaunchConfiguration('place_x_m'),
            'place_y_m': LaunchConfiguration('place_y_m'),
            'place_z_m': LaunchConfiguration('place_z_m'),
            'place_hover_offset_m': LaunchConfiguration('place_hover_offset_m'),
            'yaw_deg': LaunchConfiguration('yaw_deg'),
            'movej_motion_type': LaunchConfiguration('movej_motion_type'),
            'return_to_place_hover': LaunchConfiguration('return_to_place_hover'),
            'run_once': LaunchConfiguration('run_once'),
            'auto_execute': LaunchConfiguration('auto_execute'),
            'dry_run': LaunchConfiguration('dry_run'),
            'ptp_action_name': LaunchConfiguration('ptp_action_name'),
            'suction_service_name': LaunchConfiguration('suction_service_name'),
            'velocity_ratio': LaunchConfiguration('velocity_ratio'),
            'acceleration_ratio': LaunchConfiguration('acceleration_ratio'),
            'action_server_timeout_sec': LaunchConfiguration('action_server_timeout_sec'),
            'motion_goal_timeout_sec': LaunchConfiguration('motion_goal_timeout_sec'),
            'motion_result_timeout_sec': LaunchConfiguration('motion_result_timeout_sec'),
            'suction_service_timeout_sec': LaunchConfiguration('suction_service_timeout_sec'),
            'suction_response_timeout_sec': LaunchConfiguration('suction_response_timeout_sec'),
        }],
    )

    return LaunchDescription([
        _declare(
            'model_path',
            '/home/ssafy/penetrate_pjt/yolo_v5/yolov5_essential_results/weights/best.pt',
        ),
        _declare('yolo_repo_path', '/home/ssafy/yolov5'),
        _declare('image_topic', '/camera/camera/color/image_raw'),
        _declare('annotated_image_topic', '/detection_image'),
        _declare('center_topic', '/detection_center'),
        _declare('detection_topic', '/detection_results'),
        _declare('conf_thres', '0.45'),
        _declare('iou_thres', '0.45'),
        _declare('imgsz', '640'),
        _declare('device', 'cpu'),
        _declare('target_class', ''),
        _declare('target_label', ''),
        _declare('status_topic', '/dobot_control/detected_object_ptp_move/status'),
        _declare('calibration_path', '~/red_plate_pixel_to_base_calibration.json'),
        _declare('min_confidence', '0.45'),
        _declare('pick_hover_z_m', '0.06'),
        _declare('pick_descend_distance_m', '0.04'),
        _declare('min_pick_z_m', '0.02'),
        _declare('place_x_m', '0.16'),
        _declare('place_y_m', '0.01'),
        _declare('place_z_m', '0.04'),
        _declare('place_hover_offset_m', '0.06'),
        _declare('yaw_deg', '0.0'),
        _declare('movej_motion_type', '1'),
        _declare('return_to_place_hover', 'true'),
        _declare('run_once', 'true'),
        _declare('auto_execute', 'false', 'false면 계획만 출력하고, true면 실제 실행/dry_run 실행으로 들어갑니다.'),
        _declare('dry_run', 'true', 'true면 action/service 호출 없이 시퀀스만 로그로 확인합니다.'),
        _declare('ptp_action_name', 'PTP_action'),
        _declare('suction_service_name', 'dobot_suction_cup_service'),
        _declare('velocity_ratio', '0.3'),
        _declare('acceleration_ratio', '0.3'),
        _declare('action_server_timeout_sec', '5.0'),
        _declare('motion_goal_timeout_sec', '5.0'),
        _declare('motion_result_timeout_sec', '120.0'),
        _declare('suction_service_timeout_sec', '5.0'),
        _declare('suction_response_timeout_sec', '10.0'),
        yolo_launch,
        ptp_node,
    ])
