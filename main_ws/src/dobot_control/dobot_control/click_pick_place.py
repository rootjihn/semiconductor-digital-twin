"""Click-based Dobot pick/place using saved red-plate pixel-to-base calibration."""

from __future__ import annotations

import json
import math
import signal
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Float64MultiArray

from dobot_control.image_crop_viewer import (
    CropSetting,
    build_crop_setting,
    image_msg_to_bgr,
    load_crop_setting,
    order_crop_points,
    save_crop_setting,
)
from dobot_control.red_plate_calibration import (
    PixelToBaseCalibration,
    apply_pixel_to_base_xy,
    load_calibration,
    pose_xy_to_action_target,
)

try:
    from dobot_msgs.action import PointToPoint
except ImportError:  # pragma: no cover - depends on external Dobot overlay.
    PointToPoint = None

try:
    from dobot_msgs.srv import SuctionCupControl
except ImportError:  # pragma: no cover - depends on external Dobot overlay.
    SuctionCupControl = None


@dataclass(frozen=True)
class DisplayTransform:
    """Map between displayed preview coordinates and original image coordinates."""

    crop_x: int
    crop_y: int
    crop_w: int
    crop_h: int
    display_w: int
    display_h: int

    def __post_init__(self) -> None:
        if self.crop_w <= 0 or self.crop_h <= 0:
            raise ValueError("crop_w and crop_h must be positive")
        if self.display_w <= 0 or self.display_h <= 0:
            raise ValueError("display_w and display_h must be positive")

    def display_to_image(self, u_disp: float, v_disp: float) -> tuple[float, float]:
        """Convert one displayed preview pixel to the original image pixel."""
        x_img = self.crop_x + float(u_disp) * self.crop_w / self.display_w
        y_img = self.crop_y + float(v_disp) * self.crop_h / self.display_h
        return x_img, y_img

    def image_to_display(self, x_img: float, y_img: float) -> tuple[float, float]:
        """Convert one original image pixel to the displayed preview pixel."""
        u_disp = (float(x_img) - self.crop_x) * self.display_w / self.crop_w
        v_disp = (float(y_img) - self.crop_y) * self.display_h / self.crop_h
        return u_disp, v_disp


@dataclass(frozen=True)
class PerspectiveDisplayTransform:
    """Map between a perspective-cropped preview and original image coordinates."""

    crop_setting: CropSetting
    display_w: int
    display_h: int
    source_to_crop: np.ndarray
    crop_to_source: np.ndarray

    def __post_init__(self) -> None:
        if self.crop_setting.output_width <= 0 or self.crop_setting.output_height <= 0:
            raise ValueError("crop output size must be positive")
        if self.display_w <= 0 or self.display_h <= 0:
            raise ValueError("display_w and display_h must be positive")

    @property
    def crop_w(self) -> int:
        return int(self.crop_setting.output_width)

    @property
    def crop_h(self) -> int:
        return int(self.crop_setting.output_height)

    def display_to_image(self, u_disp: float, v_disp: float) -> tuple[float, float]:
        """Convert one displayed perspective-crop pixel to the original image pixel."""
        u_crop = float(u_disp) * self.crop_w / self.display_w
        v_crop = float(v_disp) * self.crop_h / self.display_h
        return _perspective_point(self.crop_to_source, u_crop, v_crop)

    def image_to_display(self, x_img: float, y_img: float) -> tuple[float, float]:
        """Convert one original image pixel to the displayed perspective-crop pixel."""
        u_crop, v_crop = _perspective_point(self.source_to_crop, x_img, y_img)
        return u_crop * self.display_w / self.crop_w, v_crop * self.display_h / self.crop_h


DisplayTransformLike = DisplayTransform | PerspectiveDisplayTransform


def _perspective_point(matrix: np.ndarray, x: float, y: float) -> tuple[float, float]:
    point = np.array([float(x), float(y), 1.0], dtype=np.float64)
    mapped = np.asarray(matrix, dtype=np.float64) @ point
    if abs(float(mapped[2])) < 1e-12:
        raise ValueError("perspective transform produced a point at infinity")
    return float(mapped[0] / mapped[2]), float(mapped[1] / mapped[2])


