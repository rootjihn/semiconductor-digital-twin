from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    model_path = LaunchConfiguration("model_path")
    yolo_repo_path = LaunchConfiguration("yolo_repo_path")
    image_topic = LaunchConfiguration("image_topic")
    annotated_image_topic = LaunchConfiguration("annotated_image_topic")
    center_topic = LaunchConfiguration("center_topic")
    result_topic = LaunchConfiguration("result_topic")
    conf_thres = LaunchConfiguration("conf_thres")
    iou_thres = LaunchConfiguration("iou_thres")
    imgsz = LaunchConfiguration("imgsz")
    device = LaunchConfiguration("device")
    target_class = LaunchConfiguration("target_class")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "model_path",
                default_value=(
                    "/home/ssafy/penetrate_pjt/yolo_v5/"
                    "yolov5_essential_results/weights/best.pt"
                ),
                description="Path to the custom YOLOv5 weights file",
            ),
            DeclareLaunchArgument(
                "yolo_repo_path",
                default_value="/home/ssafy/yolov5",
                description="Path to the local ultralytics/yolov5 repository",
            ),
            DeclareLaunchArgument(
                "image_topic",
                default_value="/camera/camera/color/image_raw",
                description="Input RealSense color image topic",
            ),
            DeclareLaunchArgument(
                "annotated_image_topic",
                default_value="/detection_image",
                description="Output annotated image topic",
            ),
            DeclareLaunchArgument(
                "center_topic",
                default_value="/detection_center",
                description="Output representative detection center topic",
            ),
            DeclareLaunchArgument(
                "result_topic",
                default_value="/detection_results",
                description="Output JSON detection result topic",
            ),
            DeclareLaunchArgument(
                "conf_thres",
                default_value="0.25",
                description="YOLO confidence threshold",
            ),
            DeclareLaunchArgument(
                "iou_thres",
                default_value="0.45",
                description="YOLO NMS IoU threshold",
            ),
            DeclareLaunchArgument(
                "imgsz",
                default_value="640",
                description="YOLO inference image size",
            ),
            DeclareLaunchArgument(
                "device",
                default_value="",
                description="Torch device, for example cuda:0 or cpu. Empty means auto/default.",
            ),
            DeclareLaunchArgument(
                "target_class",
                default_value="",
                description="Optional class label filter. Empty means all classes.",
            ),
            Node(
                package="yolo_v5",
                executable="realsense_yolov5_node",
                name="realsense_yolov5_node",
                output="screen",
                parameters=[
                    {
                        "model_path": model_path,
                        "yolo_repo_path": yolo_repo_path,
                        "image_topic": image_topic,
                        "annotated_image_topic": annotated_image_topic,
                        "center_topic": center_topic,
                        "result_topic": result_topic,
                        "conf_thres": conf_thres,
                        "iou_thres": iou_thres,
                        "imgsz": imgsz,
                        "device": device,
                        "target_class": target_class,
                    }
                ],
            ),
        ]
    )
