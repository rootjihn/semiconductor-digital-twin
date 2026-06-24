"""OpenCV image topic viewer with persistent four-point crop selection."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


@dataclass(frozen=True)
class CropSetting:
    """Persistent perspective crop setting in source image pixel coordinates."""

    points: list[list[float]]
    output_width: int
    output_height: int
    image_width: int | None = None
    image_height: int | None = None


def order_crop_points(points: Any) -> np.ndarray:
    """Return four crop points ordered TL, TR, BR, BL regardless of click order."""
    pts = np.asarray(points, dtype=np.float32)
    if pts.shape != (4, 2):
        raise ValueError(f"crop points must be shaped (4, 2), got {pts.shape}")
    if np.unique(pts, axis=0).shape[0] != 4:
        raise ValueError("crop points must contain four distinct points")

    center = np.mean(pts, axis=0)
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    ordered = pts[np.argsort(angles)]
    top_left_index = int(np.argmin(np.sum(ordered, axis=1)))
    ordered = np.roll(ordered, -top_left_index, axis=0)
    return ordered.astype(np.float32)


def crop_output_size(ordered_points: Any) -> tuple[int, int]:
    """Compute perspective output width/height from ordered crop points."""
    pts = np.asarray(ordered_points, dtype=np.float32)
    if pts.shape != (4, 2):
        raise ValueError(f"ordered_points must be shaped (4, 2), got {pts.shape}")
    top_left, top_right, bottom_right, bottom_left = pts
    width_top = np.linalg.norm(top_right - top_left)
    width_bottom = np.linalg.norm(bottom_right - bottom_left)
    height_right = np.linalg.norm(bottom_right - top_right)
    height_left = np.linalg.norm(bottom_left - top_left)
    width = max(1, int(round(max(width_top, width_bottom))))
    height = max(1, int(round(max(height_right, height_left))))
    return width, height


def build_crop_setting(points: Any, image_shape: tuple[int, ...]) -> CropSetting:
    """Build a serializable crop setting from clicked points and source image shape."""
    ordered = order_crop_points(points)
    width, height = crop_output_size(ordered)
    image_height = int(image_shape[0]) if len(image_shape) >= 1 else None
    image_width = int(image_shape[1]) if len(image_shape) >= 2 else None
    return CropSetting(
        points=ordered.astype(float).tolist(),
        output_width=width,
        output_height=height,
        image_width=image_width,
        image_height=image_height,
    )


def apply_crop_setting(image: np.ndarray, setting: CropSetting) -> np.ndarray:
    """Perspective-warp the saved crop region from an image."""
    if setting.output_width <= 0 or setting.output_height <= 0:
        raise ValueError("crop output size must be positive")
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
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image, matrix, (setting.output_width, setting.output_height))


def save_crop_setting(path: str | Path, setting: CropSetting) -> None:
    """Save crop setting JSON, creating parent directories."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(setting), ensure_ascii=False, indent=2), encoding="utf-8")


def load_crop_setting(path: str | Path) -> CropSetting:
    """Load crop setting JSON from disk."""
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    return CropSetting(
        points=[[float(x), float(y)] for x, y in payload["points"]],
        output_width=int(payload["output_width"]),
        output_height=int(payload["output_height"]),
        image_width=(
            None if payload.get("image_width") is None else int(payload.get("image_width"))
        ),
        image_height=(
            None if payload.get("image_height") is None else int(payload.get("image_height"))
        ),
    )


def image_msg_to_bgr(msg: Image) -> np.ndarray:
    """Convert common ROS Image encodings into an OpenCV BGR image."""
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
    if encoding in {"bgra8", "rgba8"}:
        image = packed[:, : msg.width * 4].reshape(msg.height, msg.width, 4)
        code = cv2.COLOR_BGRA2BGR if encoding == "bgra8" else cv2.COLOR_RGBA2BGR
        return cv2.cvtColor(image, code)
    if encoding in {"mono8", "8uc1"}:
        return cv2.cvtColor(packed[:, : msg.width], cv2.COLOR_GRAY2BGR)
    raise ValueError(f"unsupported image encoding: {msg.encoding}")