def build_perspective_display_transform(
    setting: CropSetting,
    *,
    display_w: int,
    display_h: int,
) -> PerspectiveDisplayTransform:
    """Create a perspective crop/resize transform from saved four-point crop settings."""
    out_w = int(setting.output_width) if int(display_w) <= 0 else int(display_w)
    out_h = int(setting.output_height) if int(display_h) <= 0 else int(display_h)
    src = order_crop_points(setting.points)
    dst = np.array(
        [
            [0.0, 0.0],
            [float(setting.output_width - 1), 0.0],
            [float(setting.output_width - 1), float(setting.output_height - 1)],
            [0.0, float(setting.output_height - 1)],
        ],
        dtype=np.float32,
    )
    source_to_crop = cv2.getPerspectiveTransform(src, dst)
    crop_to_source = cv2.getPerspectiveTransform(dst, src)
    return PerspectiveDisplayTransform(
        crop_setting=setting,
        display_w=out_w,
        display_h=out_h,
        source_to_crop=source_to_crop,
        crop_to_source=crop_to_source,
    )


@dataclass(frozen=True)
class ClickMarker:
    """Marker stored in original image coordinates."""

    image_xy: tuple[float, float]
    kind: str
    mode: str


@dataclass(frozen=True)
class PickPlaceStep:
    """One deterministic pick/place operation step."""

    kind: str
    label: str
    motion_type: int | None = None
    target_pose: list[float] | None = None
    suction_enabled: bool | None = None


@dataclass(frozen=True)
class ClickPickPlacePlan:
    """A complete click-derived sequence before ROS action/service execution."""

    mode: str
    display_xy: tuple[float, float]
    image_xy: tuple[float, float]
    base_xy: tuple[float, float]
    steps: list[PickPlaceStep]


@dataclass(frozen=True)
class PlanExecutionResult:
    """Execution logs plus whether every planned step completed."""

    logs: list[str]
    succeeded: bool
    failed_step_label: str | None = None


def marker_kind_for_mode(mode: str | None) -> str:
    """Return the display marker for an attach/detach click mode."""
    if mode == "attach":
        return "+"
    if mode == "detach":
        return "x"
    raise ValueError(f"unsupported click mode: {mode!r}")


