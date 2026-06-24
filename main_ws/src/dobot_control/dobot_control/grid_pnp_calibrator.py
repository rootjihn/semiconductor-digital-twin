"""Estimate camera-to-base transform from a floor grid using checkerboard PnP."""

from __future__ import annotations

import json
from typing import Any

import cv2
import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from tf2_ros import TransformBroadcaster

from dobot_control.grid_pnp_calibration import (
    camera_matrix_from_k,
    distortion_from_d,
    estimate_grid_pose_pnp,
    find_checkerboard_corners,
    make_grid_object_points,
    quaternion_from_rotation_matrix,
    rpy_from_rotation_matrix,
)


def image_msg_to_cv2(msg: Image) -> np.ndarray:
    """Convert common ROS Image encodings without cv_bridge."""
    encoding = msg.encoding.lower()
    data = np.frombuffer(bytes(msg.data), dtype=np.uint8)

    if encoding in {"bgr8", "rgb8"}:
        expected = msg.height * msg.step
        if data.size < expected:
            raise ValueError("image data is shorter than height * step")
        image = data[:expected].reshape(msg.height, msg.step)
        image = image[:, : msg.width * 3].reshape(msg.height, msg.width, 3)
        if encoding == "rgb8":
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        return image.copy()

    if encoding in {"mono8", "8uc1"}:
        expected = msg.height * msg.step
        if data.size < expected:
            raise ValueError("image data is shorter than height * step")
        image = data[:expected].reshape(msg.height, msg.step)
        return image[:, : msg.width].copy()

    raise ValueError(f"Unsupported image encoding for grid calibration: {msg.encoding}")


def _param_float_list(node: Node, name: str) -> list[float]:
    value = node.get_parameter(name).value
    if isinstance(value, str):
        return [float(item.strip()) for item in value.split(",") if item.strip()]
    return [float(item) for item in value]


