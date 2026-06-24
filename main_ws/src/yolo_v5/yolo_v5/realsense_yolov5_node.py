#!/usr/bin/env python3
"""
RealSense color image YOLOv5 inference node.

Subscribes to a RealSense raw color image topic, runs a local YOLOv5 custom
model, publishes an annotated image, the representative detection center point,
and a JSON string containing all detections.
"""

import json
import time
from typing import List, Optional, Tuple

import cv2
import rclpy
import torch
from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String


Detection = Tuple[int, int, int, int, float, int, str]


class RealSenseYoloV5Node(Node):
    """YOLOv5 detector for ROS2 RealSense image_raw streams."""

    def __init__(self) -> None:
        super().__init__("realsense_yolov5_node")

        self.declare_parameter(
            "model_path",
            "/home/ssafy/penetrate_pjt/yolo_v5/yolov5_essential_results/weights/best.pt",
        )
        self.declare_parameter("yolo_repo_path", "/home/ssafy/yolov5")
        self.declare_parameter("image_topic", "/camera/camera/color/image_raw")
        self.declare_parameter("annotated_image_topic", "/detection_image")
        self.declare_parameter("center_topic", "/detection_center")
        self.declare_parameter("result_topic", "/detection_results")
        self.declare_parameter("conf_thres", 0.25)
        self.declare_parameter("iou_thres", 0.45)
        self.declare_parameter("imgsz", 640)
        self.declare_parameter("device", "")
        self.declare_parameter("target_class", "")
        self.declare_parameter("publish_empty_results", True)

        self.model_path = self.get_parameter("model_path").value
        self.yolo_repo_path = self.get_parameter("yolo_repo_path").value
        self.image_topic = self.get_parameter("image_topic").value
        self.annotated_image_topic = self.get_parameter("annotated_image_topic").value
        self.center_topic = self.get_parameter("center_topic").value
        self.result_topic = self.get_parameter("result_topic").value
        self.conf_thres = float(self.get_parameter("conf_thres").value)
        self.iou_thres = float(self.get_parameter("iou_thres").value)
        self.imgsz = int(self.get_parameter("imgsz").value)
        self.device = str(self.get_parameter("device").value).strip()
        self.target_class = str(self.get_parameter("target_class").value).strip()
        self.publish_empty_results = bool(
            self.get_parameter("publish_empty_results").value
        )

        self.bridge = CvBridge()
        self.model = self._load_model()

        self.image_sub = self.create_subscription(
            Image,
            self.image_topic,
            self.image_callback,
            qos_profile_sensor_data,
        )
        self.annotated_image_publisher = self.create_publisher(
            Image,
            self.annotated_image_topic,
            10,
        )
        self.center_publisher = self.create_publisher(Point, self.center_topic, 10)
        self.result_publisher = self.create_publisher(String, self.result_topic, 10)

        self.last_log_time = 0.0
        self.get_logger().info(
            "RealSense YOLOv5 node ready: "
            f"subscribe={self.image_topic}, "
            f"image_pub={self.annotated_image_topic}, "
            f"center_pub={self.center_topic}, "
            f"result_pub={self.result_topic}, "
            f"model={self.model_path}"
        )

    def _load_model(self):
        self.get_logger().info(
            f"Loading YOLOv5 model from {self.model_path} using repo {self.yolo_repo_path}"
        )
        model = torch.hub.load(
            self.yolo_repo_path,
            "custom",
            path=self.model_path,
            source="local",
        )
        model.conf = self.conf_thres
        model.iou = self.iou_thres
        if self.device:
            model.to(self.device)
        return model

    def image_callback(self, msg: Image) -> None:
        try:
            bgr_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except CvBridgeError as exc:
            self.get_logger().error(f"Failed to convert ROS Image to OpenCV image: {exc}")
            return

        annotated_image = bgr_image.copy()
        rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)

        try:
            results = self.model(rgb_image, size=self.imgsz)
        except Exception as exc:  # noqa: BLE001 - keep node alive on inference failure
            self.get_logger().error(f"YOLOv5 inference failed: {exc}")
            return

        detections = self._parse_detections(results)
        representative = self._select_representative_detection(detections)

        for detection in detections:
            self._draw_detection(annotated_image, detection, detection == representative)

        self._publish_results(detections)
        if representative is not None:
            self._publish_center(representative)

        try:
            annotated_msg = self.bridge.cv2_to_imgmsg(annotated_image, encoding="bgr8")
            annotated_msg.header = msg.header
            self.annotated_image_publisher.publish(annotated_msg)
        except CvBridgeError as exc:
            self.get_logger().error(f"Failed to publish annotated image: {exc}")
            return

        self._log_throttled(len(detections), representative)

    def _parse_detections(self, results) -> List[Detection]:
        detections: List[Detection] = []
        names = getattr(self.model, "names", {})

        for result in results.xyxy[0]:
            x1, y1, x2, y2 = [int(v) for v in result[:4]]
            confidence = float(result[4])
            class_id = int(result[5])
            label = names[class_id] if class_id in names else str(class_id)

            if self.target_class and label != self.target_class:
                continue

            detections.append((x1, y1, x2, y2, confidence, class_id, label))

        return detections

    @staticmethod
    def _select_representative_detection(
        detections: List[Detection],
    ) -> Optional[Detection]:
        if not detections:
            return None
        return max(detections, key=lambda item: item[4])

    def _draw_detection(
        self,
        image,
        detection: Detection,
        is_representative: bool,
    ) -> None:
        x1, y1, x2, y2, confidence, _class_id, label = detection
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        color = (0, 0, 255) if is_representative else (0, 255, 0)

        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.circle(image, (center_x, center_y), 5, color, -1)
        cv2.drawMarker(
            image,
            (center_x, center_y),
            color,
            markerType=cv2.MARKER_CROSS,
            markerSize=18,
            thickness=2,
        )
        cv2.putText(
            image,
            f"{label} {confidence:.2f} ({center_x},{center_y})",
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    def _publish_center(self, detection: Detection) -> None:
        x1, y1, x2, y2, _confidence, _class_id, _label = detection
        center_msg = Point()
        center_msg.x = float((x1 + x2) // 2)
        center_msg.y = float((y1 + y2) // 2)
        center_msg.z = 0.0
        self.center_publisher.publish(center_msg)

    def _publish_results(self, detections: List[Detection]) -> None:
        if not detections and not self.publish_empty_results:
            return

        payload = []
        for x1, y1, x2, y2, confidence, class_id, label in detections:
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            payload.append(
                {
                    "label": label,
                    "class_id": class_id,
                    "confidence": round(confidence, 4),
                    "bbox": [x1, y1, x2, y2],
                    "center": [center_x, center_y],
                }
            )

        msg = String()
        msg.data = json.dumps(payload, ensure_ascii=False)
        self.result_publisher.publish(msg)

    def _log_throttled(
        self,
        detection_count: int,
        representative: Optional[Detection],
    ) -> None:
        now = time.monotonic()
        if now - self.last_log_time < 5.0:
            return
        self.last_log_time = now

        if representative is None:
            self.get_logger().info("No detections")
            return

        x1, y1, x2, y2, confidence, _class_id, label = representative
        self.get_logger().info(
            "Detections: "
            f"count={detection_count}, representative={label}, "
            f"conf={confidence:.2f}, center=({(x1 + x2) // 2},{(y1 + y2) // 2})"
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RealSenseYoloV5Node()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
