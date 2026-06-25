"""Interactive red plate center calibration and Dobot movement test node."""

from __future__ import annotations

import json
import math
import queue
import sys
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Float64MultiArray, String

from dobot_control.red_plate_calibration import (
    RedPlateDetection,
    RedPlateDetectionError,
    RedPlateHsvThresholds,
    PixelToBaseCalibration,
    apply_pixel_to_base_xy,
    build_red_debug_images,
    calibration_to_json,
    detect_red_plate,
    estimate_pixel_to_base_calibration,
    pose_xy_to_action_target,
    save_calibration,
)


COMMAND_HELPER_LAUNCH = "ros2 launch dobot_control red_plate_command.launch.py"
STATUS_TOPIC_DEFAULT = "/dobot_control/red_plate_calibration/status"


def command_helper_command(choice: str) -> str:
    """Return the short launch command for one interactive choice."""
    return f"{COMMAND_HELPER_LAUNCH} command:={choice}"


def compact_choice_hint(valid: set[str]) -> str:
    """Return a concise command hint for the current valid choices."""
    choices = [choice for choice in sorted(valid) if choice]
    if not choices:
        return "명령: Enter"
    if len(choices) == 1:
        return f"명령: {command_helper_command(choices[0])}"
    return f"명령: {COMMAND_HELPER_LAUNCH} command:=<번호>  ({'/'.join(choices)})"


try:
    from dobot_msgs.action import PointToPoint
except ImportError:  # pragma: no cover - depends on external Dobot workspace overlay.
    PointToPoint = None


@dataclass(frozen=True)
class CalibrationSample:
    pixel_center: tuple[float, float]
    corners: list[list[float]]
    tcp_pose_m: list[float]
    quality: float
    timestamp: str


def make_calibration_sample(
    *,
    detection: RedPlateDetection,
    tcp_pose_m: list[float],
    timestamp: str | None = None,
) -> CalibrationSample:
    """Pair a previously visible red-plate detection with a later TCP pose."""
    return CalibrationSample(
        pixel_center=detection.center,
        corners=detection.corners.astype(float).tolist(),
        tcp_pose_m=list(tcp_pose_m),
        quality=detection.quality,
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
    )


def image_msg_to_bgr(msg: Image) -> np.ndarray:
    """Convert bgr8/rgb8/mono8 ROS Image to an OpenCV BGR image."""
    encoding = msg.encoding.lower()
    data = np.frombuffer(bytes(msg.data), dtype=np.uint8)
    expected = msg.height * msg.step
    if data.size < expected:
        raise ValueError("image data is shorter than height * step")
    packed = data[:expected].reshape(msg.height, msg.step)
    if encoding in {"bgr8", "rgb8"}:
        image = packed[:, : msg.width * 3].reshape(msg.height, msg.width, 3)
        if encoding == "rgb8":
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        return image.copy()
    if encoding in {"mono8", "8uc1"}:
        return cv2.cvtColor(packed[:, : msg.width], cv2.COLOR_GRAY2BGR)
    raise ValueError(f"unsupported image encoding: {msg.encoding}")


def cv_image_to_msg(image: np.ndarray, *, encoding: str, header: Any) -> Image:
    """Convert a mono8 or bgr8 OpenCV image into a ROS Image message."""
    msg = Image()
    msg.header = header
    msg.height = int(image.shape[0])
    msg.width = int(image.shape[1])
    msg.encoding = encoding
    msg.is_bigendian = False
    channels = 1 if image.ndim == 2 else int(image.shape[2])
    msg.step = int(msg.width * channels)
    msg.data = np.ascontiguousarray(image).tobytes()
    return msg