def _param_bool(node: Node, name: str) -> bool:
    value = node.get_parameter(name).value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class GridPnPCalibratorNode(Node):
    """Auto-detect grid corners and estimate calibrated camera/base extrinsics."""

    def __init__(self) -> None:
        super().__init__("grid_pnp_calibrator_node")

        self.declare_parameter("image_topic", "/camera/camera/color/image_raw")
        self.declare_parameter("camera_info_topic", "/camera/camera/color/camera_info")
        self.declare_parameter("result_topic", "/dobot_control/grid_pnp_calibration/result")
        self.declare_parameter("base_frame", "magician_base_link")
        self.declare_parameter("camera_frame", "camera_color_optical_frame")
        self.declare_parameter("publish_tf", False)
        self.declare_parameter("calibrated_camera_frame", "camera_color_optical_frame_calibrated")

        self.declare_parameter("grid_columns", 7)
        self.declare_parameter("grid_rows", 5)
        self.declare_parameter("grid_square_size", 0.025)
        self.declare_parameter("grid_origin_xyz", "0.0,0.0,0.0")
        self.declare_parameter("grid_axes", "xy")
        self.declare_parameter("refine_subpixel", True)
        self.declare_parameter("refine_lm", True)
        self.declare_parameter("ransac_reprojection_error_px", 4.0)
        self.declare_parameter("ransac_confidence", 0.99)
        self.declare_parameter("ransac_iterations", 100)
        self.declare_parameter("max_publish_rate_hz", 2.0)

        # Existing launch default/starting guess.  It is logged with results so the
        # operator can compare PnP output against the manual seed.
        self.declare_parameter("initial_x", 0.435)
        self.declare_parameter("initial_y", -0.02)
        self.declare_parameter("initial_z", 0.3)
        self.declare_parameter("initial_roll", 0.0)
        self.declare_parameter("initial_pitch", 1.0472)
        self.declare_parameter("initial_yaw", 3.14159)

        self._camera_info: CameraInfo | None = None
        self._last_publish_ns = 0
        self._tf_broadcaster = TransformBroadcaster(self)
        self._result_pub = self.create_publisher(
            String, str(self.get_parameter("result_topic").value), 10
        )

        self.create_subscription(
            CameraInfo,
            str(self.get_parameter("camera_info_topic").value),
            self._camera_info_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Image,
            str(self.get_parameter("image_topic").value),
            self._image_callback,
            qos_profile_sensor_data,
        )

        self.get_logger().info(
            "grid_pnp_calibrator ready: image=%s, camera_info=%s, grid=%dx%d square=%.4fm"
            % (
                self.get_parameter("image_topic").value,
                self.get_parameter("camera_info_topic").value,
                int(self.get_parameter("grid_columns").value),
                int(self.get_parameter("grid_rows").value),
                float(self.get_parameter("grid_square_size").value),
            )
        )

    def _camera_info_callback(self, msg: CameraInfo) -> None:
        self._camera_info = msg

    def _image_callback(self, msg: Image) -> None:
        if self._camera_info is None:
            self._log_throttled("Waiting for CameraInfo before grid PnP calibration...")
            return

        now_ns = self.get_clock().now().nanoseconds
        max_rate = float(self.get_parameter("max_publish_rate_hz").value)
        min_period_ns = int(1e9 / max_rate) if max_rate > 0.0 else 0
        if min_period_ns and now_ns - self._last_publish_ns < min_period_ns:
            return

        columns = int(self.get_parameter("grid_columns").value)
        rows = int(self.get_parameter("grid_rows").value)
        try:
            cv_image = image_msg_to_cv2(msg)
            image_points = find_checkerboard_corners(
                cv_image,
                columns=columns,
                rows=rows,
                refine_subpixel=_param_bool(self, "refine_subpixel"),
            )
        except ValueError as exc:
            self.get_logger().error(str(exc))
            return

        if image_points is None:
            self._log_throttled("Grid checkerboard not detected in current image")
            return

        try:
            object_points = make_grid_object_points(
                columns=columns,
                rows=rows,
                square_size=float(self.get_parameter("grid_square_size").value),
                origin_xyz=_param_float_list(self, "grid_origin_xyz"),
                axes=str(self.get_parameter("grid_axes").value),
            )
            result = estimate_grid_pose_pnp(
                object_points=object_points,
                image_points=image_points,
                camera_matrix=camera_matrix_from_k(self._camera_info.k),
                dist_coeffs=distortion_from_d(self._camera_info.d),
                ransac_reprojection_error_px=float(
                    self.get_parameter("ransac_reprojection_error_px").value
                ),
                ransac_confidence=float(self.get_parameter("ransac_confidence").value),
                ransac_iterations=int(self.get_parameter("ransac_iterations").value),
                refine_lm=_param_bool(self, "refine_lm"),
            )
        except (RuntimeError, ValueError) as exc:
            self.get_logger().warning(f"Grid PnP failed: {exc}")
            return

        base_to_cam_rpy = rpy_from_rotation_matrix(result.rotation_base_to_camera)
        cam_to_base_rpy = rpy_from_rotation_matrix(result.rotation_camera_to_base)
        payload: dict[str, Any] = {
            "stamp": {
                "sec": int(msg.header.stamp.sec),
                "nanosec": int(msg.header.stamp.nanosec),
            },
            "base_frame": str(self.get_parameter("base_frame").value),
            "camera_frame": str(
                self._camera_info.header.frame_id
                or msg.header.frame_id
                or self.get_parameter("camera_frame").value
            ),
            "grid": {
                "columns": columns,
                "rows": rows,
                "square_size_m": float(self.get_parameter("grid_square_size").value),
                "origin_xyz_m": _param_float_list(self, "grid_origin_xyz"),
                "axes": str(self.get_parameter("grid_axes").value),
            },
            "base_to_camera_optical": {
                "translation_xyz_m": result.translation_base_to_camera.tolist(),
                "rpy_rad": list(base_to_cam_rpy),
            },
            "camera_optical_to_base": {
                "translation_xyz_m": result.translation_camera_to_base.tolist(),
                "rpy_rad": list(cam_to_base_rpy),
            },
            "quality": {
                "mean_reprojection_error_px": result.quality.mean_error_px,
                "max_reprojection_error_px": result.quality.max_error_px,
                "rms_reprojection_error_px": result.quality.rms_error_px,
                "inlier_ratio": result.quality.inlier_ratio,
                "inlier_count": result.quality.inlier_count,
                "point_count": result.quality.point_count,
            },
            "initial_guess_base_to_camera_link": {
                "x": float(self.get_parameter("initial_x").value),
                "y": float(self.get_parameter("initial_y").value),
                "z": float(self.get_parameter("initial_z").value),
                "roll": float(self.get_parameter("initial_roll").value),
                "pitch": float(self.get_parameter("initial_pitch").value),
                "yaw": float(self.get_parameter("initial_yaw").value),
            },
            "residual_correction_ready": True,
            "note": (
                "PnP result is for base_frame -> camera optical frame; "
                "residual touch-point correction can be layered on top."
            ),
        }

        msg_out = String()
        msg_out.data = json.dumps(payload, ensure_ascii=False)
        self._result_pub.publish(msg_out)
        self._last_publish_ns = now_ns

        if _param_bool(self, "publish_tf"):
            self._publish_transform(msg, result)

        q = result.quality
        t = result.translation_base_to_camera
        self.get_logger().info(
            (
                "grid PnP OK: base->camera_optical xyz=(%.4f, %.4f, %.4f), "
                "rpy=(%.4f, %.4f, %.4f), reproj mean/max/rms="
                "%.3f/%.3f/%.3f px, inliers=%d/%d"
            )
            % (
                t[0],
                t[1],
                t[2],
                base_to_cam_rpy[0],
                base_to_cam_rpy[1],
                base_to_cam_rpy[2],
                q.mean_error_px,
                q.max_error_px,
                q.rms_error_px,
                q.inlier_count,
                q.point_count,
            )
        )

    def _publish_transform(self, image_msg: Image, result) -> None:
        transform = TransformStamped()
        transform.header.stamp = image_msg.header.stamp
        transform.header.frame_id = str(self.get_parameter("base_frame").value)
        transform.child_frame_id = str(self.get_parameter("calibrated_camera_frame").value)
        transform.transform.translation.x = float(result.translation_base_to_camera[0])
        transform.transform.translation.y = float(result.translation_base_to_camera[1])
        transform.transform.translation.z = float(result.translation_base_to_camera[2])
        qx, qy, qz, qw = quaternion_from_rotation_matrix(result.rotation_base_to_camera)
        transform.transform.rotation.x = qx
        transform.transform.rotation.y = qy
        transform.transform.rotation.z = qz
        transform.transform.rotation.w = qw
        self._tf_broadcaster.sendTransform(transform)

    def _log_throttled(self, message: str, period_sec: float = 2.0) -> None:
        now = self.get_clock().now()
        if now.nanoseconds - self._last_publish_ns >= int(period_sec * 1e9):
            self.get_logger().info(message)
            self._last_publish_ns = now.nanoseconds


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = GridPnPCalibratorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
