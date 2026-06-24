"""Convert RealSense aligned-depth pixels into Dobot/base-frame points."""

from __future__ import annotations

import math
import struct
from typing import Iterable

import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PointStamped
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformException, TransformListener
import tf2_geometry_msgs  # noqa: F401 - registers PointStamped transform helpers


def deproject_pixel_to_point(
    *,
    u: int,
    v: int,
    depth_raw: float,
    encoding: str,
    k: Iterable[float],
) -> tuple[float, float, float] | None:
    """Return camera optical-frame XYZ meters for one depth pixel."""
    if depth_raw is None:
        return None

    depth_value = float(depth_raw)
    if not math.isfinite(depth_value) or depth_value <= 0.0:
        return None

    normalized_encoding = encoding.upper()
    if normalized_encoding in {"16UC1", "MONO16"}:
        z = depth_value / 1000.0
    elif normalized_encoding == "32FC1":
        z = depth_value
    else:
        raise ValueError(f"Unsupported depth encoding: {encoding}")

    intrinsics = list(k)
    if len(intrinsics) < 6:
        raise ValueError("CameraInfo.k must contain at least 6 values")

    fx = float(intrinsics[0])
    fy = float(intrinsics[4])
    cx = float(intrinsics[2])
    cy = float(intrinsics[5])
    if fx == 0.0 or fy == 0.0:
        raise ValueError("CameraInfo.k has invalid fx/fy")

    x = (float(u) - cx) * z / fx
    y = (float(v) - cy) * z / fy
    return x, y, z


def read_depth_pixel(image: Image, u: int, v: int) -> float | None:
    """Read one depth sample from a ROS Image without cv_bridge."""
    if u < 0 or v < 0 or u >= image.width or v >= image.height:
        return None

    encoding = image.encoding.upper()
    if encoding in {"16UC1", "MONO16"}:
        byte_count = 2
        fmt = ">H" if image.is_bigendian else "<H"
    elif encoding == "32FC1":
        byte_count = 4
        fmt = ">f" if image.is_bigendian else "<f"
    else:
        raise ValueError(f"Unsupported depth encoding: {image.encoding}")

    offset = int(v) * image.step + int(u) * byte_count
    end = offset + byte_count
    if end > len(image.data):
        return None

    return struct.unpack(fmt, bytes(image.data[offset:end]))[0]


class PixelToBaseNode(Node):
    """Subscribe to aligned depth and publish the selected pixel in base frame."""

    def __init__(self) -> None:
        super().__init__("pixel_to_base_node")

        self.declare_parameter(
            "aligned_depth_topic", "/camera/camera/aligned_depth_to_color/image_raw"
        )
        self.declare_parameter(
            "camera_info_topic", "/camera/camera/aligned_depth_to_color/camera_info"
        )
        self.declare_parameter("target_frame", "magician_base_link")
        self.declare_parameter("pixel_u", 320)
        self.declare_parameter("pixel_v", 240)
        self.declare_parameter("tf_timeout_sec", 0.2)
        self.declare_parameter("camera_point_topic", "/dobot_control/target_point_camera")
        self.declare_parameter("base_point_topic", "/dobot_control/target_point_base")

        self._camera_info: CameraInfo | None = None
        self._last_log_time = self.get_clock().now()

        aligned_depth_topic = self.get_parameter("aligned_depth_topic").value
        camera_info_topic = self.get_parameter("camera_info_topic").value
        camera_point_topic = self.get_parameter("camera_point_topic").value
        base_point_topic = self.get_parameter("base_point_topic").value

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        self._camera_point_pub = self.create_publisher(PointStamped, camera_point_topic, 10)
        self._base_point_pub = self.create_publisher(PointStamped, base_point_topic, 10)
        self.create_subscription(
            CameraInfo,
            camera_info_topic,
            self._camera_info_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Image,
            aligned_depth_topic,
            self._depth_callback,
            qos_profile_sensor_data,
        )

        self.get_logger().info(
            "pixel_to_base_node ready: depth=%s, camera_info=%s, target_frame=%s"
            % (aligned_depth_topic, camera_info_topic, self.get_parameter("target_frame").value)
        )

    def _camera_info_callback(self, msg: CameraInfo) -> None:
        self._camera_info = msg

    def _depth_callback(self, msg: Image) -> None:
        if self._camera_info is None:
            self._log_throttled("Waiting for CameraInfo...")
            return

        u = int(self.get_parameter("pixel_u").value)
        v = int(self.get_parameter("pixel_v").value)
        target_frame = str(self.get_parameter("target_frame").value)
        tf_timeout_sec = float(self.get_parameter("tf_timeout_sec").value)

        try:
            depth_raw = read_depth_pixel(msg, u, v)
            camera_xyz = deproject_pixel_to_point(
                u=u,
                v=v,
                depth_raw=depth_raw,
                encoding=msg.encoding,
                k=self._camera_info.k,
            )
        except ValueError as exc:
            self.get_logger().error(str(exc))
            return

        if camera_xyz is None:
            self._log_throttled(f"Invalid depth at pixel ({u}, {v})")
            return

        source_frame = self._camera_info.header.frame_id or msg.header.frame_id
        if not source_frame:
            source_frame = "camera_color_optical_frame"

        camera_point = PointStamped()
        if msg.header.stamp != Time():
            camera_point.header.stamp = msg.header.stamp
        else:
            camera_point.header.stamp = self.get_clock().now().to_msg()
        camera_point.header.frame_id = source_frame
        camera_point.point.x = camera_xyz[0]
        camera_point.point.y = camera_xyz[1]
        camera_point.point.z = camera_xyz[2]
        self._camera_point_pub.publish(camera_point)

        try:
            base_point = self._tf_buffer.transform(
                camera_point,
                target_frame,
                timeout=Duration(seconds=tf_timeout_sec),
            )
        except TransformException as exc:
            self._log_throttled(
                f"Waiting for TF {target_frame} <- {source_frame}: {exc}"
            )
            return

        self._base_point_pub.publish(base_point)
        self._log_throttled(
            "pixel (%d,%d), camera[%s]=(%.3f, %.3f, %.3f), %s=(%.3f, %.3f, %.3f)"
            % (
                u,
                v,
                source_frame,
                camera_point.point.x,
                camera_point.point.y,
                camera_point.point.z,
                target_frame,
                base_point.point.x,
                base_point.point.y,
                base_point.point.z,
            )
        )

    def _log_throttled(self, message: str, period_sec: float = 1.0) -> None:
        now = self.get_clock().now()
        if (now - self._last_log_time).nanoseconds >= int(period_sec * 1e9):
            self.get_logger().info(message)
            self._last_log_time = now


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = PixelToBaseNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
