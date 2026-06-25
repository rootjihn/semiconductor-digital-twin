#!/usr/bin/env python3
"""
Save RealSense color image topic frames as JPG files for YOLO dataset collection.

Default behavior matches the current SSAFY project setup:
- ROS_DOMAIN_ID defaults to 125 when not already set.
- Subscribes to /camera/camera/color/image_raw with sensor-data QoS.
- Saves about 2 images per second under
  /home/ssafy/penetrate_pjt/datasets/floor_images/raw.
- File names look like floor_YYYYmmdd_HHMMSS_000001.jpg.

Run with ROS Humble Python, for example:

    source /opt/ros/humble/setup.bash
    cd /home/ssafy/penetrate_pjt/main_ws
    source install/setup.bash
    export ROS_DOMAIN_ID=125
    /usr/bin/python3 src/yolo_v5/scripts/collect_realsense_images.py
"""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import signal
import sys
import time
from typing import Optional

# rclpy reads ROS_DOMAIN_ID from the environment at init time. Set the project
# default before importing/initializing ROS if the operator did not set it.
os.environ.setdefault("ROS_DOMAIN_ID", "125")

import cv2  # noqa: E402
from cv_bridge import CvBridge, CvBridgeError  # noqa: E402
import rclpy  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import qos_profile_sensor_data  # noqa: E402
from sensor_msgs.msg import Image  # noqa: E402


DEFAULT_IMAGE_TOPIC = "/camera/camera/color/image_raw"
DEFAULT_OUTPUT_DIR = "/home/ssafy/penetrate_pjt/datasets/floor_images/raw"
DEFAULT_RATE_HZ = 2.0
DEFAULT_PREFIX = "floor"


class RealSenseImageCollector(Node):
    """ROS2 node that throttles an image topic and saves frames as JPG."""

    def __init__(
        self,
        *,
        image_topic: str,
        output_dir: Path,
        rate_hz: float,
        prefix: str,
        jpeg_quality: int,
        max_images: int,
        log_every: int,
    ) -> None:
        super().__init__("realsense_image_collector")
        if rate_hz <= 0.0:
            raise ValueError("rate_hz must be positive")
        if not 1 <= jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100")

        self.image_topic = image_topic
        self.output_dir = output_dir
        self.rate_hz = rate_hz
        self.min_interval_sec = 1.0 / rate_hz
        self.prefix = prefix
        self.jpeg_quality = jpeg_quality
        self.max_images = max(0, max_images)
        self.log_every = max(1, log_every)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.bridge = CvBridge()
        self.received_count = 0
        self.saved_count = 0
        self.failed_count = 0
        self.last_save_time = 0.0
        self.stop_requested = False
        self.first_image_time: Optional[float] = None

        self.subscription = self.create_subscription(
            Image,
            self.image_topic,
            self._image_callback,
            qos_profile_sensor_data,
        )
        self.status_timer = self.create_timer(5.0, self._log_waiting_status)

        domain_id = os.environ.get("ROS_DOMAIN_ID", "")
        self.get_logger().info(
            "RealSense image collector ready: "
            f"topic={self.image_topic}, output_dir={self.output_dir}, "
            f"rate_hz={self.rate_hz:.3f}, ROS_DOMAIN_ID={domain_id or '<unset>'}"
        )
        self.get_logger().info("Press Ctrl+C to stop safely.")

    def _image_callback(self, msg: Image) -> None:
        self.received_count += 1
        now = time.monotonic()
        if self.first_image_time is None:
            self.first_image_time = now
            self.get_logger().info(
                "First image received: "
                f"{msg.width}x{msg.height}, encoding={msg.encoding}, "
                f"frame_id={msg.header.frame_id}"
            )

        if now - self.last_save_time < self.min_interval_sec:
            return
        if self.max_images and self.saved_count >= self.max_images:
            self.stop_requested = True
            return

        next_index = self.saved_count + 1
        filename = f"{self.prefix}_{self.session_stamp}_{next_index:06d}.jpg"
        output_path = self.output_dir / filename

        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            ok = cv2.imwrite(
                str(output_path),
                cv_image,
                [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality],
            )
            if not ok:
                raise RuntimeError("cv2.imwrite returned False")
        except (CvBridgeError, RuntimeError, OSError) as exc:
            self.failed_count += 1
            self.get_logger().error(f"Failed to save image #{next_index}: {exc}")
            return

        self.saved_count = next_index
        self.last_save_time = now

        if self.saved_count == 1 or self.saved_count % self.log_every == 0:
            self.get_logger().info(
                f"Saved {self.saved_count} image(s): {output_path} "
                f"(received={self.received_count}, failed={self.failed_count})"
            )

        if self.max_images and self.saved_count >= self.max_images:
            self.get_logger().info(f"Reached max_images={self.max_images}; stopping.")
            self.stop_requested = True

    def _log_waiting_status(self) -> None:
        if self.received_count == 0:
            self.get_logger().warn(
                "No image received yet. Check RealSense launch, ROS_DOMAIN_ID, "
                f"and topic name: {self.image_topic}"
            )
        else:
            self.get_logger().info(
                f"Status: received={self.received_count}, saved={self.saved_count}, "
                f"failed={self.failed_count}, output_dir={self.output_dir}"
            )

    def summary(self) -> str:
        return (
            f"received={self.received_count}, saved={self.saved_count}, "
            f"failed={self.failed_count}, output_dir={self.output_dir}"
        )


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Save RealSense ROS2 color image frames as JPG files."
    )
    parser.add_argument(
        "--image-topic",
        default=DEFAULT_IMAGE_TOPIC,
        help=f"Input image topic. Default: {DEFAULT_IMAGE_TOPIC}",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save JPG images. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--rate-hz",
        type=float,
        default=DEFAULT_RATE_HZ,
        help=f"Maximum save rate in images/sec. Default: {DEFAULT_RATE_HZ}",
    )
    parser.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help=f"Filename prefix. Default: {DEFAULT_PREFIX}",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=95,
        help="JPEG quality 1-100. Default: 95",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=0,
        help="Stop after this many saved images. 0 means unlimited. Default: 0",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=10,
        help="Log every N saved images after the first. Default: 10",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir).expanduser().resolve()

    rclpy.init(args=None)
    node = RealSenseImageCollector(
        image_topic=args.image_topic,
        output_dir=output_dir,
        rate_hz=args.rate_hz,
        prefix=args.prefix,
        jpeg_quality=args.jpeg_quality,
        max_images=args.max_images,
        log_every=args.log_every,
    )

    should_stop = {"value": False}

    def request_stop(signum, _frame):  # type: ignore[no-untyped-def]
        should_stop["value"] = True
        node.stop_requested = True
        node.get_logger().info(f"Signal {signum} received; shutting down after current callback.")

    previous_sigint = signal.getsignal(signal.SIGINT)
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    try:
        while rclpy.ok() and not should_stop["value"] and not node.stop_requested:
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        node.get_logger().info("KeyboardInterrupt received; shutting down.")
    finally:
        node.get_logger().info("Final summary: " + node.summary())
        node.destroy_node()
        rclpy.shutdown()
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