class ImageCropViewer(Node):
    """ROS2 image-topic viewer that can save and reload a perspective crop."""

    def __init__(self) -> None:
        super().__init__("image_crop_viewer")
        self.declare_parameter("image_topic", "/camera/camera/color/image_raw")
        self.declare_parameter("crop_save_path", "~/image_crop_viewer_crop.json")
        self.declare_parameter("window_name", "image_crop_viewer")
        self.declare_parameter("auto_load_crop", True)

        self._latest_frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()
        self._selecting = False
        self._clicked_points: list[list[float]] = []
        self._closed = False
        self._last_error = ""
        self._window_name = str(self.get_parameter("window_name").value)
        self._crop_save_path = Path(str(self.get_parameter("crop_save_path").value)).expanduser()
        self._crop_setting: CropSetting | None = self._load_initial_crop_setting()

        self.create_subscription(
            Image,
            str(self.get_parameter("image_topic").value),
            self._image_callback,
            qos_profile_sensor_data,
        )
        cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self._window_name, self._mouse_callback)
        self._print_startup_message()

    @property
    def closed(self) -> bool:
        """Return True when the user requested window shutdown."""
        return self._closed

    def _load_initial_crop_setting(self) -> CropSetting | None:
        if not bool(self.get_parameter("auto_load_crop").value):
            return None
        path = Path(str(self.get_parameter("crop_save_path").value)).expanduser()
        if not path.exists():
            return None
        try:
            setting = load_crop_setting(path)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.get_logger().warn(f"crop setting load failed: {exc}")
            return None
        self.get_logger().info(f"loaded crop setting: {path}")
        return setting

    def _print_startup_message(self) -> None:
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
        print("▶ image crop viewer", flush=True)
        print(f"  image: {self.get_parameter('image_topic').value}", flush=True)
        print(f"  save : {self._crop_save_path}", flush=True)
        print("  키: x=크롭 선택, r=크롭 해제, q/ESC=종료", flush=True)
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)

    def _image_callback(self, msg: Image) -> None:
        try:
            frame = image_msg_to_bgr(msg)
        except ValueError as exc:
            text = str(exc)
            if text != self._last_error:
                self.get_logger().warn(text)
                self._last_error = text
            return
        with self._frame_lock:
            self._latest_frame = frame

    def _mouse_callback(self, event: int, x: int, y: int, flags: int, param: Any) -> None:
        del flags, param
        if event != cv2.EVENT_LBUTTONDOWN or not self._selecting:
            return
        frame = self._current_frame()
        if frame is None:
            return
        height, width = frame.shape[:2]
        clipped_x = float(max(0, min(width - 1, x)))
        clipped_y = float(max(0, min(height - 1, y)))
        self._clicked_points.append([clipped_x, clipped_y])
        print(f"[crop] point {len(self._clicked_points)}/4 = ({clipped_x:.0f}, {clipped_y:.0f})")
        if len(self._clicked_points) == 4:
            self._finish_crop_selection(frame)

    def _current_frame(self) -> np.ndarray | None:
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def _finish_crop_selection(self, frame: np.ndarray) -> None:
        try:
            setting = build_crop_setting(points=self._clicked_points, image_shape=frame.shape)
            save_crop_setting(self._crop_save_path, setting)
        except (OSError, ValueError) as exc:
            print(f"[crop 저장 실패] {exc}", flush=True)
            self._clicked_points = []
            return
        self._crop_setting = setting
        self._selecting = False
        self._clicked_points = []
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
        print("▶ crop saved", flush=True)
        print(f"  size: {setting.output_width}x{setting.output_height}", flush=True)
        print(f"  path: {self._crop_save_path}", flush=True)
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)

    def update_window(self) -> None:
        """Draw the latest image and process OpenCV keyboard events once."""
        frame = self._current_frame()
        if frame is not None:
            display = self._display_frame(frame)
            cv2.imshow(self._window_name, display)
        key = cv2.waitKey(1) & 0xFF
        self._handle_key(key)

    def _display_frame(self, frame: np.ndarray) -> np.ndarray:
        if self._selecting:
            display = frame.copy()
            self._draw_selection_overlay(display)
            return display
        if self._crop_setting is None:
            display = frame.copy()
            self._draw_text(display, "x: crop select | r: clear | q: quit")
            return display
        try:
            display = apply_crop_setting(frame, self._crop_setting)
        except (ValueError, cv2.error) as exc:
            text = f"crop apply failed: {exc}"
            if text != self._last_error:
                self.get_logger().warn(text)
                self._last_error = text
            display = frame.copy()
        self._draw_text(display, "CROPPED | x: reselect | r: clear | q: quit")
        return display

    def _draw_selection_overlay(self, display: np.ndarray) -> None:
        for index, point in enumerate(self._clicked_points, start=1):
            x, y = int(point[0]), int(point[1])
            cv2.circle(display, (x, y), 5, (0, 255, 255), -1)
            cv2.putText(
                display,
                str(index),
                (x + 8, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )
        self._draw_text(
            display,
            f"Click 4 crop corners: {len(self._clicked_points)}/4 | r: cancel",
        )

    def _draw_text(self, image: np.ndarray, text: str) -> None:
        cv2.rectangle(image, (0, 0), (image.shape[1], 32), (0, 0, 0), -1)
        cv2.putText(
            image,
            text,
            (10, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    def _handle_key(self, key: int) -> None:
        if key in {255, -1}:
            return
        if key in {ord("q"), 27}:
            self._closed = True
            return
        if key == ord("x"):
            self._selecting = True
            self._clicked_points = []
            print("[crop] 원본 화면에서 꼭지점 4개를 순서 상관 없이 클릭하세요.", flush=True)
            return
        if key == ord("r"):
            self._selecting = False
            self._clicked_points = []
            self._crop_setting = None
            print("[crop] 현재 실행 중인 크롭을 해제했습니다. 저장 파일은 유지됩니다.", flush=True)


def main(args: list[str] | None = None) -> None:
    """Run the image crop viewer node."""
    rclpy.init(args=args)
    node = ImageCropViewer()
    try:
        while rclpy.ok() and not node.closed:
            rclpy.spin_once(node, timeout_sec=0.01)
            node.update_window()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