class RedPlateInteractiveCalibrator(Node):
    """Collect red-plate samples and test a planar pixel-to-base mapping."""

    def __init__(self) -> None:
        super().__init__("red_plate_interactive_calibrator")
        self.declare_parameter("image_topic", "/camera/camera/color/image_raw")
        self.declare_parameter("tcp_pose_topic", "dobot_pose_raw")
        self.declare_parameter("result_topic", "/dobot_control/red_plate_calibration/result")
        self.declare_parameter("command_topic", "/dobot_control/red_plate_calibration/command")
        self.declare_parameter("status_topic", STATUS_TOPIC_DEFAULT)
        self.declare_parameter("debug_publish_images", True)
        self.declare_parameter("debug_mask_topic", "/dobot_control/red_plate/debug_mask")
        self.declare_parameter("debug_red_only_topic", "/dobot_control/red_plate/debug_red_only")
        self.declare_parameter("debug_overlay_topic", "/dobot_control/red_plate/debug_overlay")
        self.declare_parameter(
            "calibration_save_path",
            "~/red_plate_pixel_to_base_calibration.json",
        )
        self.declare_parameter("expected_aspect_ratio", 5.0 / 3.4)
        self.declare_parameter("min_area_px", 800.0)
        self.declare_parameter("min_quality", 0.55)
        self.declare_parameter("ambiguity_ratio", 0.85)
        self.declare_parameter("hsv_lower_red1", "0,120,70")
        self.declare_parameter("hsv_upper_red1", "10,255,255")
        self.declare_parameter("hsv_lower_red2", "170,120,70")
        self.declare_parameter("hsv_upper_red2", "180,255,255")
        self.declare_parameter("min_samples", 4)
        self.declare_parameter("z_hover_offset_m", 0.04)
        self.declare_parameter("min_z_m", 0.02)
        self.declare_parameter("target_r_deg", 0.0)
        self.declare_parameter("motion_type", 2)
        self.declare_parameter("velocity_ratio", 0.3)
        self.declare_parameter("acceleration_ratio", 0.3)
        self.declare_parameter("dry_run", False)
        self.declare_parameter("action_name", "PTP_action")
        self.declare_parameter("tcp_xyz_units", "m")

        self._latest_image: Image | None = None
        self._latest_tcp: list[float] | None = None
        self._image_count = 0
        self._tcp_count = 0
        self._samples: list[CalibrationSample] = []
        self._calibration: PixelToBaseCalibration | None = None
        self._last_target: dict[str, Any] | None = None
        self._input_queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._status_seq = 0

        self._result_pub = self.create_publisher(
            String,
            str(self.get_parameter("result_topic").value),
            10,
        )
        self._status_pub = self.create_publisher(
            String,
            str(self.get_parameter("status_topic").value),
            10,
        )
        self._debug_publish_images = bool(self.get_parameter("debug_publish_images").value)
        self._debug_mask_pub = self.create_publisher(
            Image,
            str(self.get_parameter("debug_mask_topic").value),
            10,
        )
        self._debug_red_only_pub = self.create_publisher(
            Image,
            str(self.get_parameter("debug_red_only_topic").value),
            10,
        )
        self._debug_overlay_pub = self.create_publisher(
            Image,
            str(self.get_parameter("debug_overlay_topic").value),
            10,
        )
        self.create_subscription(
            Image,
            str(self.get_parameter("image_topic").value),
            self._image_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Float64MultiArray,
            str(self.get_parameter("tcp_pose_topic").value),
            self._tcp_callback,
            10,
        )
        self.create_subscription(
            String,
            str(self.get_parameter("command_topic").value),
            self._command_callback,
            10,
        )
        self._action_client = None
        if PointToPoint is not None:
            self._action_client = ActionClient(
                self,
                PointToPoint,
                str(self.get_parameter("action_name").value),
            )

    def _parse_hsv_triplet(self, parameter_name: str) -> tuple[int, int, int]:
        raw = str(self.get_parameter(parameter_name).value)
        try:
            values = [int(part.strip()) for part in raw.split(",")]
        except ValueError as exc:
            raise ValueError(f"{parameter_name} must be comma-separated HSV integers") from exc
        if len(values) != 3:
            raise ValueError(f"{parameter_name} must have exactly 3 values, got {raw!r}")
        h, s, v = values
        return max(0, min(180, h)), max(0, min(255, s)), max(0, min(255, v))

    def _hsv_thresholds(self) -> RedPlateHsvThresholds:
        return RedPlateHsvThresholds(
            lower_red_1=self._parse_hsv_triplet("hsv_lower_red1"),
            upper_red_1=self._parse_hsv_triplet("hsv_upper_red1"),
            lower_red_2=self._parse_hsv_triplet("hsv_lower_red2"),
            upper_red_2=self._parse_hsv_triplet("hsv_upper_red2"),
        )

    def _image_callback(self, msg: Image) -> None:
        self._latest_image = msg
        self._image_count += 1
        if self._debug_publish_images:
            try:
                image_bgr = image_msg_to_bgr(msg)
                mask, red_only, overlay = build_red_debug_images(
                    image_bgr,
                    thresholds=self._hsv_thresholds(),
                )
            except ValueError as exc:
                self.get_logger().warn(f"red debug image publish skipped: {exc}")
                return
            self._debug_mask_pub.publish(
                cv_image_to_msg(mask, encoding="mono8", header=msg.header)
            )
            self._debug_red_only_pub.publish(
                cv_image_to_msg(red_only, encoding="bgr8", header=msg.header)
            )
            self._debug_overlay_pub.publish(
                cv_image_to_msg(overlay, encoding="bgr8", header=msg.header)
            )

    def _tcp_callback(self, msg: Float64MultiArray) -> None:
        values = [float(value) for value in msg.data]
        if len(values) < 3:
            return
        self._tcp_count += 1
        units = str(self.get_parameter("tcp_xyz_units").value).lower()
        if units == "mm":
            values[0] /= 1000.0
            values[1] /= 1000.0
            values[2] /= 1000.0
        self._latest_tcp = values

    def _command_callback(self, msg: String) -> None:
        command = msg.data.strip()
        self._input_queue.put(command)
        print(f"✓ 입력 command:={command}", flush=True)

    def _publish_status(
        self,
        *,
        event: str,
        title: str,
        lines: list[str],
        valid: set[str] | None = None,
    ) -> None:
        self._status_seq += 1
        msg = String()
        msg.data = json.dumps(
            {
                "event": event,
                "seq": self._status_seq,
                "title": title,
                "lines": lines,
                "valid": sorted(choice for choice in (valid or set()) if choice),
            },
            ensure_ascii=False,
        )
        self._status_pub.publish(msg)

    def _print_panel(self, title: str, lines: list[str]) -> None:
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
        print(f"▶ {title}", flush=True)
        for line in lines:
            print(f"  {line}", flush=True)
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)

    def _show_status(self, event: str, title: str, lines: list[str]) -> None:
        self._print_panel(title, lines)
        self._publish_status(event=event, title=title, lines=lines)

    def _stdin_thread(self) -> None:
        while not self._stop_event.is_set():
            line = sys.stdin.readline()
            if not line:
                self._stop_event.set()
                return
            self._input_queue.put(line.strip())

    def _read_choice(self, prompt: str, valid: set[str]) -> str:
        lines = [prompt, compact_choice_hint(valid)]
        self._print_panel("다음 선택", lines)
        self._publish_status(event="prompt", title="다음 선택", lines=lines, valid=valid)
        last_status_time = self.get_clock().now()
        while rclpy.ok() and not self._stop_event.is_set():
            try:
                choice = self._input_queue.get(timeout=0.1)
            except queue.Empty:
                now = self.get_clock().now()
                if (now - last_status_time).nanoseconds >= 10_000_000_000:
                    print(
                        f"[대기] image={self._image_count} tcp={self._tcp_count}",
                        flush=True,
                    )
                    last_status_time = now
                continue
            if choice in valid:
                return choice
            choices = "/".join(sorted(choice if choice else "enter" for choice in valid))
            print(f"잘못된 입력: {choice!r} (가능: {choices})", flush=True)
        return ""

    def _detect_latest(self) -> RedPlateDetection:
        if self._latest_image is None:
            raise RedPlateDetectionError("아직 image topic을 받지 못했습니다")
        cv_image = image_msg_to_bgr(self._latest_image)
        return detect_red_plate(
            cv_image,
            thresholds=self._hsv_thresholds(),
            expected_aspect_ratio=float(self.get_parameter("expected_aspect_ratio").value),
            min_area_px=float(self.get_parameter("min_area_px").value),
            min_quality=float(self.get_parameter("min_quality").value),
            ambiguity_ratio=float(self.get_parameter("ambiguity_ratio").value),
        )

    def _capture_plate_center(self) -> RedPlateDetection | None:
        try:
            detection = self._detect_latest()
        except (RedPlateDetectionError, ValueError) as exc:
            self._show_status("error", "검출 실패", [str(exc)])
            return None
        self._show_status(
            "detected",
            "빨간 판 확인",
            [
                "center=(%.1f, %.1f)  quality=%.3f  area=%.0f"
                % (detection.center[0], detection.center[1], detection.quality, detection.area_px),
            ],
        )
        return detection

    def _save_sample_from_detection(self, detection: RedPlateDetection) -> None:
        if self._latest_tcp is None:
            self._show_status("blocker", "저장 불가", ["dobot_pose_raw TCP pose를 아직 받지 못했습니다."])
            return
        sample = make_calibration_sample(detection=detection, tcp_pose_m=self._latest_tcp)
        self._samples.append(sample)
        min_samples = int(self.get_parameter("min_samples").value)
        self._show_status(
            "sample_saved",
            "샘플 저장",
            [
                "count=%d/%d  center=(%.1f, %.1f)"
                % (
                    len(self._samples),
                    min_samples,
                    sample.pixel_center[0],
                    sample.pixel_center[1],
                ),
                "tcp=(%.4f, %.4f, %.4f)  quality=%.3f"
                % (
                    sample.tcp_pose_m[0],
                    sample.tcp_pose_m[1],
                    sample.tcp_pose_m[2],
                    sample.quality,
                ),
            ],
        )
        self._recompute_calibration_if_possible()

    def _add_sample(self) -> None:
        detection = self._capture_plate_center()
        if detection is not None:
            self._save_sample_from_detection(detection)

    def _recompute_calibration_if_possible(self) -> None:
        min_samples = int(self.get_parameter("min_samples").value)
        if len(self._samples) < min_samples:
            self._show_status(
                "waiting_samples",
                "보정 대기",
                [f"샘플 {len(self._samples)}/{min_samples}개 저장됨. 계속 보정하세요."],
            )
            return
        pixels = [sample.pixel_center for sample in self._samples]
        base_xy = [[sample.tcp_pose_m[0], sample.tcp_pose_m[1]] for sample in self._samples]
        try:
            self._calibration = estimate_pixel_to_base_calibration(pixels, base_xy)
        except (RuntimeError, ValueError) as exc:
            self._show_status("error", "보정 실패", [str(exc)])
            return
        result = self._calibration
        self._show_status(
            "calibrated",
            "보정 결과",
            [
                "model=%s  samples=%d  inliers=%d"
                % (result.model_type, result.sample_count, result.inlier_count),
                "XY residual mean/max/RMS=%.5f/%.5f/%.5f m"
                % (result.residual_mean_m, result.residual_max_m, result.residual_rms_m),
            ],
        )

    def _touch_z_m(self) -> float:
        if not self._samples:
            raise RuntimeError("no calibration samples available")
        return float(np.mean([sample.tcp_pose_m[2] for sample in self._samples]))

    def _target_r_deg(self) -> float:
        if self._latest_tcp is not None and len(self._latest_tcp) >= 4:
            return float(self._latest_tcp[3])
        return float(self.get_parameter("target_r_deg").value)

    def _publish_result(self, event: str, payload: dict[str, Any]) -> None:
        msg = String()
        msg.data = json.dumps({"event": event, **payload}, ensure_ascii=False)
        self._result_pub.publish(msg)

    def _run_test_once(self) -> bool:
        min_samples = int(self.get_parameter("min_samples").value)
        if self._calibration is None:
            self._show_status(
                "blocker",
                "테스트 불가",
                [
                    f"보정값 없음: 샘플 {len(self._samples)}/{min_samples}",
                    f"샘플 {min_samples}개 저장 후 테스트하세요. 다음 선택은 3(보정 이어서).",
                ],
            )
            return False
        try:
            detection = self._detect_latest()
        except (RedPlateDetectionError, ValueError) as exc:
            self._show_status("error", "검출 실패", [str(exc)])
            return False
        x_m, y_m = apply_pixel_to_base_xy(self._calibration, detection.center)
        raw_z_m = self._touch_z_m() + float(self.get_parameter("z_hover_offset_m").value)
        min_z_m = float(self.get_parameter("min_z_m").value)
        if not math.isfinite(min_z_m):
            self._show_status("error", "테스트 실패", ["min_z_m must be finite"])
            return False
        z_m = max(min_z_m, raw_z_m)
        r_deg = self._target_r_deg()
        target_pose = pose_xy_to_action_target(x_m=x_m, y_m=y_m, z_m=z_m, yaw_deg=r_deg)
        self._last_target = {
            "pixel_center": detection.center,
            "target_base_m": [x_m, y_m, z_m, r_deg],
            "raw_target_z_m": raw_z_m,
            "min_z_m": min_z_m,
            "target_action_units": target_pose,
            "quality": detection.quality,
        }
        self._publish_result("test_target", self._last_target)
        target_lines = [
            "center=(%.1f, %.1f)" % (detection.center[0], detection.center[1]),
            "target=(%.4f, %.4f, %.4f, %.2fdeg)" % (x_m, y_m, z_m, r_deg),
        ]
        if z_m > raw_z_m:
            target_lines.append(
                "z clamped: raw_z=%.4f < min_z_m=%.4f" % (raw_z_m, min_z_m)
            )
        self._show_status(
            "test_target",
            "테스트 목표",
            target_lines,
        )
        self._send_motion_goal(target_pose)
        return True

    def _send_motion_goal(self, target_pose: list[float]) -> None:
        if bool(self.get_parameter("dry_run").value):
            self._show_status("dry_run", "dry-run", [f"Dobot 이동 명령 생략: {target_pose}"])
            return
        if PointToPoint is None or self._action_client is None:
            self._show_status(
                "blocker",
                "이동 불가",
                [
                    "dobot_msgs.action.PointToPoint import 실패",
                    "magician_ros2_control_system_ws/install/setup.bash를 source 후 실행하세요.",
                ],
            )
            return
        if not self._action_client.wait_for_server(timeout_sec=3.0):
            self._show_status("blocker", "이동 불가", ["PTP_action action server가 없습니다."])
            return
        goal = PointToPoint.Goal()
        goal.motion_type = int(self.get_parameter("motion_type").value)
        goal.target_pose = target_pose
        goal.velocity_ratio = float(self.get_parameter("velocity_ratio").value)
        goal.acceleration_ratio = float(self.get_parameter("acceleration_ratio").value)
        future = self._action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        goal_handle = future.result()
        if goal_handle is None or not goal_handle.accepted:
            self._show_status("error", "이동 실패", ["PTP goal rejected"])
            return
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=30.0)
        result = result_future.result()
        self._show_status("motion_done", "이동 완료", [f"achieved_pose={result.result.achieved_pose}"])

    def _save_approved(self) -> None:
        if self._calibration is None:
            self._show_status("blocker", "저장 실패", ["보정값 없음"])
            return
        path = str(self.get_parameter("calibration_save_path").value)
        save_calibration(path, self._calibration)
        sample_path = str(Path(path).expanduser().with_suffix(".samples.json"))
        Path(sample_path).write_text(
            json.dumps([asdict(sample) for sample in self._samples], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._publish_result(
            "approved_saved",
            {
                "calibration_path": str(Path(path).expanduser()),
                "samples_path": sample_path,
                "calibration": json.loads(calibration_to_json(self._calibration)),
            },
        )
        self._show_status(
            "approved_saved",
            "저장 완료",
            [
                f"calibration: {Path(path).expanduser()}",
                f"samples: {sample_path}",
            ],
        )

    def run_interactive(self) -> None:
        threading.Thread(target=self._stdin_thread, daemon=True).start()
        self._show_status(
            "started",
            "빨간 판 보정 시작",
            [
                "1) 판 중심 확인 → 2) TCP를 중심 위로 이동 → 3) 샘플 저장",
                "기본 4개 샘플 후 테스트/저장 가능",
                f"도움말: {COMMAND_HELPER_LAUNCH}",
            ],
        )
        while rclpy.ok() and not self._stop_event.is_set():
            choice = self._read_choice(
                "빨간 판이 보이면 1: 중심 확인",
                {"", "1"},
            )
            if choice not in {"", "1"}:
                return
            detection = self._capture_plate_center()
            if detection is None:
                continue
            next_choice = self._read_choice(
                "이제 엔드이펙터(TCP)를 방금 확인한 중심 위로 맞춘 뒤: "
                "1=샘플 저장, 2=중심 다시 확인",
                {"1", "2"},
            )
            if next_choice == "2":
                continue
            if next_choice == "1":
                self._save_sample_from_detection(detection)
            next_choice = self._read_choice("1=다시 보정, 2=보정 끝/테스트", {"1", "2"})
            if next_choice == "1":
                continue
            if next_choice == "2":
                break
        while rclpy.ok() and not self._stop_event.is_set():
            choice = self._read_choice("빨간 판을 테스트 위치에 둔 뒤 1=테스트 실행", {"1"})
            if choice != "1":
                return
            test_started = self._run_test_once()
            if not test_started:
                next_choice = self._read_choice(
                    "2=다시 테스트, 3=보정 이어서",
                    {"2", "3"},
                )
                if next_choice == "2":
                    continue
                if next_choice == "3":
                    self.run_interactive()
                    return
            next_choice = self._read_choice(
                "1=저장 후 종료, 2=다시 테스트, 3=보정 이어서",
                {"1", "2", "3"},
            )
            if next_choice == "1":
                self._save_approved()
                return
            if next_choice == "2":
                continue
            if next_choice == "3":
                self.run_interactive()
                return


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = RedPlateInteractiveCalibrator()
    executor_thread = threading.Thread(target=lambda: rclpy.spin(node), daemon=True)
    executor_thread.start()
    try:
        node.run_interactive()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node._stop_event.set()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        executor_thread.join(timeout=1.0)


if __name__ == "__main__":
    main()