def parse_bool(value: Any) -> bool:
    """Parse launch/rclpy bool values without treating 'false' as truthy."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, np.integer)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"cannot parse bool value: {value!r}")


def normalize_descend_distance_m(value: float) -> float:
    """
    Return a downward Z travel distance in meters.

    Operators sometimes type a signed Z offset such as ``-0.01`` to mean
    "go down 1 cm". The parameter is a distance, not an offset, so use the
    magnitude and compute ``descend_z_m = hover_z_m - abs(descend_distance_m)``.
    The resulting target Z may be negative; unreachable targets are left to
    the Dobot action server/trajectory validator instead of being pre-clamped.
    """
    distance = float(value)
    if not math.isfinite(distance):
        raise ValueError("descend_distance_m must be finite")
    return abs(distance)


def compute_descend_z_m(hover_z_m: float, descend_distance_m: float) -> float:
    """Compute final descend target Z, accepting signed operator input and negative Z."""
    hover_z = float(hover_z_m)
    if not math.isfinite(hover_z):
        raise ValueError("hover_z_m must be finite")
    descend_distance = normalize_descend_distance_m(descend_distance_m)
    return hover_z - descend_distance


def make_click_marker(mode: str, image_xy: tuple[float, float]) -> ClickMarker:
    """Build a marker using original image coordinates."""
    return ClickMarker(image_xy=image_xy, kind=marker_kind_for_mode(mode), mode=mode)


def build_display_transform(
    *,
    image_shape: tuple[int, ...],
    crop_x: int,
    crop_y: int,
    crop_w: int,
    crop_h: int,
    display_w: int,
    display_h: int,
) -> DisplayTransform:
    """Create a clipped rectangular crop/resize transform for an image."""
    image_h = int(image_shape[0])
    image_w = int(image_shape[1])
    if image_w <= 0 or image_h <= 0:
        raise ValueError("image_shape must contain positive width/height")

    clipped_x = max(0, min(int(crop_x), image_w - 1))
    clipped_y = max(0, min(int(crop_y), image_h - 1))
    available_w = image_w - clipped_x
    available_h = image_h - clipped_y
    clipped_w = available_w if int(crop_w) <= 0 else min(int(crop_w), available_w)
    clipped_h = available_h if int(crop_h) <= 0 else min(int(crop_h), available_h)
    out_w = clipped_w if int(display_w) <= 0 else int(display_w)
    out_h = clipped_h if int(display_h) <= 0 else int(display_h)

    return DisplayTransform(
        crop_x=clipped_x,
        crop_y=clipped_y,
        crop_w=clipped_w,
        crop_h=clipped_h,
        display_w=out_w,
        display_h=out_h,
    )


def crop_and_resize_preview(image_bgr: np.ndarray, transform: DisplayTransformLike) -> np.ndarray:
    """Return the image region shown in the OpenCV preview window."""
    if isinstance(transform, PerspectiveDisplayTransform):
        crop = cv2.warpPerspective(
            image_bgr,
            transform.source_to_crop,
            (transform.crop_w, transform.crop_h),
        )
        if crop.shape[1] == transform.display_w and crop.shape[0] == transform.display_h:
            return crop
        return cv2.resize(crop, (transform.display_w, transform.display_h))

    x0 = transform.crop_x
    y0 = transform.crop_y
    crop = image_bgr[y0:y0 + transform.crop_h, x0:x0 + transform.crop_w].copy()
    if crop.shape[1] == transform.display_w and crop.shape[0] == transform.display_h:
        return crop
    return cv2.resize(crop, (transform.display_w, transform.display_h))


def _validate_mode(mode: str) -> None:
    if mode not in {"attach", "detach"}:
        raise ValueError("mode must be 'attach' or 'detach'")


def build_click_pick_place_plan(
    *,
    mode: str,
    display_xy: tuple[float, float],
    transform: DisplayTransformLike,
    calibration: PixelToBaseCalibration,
    hover_z_m: float,
    descend_distance_m: float,
    r_deg: float,
    return_to_hover: bool,
    movej_motion_type: int,
    movel_motion_type: int,
) -> ClickPickPlacePlan:
    """Build the MoveJ -> MoveL -> suction -> optional-return sequence for a click."""
    _validate_mode(mode)
    if not all(math.isfinite(float(v)) for v in [hover_z_m, descend_distance_m, r_deg]):
        raise ValueError("hover_z_m, descend_distance_m, and r_deg must be finite")

    image_xy = transform.display_to_image(*display_xy)
    base_x_m, base_y_m = apply_pixel_to_base_xy(calibration, image_xy)
    effective_descend_distance_m = normalize_descend_distance_m(descend_distance_m)
    descend_z_m = compute_descend_z_m(hover_z_m, effective_descend_distance_m)
    hover_pose = pose_xy_to_action_target(
        x_m=base_x_m,
        y_m=base_y_m,
        z_m=hover_z_m,
        yaw_deg=r_deg,
    )
    descend_pose = pose_xy_to_action_target(
        x_m=base_x_m,
        y_m=base_y_m,
        z_m=descend_z_m,
        yaw_deg=r_deg,
    )
    suction_enabled = mode == "attach"
    suction_label = "suction ON" if suction_enabled else "suction OFF"

    steps = [
        PickPlaceStep(
            kind="move",
            label="MoveJ XY hover",
            motion_type=int(movej_motion_type),
            target_pose=hover_pose,
        ),
        PickPlaceStep(
            kind="move",
            label="MoveL descend",
            motion_type=int(movel_motion_type),
            target_pose=descend_pose,
        ),
        PickPlaceStep(
            kind="suction",
            label=suction_label,
            suction_enabled=suction_enabled,
        ),
    ]
    if return_to_hover:
        steps.append(
            PickPlaceStep(
                kind="move",
                label="MoveL return hover",
                motion_type=int(movel_motion_type),
                target_pose=hover_pose,
            )
        )

    return ClickPickPlacePlan(
        mode=mode,
        display_xy=(float(display_xy[0]), float(display_xy[1])),
        image_xy=(float(image_xy[0]), float(image_xy[1])),
        base_xy=(float(base_x_m), float(base_y_m)),
        steps=steps,
    )


def click_log_line(plan: ClickPickPlacePlan) -> str:
    """Return the required click coordinate trace log line."""
    return (
        "[click] mode=%s display=(%.1f, %.1f) image=(%.1f, %.1f) base=(%.4f, %.4f)"
        % (
            plan.mode,
            plan.display_xy[0],
            plan.display_xy[1],
            plan.image_xy[0],
            plan.image_xy[1],
            plan.base_xy[0],
            plan.base_xy[1],
        )
    )


def execute_plan_steps(
    plan: ClickPickPlacePlan,
    *,
    dry_run: bool,
    motion_sender: Callable[[int, list[float]], bool | None],
    suction_sender: Callable[[bool], bool | None],
) -> PlanExecutionResult:
    """Execute or describe a plan; dry-run never calls action/service senders."""
    logs: list[str] = []
    for step in plan.steps:
        if step.kind == "move":
            if step.motion_type is None or step.target_pose is None:
                raise ValueError("move step requires motion_type and target_pose")
            if dry_run:
                logs.append(f"[dry-run] {step.label}: {step.target_pose}")
            else:
                logs.append(f"[motion] {step.label}: {step.target_pose}")
                ok = motion_sender(step.motion_type, step.target_pose)
                if ok is False:
                    logs.append(f"[blocker] sequence stopped after {step.label}")
                    return PlanExecutionResult(logs, False, step.label)
            continue
        if step.kind == "suction":
            if step.suction_enabled is None:
                raise ValueError("suction step requires suction_enabled")
            if dry_run:
                logs.append(f"[dry-run] {step.label}")
            else:
                logs.append(f"[suction] {step.label}")
                ok = suction_sender(step.suction_enabled)
                if ok is False:
                    logs.append(f"[blocker] sequence stopped after {step.label}")
                    return PlanExecutionResult(logs, False, step.label)
            continue
        raise ValueError(f"unsupported step kind: {step.kind!r}")
    return PlanExecutionResult(logs, True)


class ClickPickPlaceNode(Node):
    """OpenCV click UI that runs Dobot pick/place plans from saved calibration."""

    def __init__(self) -> None:
        super().__init__("click_pick_place")
        self.declare_parameter("image_topic", "/camera/camera/color/image_raw")
        self.declare_parameter("calibration_path", "~/red_plate_pixel_to_base_calibration.json")
        self.declare_parameter("tcp_pose_topic", "dobot_pose_raw")
        self.declare_parameter("dry_run", True)
        self.declare_parameter("window_name", "click_pick_place")
        self.declare_parameter("crop_x", 0)
        self.declare_parameter("crop_y", 0)
        self.declare_parameter("crop_w", 0)
        self.declare_parameter("crop_h", 0)
        self.declare_parameter("display_w", 0)
        self.declare_parameter("display_h", 0)
        self.declare_parameter("crop_save_path", "~/image_crop_viewer_crop.json")
        self.declare_parameter("auto_load_crop", True)
        self.declare_parameter("hover_z_m", 0.06)
        self.declare_parameter("descend_distance_m", 0.04)
        self.declare_parameter("r_deg", 0.0)
        self.declare_parameter("return_to_hover", True)
        self.declare_parameter("movej_motion_type", 1)
        self.declare_parameter("movel_motion_type", 2)
        self.declare_parameter("ptp_action_name", "PTP_action")
        self.declare_parameter("suction_service_name", "dobot_suction_cup_service")
        self.declare_parameter("velocity_ratio", 0.3)
        self.declare_parameter("acceleration_ratio", 0.3)
        self.declare_parameter("action_server_timeout_sec", 5.0)
        self.declare_parameter("motion_goal_timeout_sec", 5.0)
        self.declare_parameter("motion_result_timeout_sec", 120.0)
        self.declare_parameter("suction_service_timeout_sec", 5.0)
        self.declare_parameter("suction_response_timeout_sec", 10.0)

        self._frame_lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._latest_transform: DisplayTransformLike | None = None
        self._latest_tcp_pose: list[float] | None = None
        self._closed = False
        self._current_mode: str | None = None
        self._markers: list[ClickMarker] = []
        self._selecting_crop = False
        self._crop_points: list[list[float]] = []
        self._crop_save_path = Path(str(self.get_parameter("crop_save_path").value)).expanduser()
        self._crop_setting: CropSetting | None = self._load_initial_crop_setting()
        self._window_name = str(self.get_parameter("window_name").value)
        self._calibration = self._load_calibration()

        self.create_subscription(
            Image,
            str(self.get_parameter("image_topic").value),
            self._image_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Float64MultiArray,
            str(self.get_parameter("tcp_pose_topic").value),
            self._tcp_pose_callback,
            10,
        )

        self._action_client = None
        if PointToPoint is not None:
            self._action_client = ActionClient(
                self,
                PointToPoint,
                str(self.get_parameter("ptp_action_name").value),
            )
        self._suction_client = None
        if SuctionCupControl is not None:
            self._suction_client = self.create_client(
                SuctionCupControl,
                str(self.get_parameter("suction_service_name").value),
            )

        cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self._window_name, self._mouse_callback)
        self._print_startup_message()

    @property
    def closed(self) -> bool:
        """Return True after q/ESC is pressed."""
        return self._closed

    def request_close(self) -> None:
        """Request loop shutdown from keys or POSIX signal handlers."""
        self._closed = True

    def _load_initial_crop_setting(self) -> CropSetting | None:
        if not parse_bool(self.get_parameter("auto_load_crop").value):
            return None
        if not self._crop_save_path.exists():
            return None
        try:
            setting = load_crop_setting(self._crop_save_path)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.get_logger().warn(f"crop setting load failed: {self._crop_save_path}: {exc}")
            return None
        self.get_logger().info(f"loaded crop setting: {self._crop_save_path}")
        return setting

    def _load_calibration(self) -> PixelToBaseCalibration | None:
        path = Path(str(self.get_parameter("calibration_path").value)).expanduser()
        try:
            calibration = load_calibration(path)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.get_logger().warn(f"calibration load failed: {path}: {exc}")
            return None
        self.get_logger().info(
            "loaded calibration: %s model=%s samples=%d"
            % (path, calibration.model_type, calibration.sample_count)
        )
        return calibration

    @staticmethod
    def _normalize_graph_name(name: str) -> str:
        text = str(name).strip()
        if not text:
            return text
        return text if text.startswith("/") else f"/{text}"

    def _available_action_names(self) -> list[str]:
        try:
            return sorted(name for name, _types in self.get_action_names_and_types())
        except RuntimeError:
            return []

    def _available_service_names(self) -> list[str]:
        try:
            return sorted(name for name, _types in self.get_service_names_and_types())
        except RuntimeError:
            return []

    def _log_robot_bringup_hint(self) -> None:
        self.get_logger().error(
            "[hint] 실제 이동 전 Dobot 제어 스택이 떠 있어야 합니다: "
            "export MAGICIAN_TOOL=suction_cup; "
            "source /home/ssafy/magician_ros2_control_system_ws/src/install/setup.bash; "
            "ros2 launch dobot_bringup dobot_magician_control_system.launch.py"
        )

    def _print_startup_message(self) -> None:
        hover_z = float(self.get_parameter("hover_z_m").value)
        raw_descend_distance = float(self.get_parameter("descend_distance_m").value)
        descend_distance = normalize_descend_distance_m(raw_descend_distance)
        descend_z = compute_descend_z_m(hover_z, raw_descend_distance)
        if raw_descend_distance < 0.0:
            self.get_logger().warn(
                "[param] descend_distance_m=%.4f was negative; "
                "using abs() as %.4f m downward"
                % (raw_descend_distance, descend_distance)
            )
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
        print("▶ click pick/place", flush=True)
        print(f"  image: {self.get_parameter('image_topic').value}", flush=True)
        print(f"  calib: {self.get_parameter('calibration_path').value}", flush=True)
        print(
            f"  crop : {self._crop_save_path} "
            f"(auto_load={self.get_parameter('auto_load_crop').value})",
            flush=True,
        )
        print(f"  dry_run: {self.get_parameter('dry_run').value}", flush=True)
        print(
            "  z: hover_z_m=%.3f, descend_distance_m=%.3f, "
            "effective_descend_m=%.3f, descend_z_m=%.3f"
            % (hover_z, raw_descend_distance, descend_distance, descend_z),
            flush=True,
        )
        if descend_z < 0.0:
            self.get_logger().warn(
                "[param] descend_z_m=%.4f is below 0; sending as requested. "
                "Dobot validation may still reject unreachable targets."
                % descend_z
            )
        print("  키: x=크롭 선택/재선택, r=크롭 해제, a=흡착(+), d=탈착(x), q/ESC=종료", flush=True)
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)

    def _image_callback(self, msg: Image) -> None:
        try:
            frame = image_msg_to_bgr(msg)
        except ValueError as exc:
            self.get_logger().warn(f"image conversion failed: {exc}")
            return
        with self._frame_lock:
            self._latest_frame = frame

    def _tcp_pose_callback(self, msg: Float64MultiArray) -> None:
        self._latest_tcp_pose = [float(value) for value in msg.data]

    def _current_frame(self) -> np.ndarray | None:
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def _build_transform_for_frame(self, frame: np.ndarray) -> DisplayTransformLike:
        if self._crop_setting is not None:
            return build_perspective_display_transform(
                self._crop_setting,
                display_w=int(self.get_parameter("display_w").value),
                display_h=int(self.get_parameter("display_h").value),
            )
        return build_display_transform(
            image_shape=frame.shape,
            crop_x=int(self.get_parameter("crop_x").value),
            crop_y=int(self.get_parameter("crop_y").value),
            crop_w=int(self.get_parameter("crop_w").value),
            crop_h=int(self.get_parameter("crop_h").value),
            display_w=int(self.get_parameter("display_w").value),
            display_h=int(self.get_parameter("display_h").value),
        )

    def update_window(self) -> None:
        """Draw the latest preview frame and process one OpenCV key event."""
        self._redraw_once()
        key = cv2.waitKey(1) & 0xFF
        self._handle_key(key)

    def _redraw_once(self) -> None:
        frame = self._current_frame()
        if frame is None:
            return
        display = self._compose_display(frame)
        cv2.imshow(self._window_name, display)

    def _compose_display(self, frame: np.ndarray) -> np.ndarray:
        if self._selecting_crop:
            self._latest_transform = build_display_transform(
                image_shape=frame.shape,
                crop_x=0,
                crop_y=0,
                crop_w=0,
                crop_h=0,
                display_w=0,
                display_h=0,
            )
            display = frame.copy()
            self._draw_crop_selection_overlay(display)
            return display

        transform = self._build_transform_for_frame(frame)
        self._latest_transform = transform
        display = crop_and_resize_preview(frame, transform)
        self._draw_markers(display, transform)
        self._draw_overlay_text(display)
        return display

    def _draw_markers(self, display: np.ndarray, transform: DisplayTransformLike) -> None:
        for marker in self._markers:
            u, v = transform.image_to_display(*marker.image_xy)
            if u < 0 or v < 0 or u >= transform.display_w or v >= transform.display_h:
                continue
            center = (int(round(u)), int(round(v)))
            color = (0, 255, 0) if marker.kind == "+" else (0, 0, 255)
            if marker.kind == "+":
                cv2.drawMarker(
                    display,
                    center,
                    color,
                    markerType=cv2.MARKER_CROSS,
                    markerSize=24,
                    thickness=2,
                )
            else:
                cv2.drawMarker(
                    display,
                    center,
                    color,
                    markerType=cv2.MARKER_TILTED_CROSS,
                    markerSize=24,
                    thickness=2,
                )

    def _draw_overlay_text(self, display: np.ndarray) -> None:
        mode_text = self._current_mode or "none"
        crop_text = "perspective" if self._crop_setting is not None else "rect"
        hover_z = float(self.get_parameter("hover_z_m").value)
        raw_descend_distance = float(self.get_parameter("descend_distance_m").value)
        descend_distance = normalize_descend_distance_m(raw_descend_distance)
        descend_z = hover_z - descend_distance
        text = (
            f"mode={mode_text} | crop={crop_text} x:crop r:clear | "
            f"a:+ d:x | z={hover_z:.3f}->{descend_z:.3f}m | q:quit"
        )
        cv2.rectangle(display, (0, 0), (display.shape[1], 32), (0, 0, 0), -1)
        cv2.putText(
            display,
            text,
            (10, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    def _draw_crop_selection_overlay(self, display: np.ndarray) -> None:
        for index, point in enumerate(self._crop_points, start=1):
            x, y = int(round(point[0])), int(round(point[1]))
            cv2.circle(display, (x, y), 5, (0, 255, 255), -1)
            cv2.putText(
                display,
                str(index),
                (x + 8, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
        text = (
            f"CROP SELECT: click 4 corners {len(self._crop_points)}/4 | "
            "r: cancel/clear | q: quit"
        )
        cv2.rectangle(display, (0, 0), (display.shape[1], 32), (0, 0, 0), -1)
        cv2.putText(
            display,
            text,
            (10, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    def _handle_key(self, key: int) -> None:
        if key in {255, -1}:
            return
        if key in {ord("q"), 27}:
            self.request_close()
            return
        if key == ord("x"):
            self._start_crop_selection()
            return
        if key == ord("r"):
            self._clear_crop_selection()
            return
        if key == ord("a"):
            self._current_mode = "attach"
            self.get_logger().info("[mode] attach: 다음 클릭에서 suction ON sequence 실행")
            return
        if key == ord("d"):
            self._current_mode = "detach"
            self.get_logger().info("[mode] detach: 다음 클릭에서 suction OFF sequence 실행")
            return

    def _start_crop_selection(self) -> None:
        self._selecting_crop = True
        self._crop_points = []
        self._markers = []
        self._current_mode = None
        self.get_logger().info("[crop] 원본 화면에서 꼭지점 4개를 순서 상관 없이 클릭하세요")

    def _clear_crop_selection(self) -> None:
        self._selecting_crop = False
        self._crop_points = []
        self._crop_setting = None
        self._markers = []
        self._latest_transform = None
        self.get_logger().info("[crop] 현재 실행 중인 크롭을 해제했습니다. 저장 파일은 유지됩니다")

    def _mouse_callback(self, event: int, x: int, y: int, flags: int, param: Any) -> None:
        del flags, param
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if self._selecting_crop:
            self._handle_crop_click(x, y)
            return
        transform = self._latest_transform
        if transform is None:
            self.get_logger().info("[click] ignored: 아직 image frame이 없습니다")
            return
        u = float(max(0, min(transform.display_w - 1, x)))
        v = float(max(0, min(transform.display_h - 1, y)))
        image_xy = transform.display_to_image(u, v)
        if self._current_mode is None:
            self.get_logger().info(
                "[click] mode=None display=(%.1f, %.1f) image=(%.1f, %.1f): 이동 없음"
                % (u, v, image_xy[0], image_xy[1])
            )
            return

        mode = self._current_mode
        self._current_mode = None
        marker = make_click_marker(mode, image_xy)
        self._markers.append(marker)
        self._redraw_once()
        cv2.waitKey(1)
        sequence_ok = False
        try:
            sequence_ok = self._run_click_sequence(
                mode=mode,
                display_xy=(u, v),
                transform=transform,
            )
        except Exception as exc:  # pragma: no cover - defensive UI boundary.
            self.get_logger().error(f"[blocker] unexpected click sequence error: {exc}")
        finally:
            if sequence_ok:
                self._markers = [stored for stored in self._markers if stored is not marker]
                self.get_logger().info("[marker] sequence completed; marker removed")
            else:
                self.get_logger().warn("[marker] sequence not completed; marker kept")
            self._redraw_once()
            cv2.waitKey(1)

    def _handle_crop_click(self, x: int, y: int) -> None:
        frame = self._current_frame()
        if frame is None:
            self.get_logger().info("[crop] ignored: 아직 image frame이 없습니다")
            return
        height, width = frame.shape[:2]
        clipped_x = float(max(0, min(width - 1, x)))
        clipped_y = float(max(0, min(height - 1, y)))
        self._crop_points.append([clipped_x, clipped_y])
        self.get_logger().info(
            "[crop] point %d/4 = (%.0f, %.0f)"
            % (len(self._crop_points), clipped_x, clipped_y)
        )
        if len(self._crop_points) == 4:
            self._finish_crop_selection(frame)

    def _finish_crop_selection(self, frame: np.ndarray) -> None:
        try:
            setting = build_crop_setting(points=self._crop_points, image_shape=frame.shape)
            save_crop_setting(self._crop_save_path, setting)
        except (OSError, ValueError) as exc:
            self.get_logger().error(f"[crop 저장 실패] {exc}")
            self._crop_points = []
            return
        self._crop_setting = setting
        self._selecting_crop = False
        self._crop_points = []
        self._latest_transform = None
        self.get_logger().info(
            "[crop saved] size=%dx%d path=%s"
            % (setting.output_width, setting.output_height, self._crop_save_path)
        )

    def _run_click_sequence(
        self,
        *,
        mode: str,
        display_xy: tuple[float, float],
        transform: DisplayTransformLike,
    ) -> bool:
        if self._calibration is None:
            self.get_logger().error("[blocker] calibration_path 보정값을 불러오지 못했습니다")
            return False
        try:
            plan = build_click_pick_place_plan(
                mode=mode,
                display_xy=display_xy,
                transform=transform,
                calibration=self._calibration,
                hover_z_m=float(self.get_parameter("hover_z_m").value),
                descend_distance_m=float(self.get_parameter("descend_distance_m").value),
                r_deg=float(self.get_parameter("r_deg").value),
                return_to_hover=parse_bool(self.get_parameter("return_to_hover").value),
                movej_motion_type=int(self.get_parameter("movej_motion_type").value),
                movel_motion_type=int(self.get_parameter("movel_motion_type").value),
            )
        except (ValueError, RuntimeError) as exc:
            self.get_logger().error(f"[blocker] click sequence build failed: {exc}")
            return False

        self.get_logger().info(click_log_line(plan))
        raw_descend_distance = float(self.get_parameter("descend_distance_m").value)
        effective_descend_distance = normalize_descend_distance_m(raw_descend_distance)
        self.get_logger().info(
            "[z] hover_z_m=%.4f descend_distance_m=%.4f "
            "effective_descend_m=%.4f descend_z_m=%.4f"
            % (
                float(self.get_parameter("hover_z_m").value),
                raw_descend_distance,
                effective_descend_distance,
                compute_descend_z_m(
                    float(self.get_parameter("hover_z_m").value),
                    raw_descend_distance,
                ),
            )
        )
        execution = execute_plan_steps(
            plan,
            dry_run=parse_bool(self.get_parameter("dry_run").value),
            motion_sender=self._send_motion_goal,
            suction_sender=self._send_suction_request,
        )
        for line in execution.logs:
            self.get_logger().info(line)
        if not execution.succeeded:
            self.get_logger().error(
                "[blocker] click sequence incomplete; failed_step=%s"
                % execution.failed_step_label
            )
        return execution.succeeded

    def _send_motion_goal(self, motion_type: int, target_pose: list[float]) -> bool:
        self.get_logger().info(
            "[target] motion_type=%d target_pose=%s" % (motion_type, target_pose)
        )
        if PointToPoint is None or self._action_client is None:
            self.get_logger().error(
                "[blocker] dobot_msgs.action.PointToPoint import 실패; "
                "magician_ros2_control_system_ws/src/install/setup.bash를 source하세요"
            )
            return False
        if not self._action_client.wait_for_server(
            timeout_sec=float(self.get_parameter("action_server_timeout_sec").value)
        ):
            requested = self._normalize_graph_name(
                str(self.get_parameter("ptp_action_name").value)
            )
            available = ", ".join(self._available_action_names()) or "(none)"
            self.get_logger().error(
                "[blocker] PointToPoint action server가 없습니다: "
                f"required={requested}, available_actions={available}"
            )
            self._log_robot_bringup_hint()
            return False
        goal = PointToPoint.Goal()
        goal.motion_type = int(motion_type)
        goal.target_pose = [float(value) for value in target_pose]
        goal.velocity_ratio = float(self.get_parameter("velocity_ratio").value)
        goal.acceleration_ratio = float(self.get_parameter("acceleration_ratio").value)
        future = self._action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(
            self,
            future,
            timeout_sec=float(self.get_parameter("motion_goal_timeout_sec").value),
        )
        goal_handle = future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error("[blocker] PointToPoint goal rejected/timeout")
            return False
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(
            self,
            result_future,
            timeout_sec=float(self.get_parameter("motion_result_timeout_sec").value),
        )
        result = result_future.result()
        if result is None:
            self.get_logger().error("[blocker] PointToPoint result timeout")
            return False
        self.get_logger().info(f"[motion done] achieved_pose={result.result.achieved_pose}")
        return True

    def _send_suction_request(self, enabled: bool) -> bool:
        self.get_logger().info(f"[target] suction enable_suction={enabled}")
        if SuctionCupControl is None or self._suction_client is None:
            self.get_logger().error(
                "[blocker] dobot_msgs.srv.SuctionCupControl import 실패; "
                "magician_ros2_control_system_ws/src/install/setup.bash를 source하세요"
            )
            return False
        if not self._suction_client.wait_for_service(
            timeout_sec=float(self.get_parameter("suction_service_timeout_sec").value)
        ):
            requested = self._normalize_graph_name(
                str(self.get_parameter("suction_service_name").value)
            )
            available = ", ".join(self._available_service_names()) or "(none)"
            self.get_logger().error(
                "[blocker] suction service가 없습니다: "
                f"required={requested}, available_services={available}"
            )
            self._log_robot_bringup_hint()
            return False
        request = SuctionCupControl.Request()
        request.enable_suction = bool(enabled)
        future = self._suction_client.call_async(request)
        rclpy.spin_until_future_complete(
            self,
            future,
            timeout_sec=float(self.get_parameter("suction_response_timeout_sec").value),
        )
        response = future.result()
        if response is None:
            self.get_logger().error("[blocker] suction service response timeout")
            return False
        self.get_logger().info(
            "[suction done] success=%s message=%s" % (response.success, response.message)
        )
        return bool(response.success)


def main(args: list[str] | None = None) -> None:
    """Run the click pick/place OpenCV UI node."""
    rclpy.init(args=args)
    node = ClickPickPlaceNode()
    shutdown_from_signal = False
    previous_handlers: dict[int, Any] = {}

    def _handle_process_signal(signum: int, frame: Any) -> None:
        del frame
        nonlocal shutdown_from_signal
        shutdown_from_signal = True
        node.get_logger().info(f"[shutdown] received signal {signum}; exiting UI loop")
        node.request_close()

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[int(signum)] = signal.getsignal(signum)
        signal.signal(signum, _handle_process_signal)

    try:
        while rclpy.ok() and not node.closed:
            rclpy.spin_once(node, timeout_sec=0.01)
            node.update_window()
    except (KeyboardInterrupt, ExternalShutdownException):
        node.request_close()
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        if not shutdown_from_signal:
            cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
