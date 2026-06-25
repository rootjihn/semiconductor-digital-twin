"""
Subscribe to YOLO detections and prepare/execute Dobot pick-place plans.

The adapter intentionally consumes camera-image-space detections only. Robot-space
conversion stays here so the YOLO node does not need to know Dobot calibration or
motion details.
"""

from __future__ import annotations

import json
import math
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String

from dobot_control.click_pick_place import (
    DisplayTransform,
    click_log_line,
    execute_plan_steps,
    parse_bool,
    build_click_pick_place_plan,
)
from dobot_control.red_plate_calibration import (
    PixelToBaseCalibration,
    load_calibration,
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
class DetectionResult:
    """One structured object detection from /detection_results."""

    label: str
    class_id: int
    confidence: float
    bbox: tuple[float, float, float, float]
    center: tuple[float, float]
    image_size: tuple[int, int] | None = None
    stamp: dict[str, int] | None = None
    frame_id: str | None = None

    def compact_dict(self) -> dict[str, Any]:
        """Return a JSON-safe compact representation for status messages."""
        payload = asdict(self)
        payload["bbox"] = list(self.bbox)
        payload["center"] = list(self.center)
        if self.image_size is not None:
            payload["image_size"] = list(self.image_size)
        return payload


def _finite_float(value: Any, field_name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def _number_sequence(value: Any, *, field_name: str, length: int) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"{field_name} must be a {length}-element array")
    return tuple(_finite_float(item, f"{field_name}[{index}]") for index, item in enumerate(value))


def _optional_image_size(value: Any) -> tuple[int, int] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("image_size must be [width, height]")
    width = int(value[0])
    height = int(value[1])
    if width <= 0 or height <= 0:
        raise ValueError("image_size values must be positive")
    return width, height


def _optional_stamp(value: Any) -> dict[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("stamp must be an object")
    stamp: dict[str, int] = {}
    for key in ("sec", "nanosec"):
        if key in value:
            stamp[key] = int(value[key])
    return stamp or None


def parse_detection_results(payload: str) -> list[DetectionResult]:
    """Parse the JSON-array contract published on /detection_results."""
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"detection_results is not valid JSON: {exc}") from exc
    if not isinstance(raw, list):
        raise ValueError("detection_results must be a JSON array")

    detections: list[DetectionResult] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"detection_results[{index}] must be an object")
        label = str(item.get("label", "")).strip()
        if not label:
            raise ValueError(f"detection_results[{index}].label is required")
        class_id = int(item.get("class_id", -1))
        confidence = _finite_float(
            item.get("confidence"),
            f"detection_results[{index}].confidence",
        )
        bbox = _number_sequence(
            item.get("bbox"),
            field_name=f"detection_results[{index}].bbox",
            length=4,
        )
        center = _number_sequence(
            item.get("center"),
            field_name=f"detection_results[{index}].center",
            length=2,
        )
        detections.append(
            DetectionResult(
                label=label,
                class_id=class_id,
                confidence=confidence,
                bbox=(bbox[0], bbox[1], bbox[2], bbox[3]),
                center=(center[0], center[1]),
                image_size=_optional_image_size(item.get("image_size")),
                stamp=_optional_stamp(item.get("stamp")),
                frame_id=str(item["frame_id"]) if item.get("frame_id") is not None else None,
            )
        )
    detections.sort(key=lambda item: item.confidence, reverse=True)
    return detections


def select_detection(
    detections: Iterable[DetectionResult],
    *,
    target_label: str = "",
    min_confidence: float = 0.0,
) -> DetectionResult | None:
    """Choose the highest-confidence detection that matches adapter policy."""
    label_filter = str(target_label).strip()
    threshold = float(min_confidence)
    candidates = [
        detection
        for detection in detections
        if detection.confidence >= threshold
        and (not label_filter or detection.label == label_filter)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.confidence)


def build_detection_pick_place_plan(
    *,
    mode: str,
    detection: DetectionResult,
    calibration: PixelToBaseCalibration,
    hover_z_m: float,
    descend_distance_m: float,
    r_deg: float,
    return_to_hover: bool,
    movej_motion_type: int,
    movel_motion_type: int,
):
    """Convert one image-space detection center into the existing Dobot plan shape."""
    width, height = detection.image_size or (1, 1)
    transform = DisplayTransform(
        crop_x=0,
        crop_y=0,
        crop_w=max(1, int(width)),
        crop_h=max(1, int(height)),
        display_w=max(1, int(width)),
        display_h=max(1, int(height)),
    )
    return build_click_pick_place_plan(
        mode=mode,
        display_xy=detection.center,
        transform=transform,
        calibration=calibration,
        hover_z_m=hover_z_m,
        descend_distance_m=descend_distance_m,
        r_deg=r_deg,
        return_to_hover=return_to_hover,
        movej_motion_type=movej_motion_type,
        movel_motion_type=movel_motion_type,
    )


def plan_to_status_steps(plan) -> list[dict[str, Any]]:
    """Serialize motion/suction steps for operator-visible status."""
    steps: list[dict[str, Any]] = []
    for step in plan.steps:
        item: dict[str, Any] = {"kind": step.kind, "label": step.label}
        if step.motion_type is not None:
            item["motion_type"] = int(step.motion_type)
        if step.target_pose is not None:
            item["target_pose"] = [float(value) for value in step.target_pose]
        if step.suction_enabled is not None:
            item["suction_enabled"] = bool(step.suction_enabled)
        steps.append(item)
    return steps


class DobotAdapterNode(Node):
    """Bridge structured YOLO detections to Dobot pick/place plans."""

    def __init__(self) -> None:
        super().__init__("dobot_adapter")
        self.declare_parameter("detection_topic", "/detection_results")
        self.declare_parameter("status_topic", "/dobot_control/dobot_adapter/status")
        self.declare_parameter("calibration_path", "~/red_plate_pixel_to_base_calibration.json")
        self.declare_parameter("target_label", "")
        self.declare_parameter("min_confidence", 0.25)
        self.declare_parameter("mode", "attach")
        self.declare_parameter("auto_execute", False)
        self.declare_parameter("dry_run", True)
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

        self._busy_lock = threading.Lock()
        self._calibration = self._load_calibration()
        self._status_pub = self.create_publisher(
            String,
            str(self.get_parameter("status_topic").value),
            10,
        )
        self.create_subscription(
            String,
            str(self.get_parameter("detection_topic").value),
            self._detection_callback,
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

        self.get_logger().info(
            "dobot adapter ready: detection_topic=%s status_topic=%s auto_execute=%s dry_run=%s"
            % (
                self.get_parameter("detection_topic").value,
                self.get_parameter("status_topic").value,
                self.get_parameter("auto_execute").value,
                self.get_parameter("dry_run").value,
            )
        )

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

    def _publish_status(self, payload: dict[str, Any]) -> None:
        msg = String()
        msg.data = json.dumps(payload, ensure_ascii=False)
        self._status_pub.publish(msg)

    def _detection_callback(self, msg: String) -> None:
        if not self._busy_lock.acquire(blocking=False):
            self._publish_status({
                "event": "busy_skip",
                "message": "previous command still running",
            })
            return
        try:
            self._handle_detection_message(msg.data)
        finally:
            self._busy_lock.release()

    def _handle_detection_message(self, payload: str) -> None:
        if self._calibration is None:
            self._publish_status({"event": "blocker", "message": "calibration not loaded"})
            self.get_logger().error("[blocker] calibration_path 보정값을 불러오지 못했습니다")
            return
        try:
            detections = parse_detection_results(payload)
        except ValueError as exc:
            self._publish_status({"event": "blocker", "message": str(exc)})
            self.get_logger().error(f"[blocker] invalid detection_results: {exc}")
            return

        detection = select_detection(
            detections,
            target_label=str(self.get_parameter("target_label").value),
            min_confidence=float(self.get_parameter("min_confidence").value),
        )
        if detection is None:
            self._publish_status(
                {
                    "event": "no_detection",
                    "count": len(detections),
                    "target_label": str(self.get_parameter("target_label").value),
                    "min_confidence": float(self.get_parameter("min_confidence").value),
                }
            )
            return

        try:
            plan = build_detection_pick_place_plan(
                mode=str(self.get_parameter("mode").value),
                detection=detection,
                calibration=self._calibration,
                hover_z_m=float(self.get_parameter("hover_z_m").value),
                descend_distance_m=float(self.get_parameter("descend_distance_m").value),
                r_deg=float(self.get_parameter("r_deg").value),
                return_to_hover=parse_bool(self.get_parameter("return_to_hover").value),
                movej_motion_type=int(self.get_parameter("movej_motion_type").value),
                movel_motion_type=int(self.get_parameter("movel_motion_type").value),
            )
        except (ValueError, RuntimeError) as exc:
            self._publish_status({"event": "blocker", "message": f"plan build failed: {exc}"})
            self.get_logger().error(f"[blocker] plan build failed: {exc}")
            return

        auto_execute = parse_bool(self.get_parameter("auto_execute").value)
        dry_run = parse_bool(self.get_parameter("dry_run").value)
        status = {
            "event": "adapter_plan",
            "selected_detection": detection.compact_dict(),
            "mode": plan.mode,
            "image_xy": list(plan.image_xy),
            "base_xy": list(plan.base_xy),
            "steps": plan_to_status_steps(plan),
            "auto_execute": auto_execute,
            "dry_run": dry_run,
        }
        self._publish_status(status)
        self.get_logger().info(click_log_line(plan))

        if not auto_execute:
            self.get_logger().info("[adapter] auto_execute=false; plan only")
            return

        execution = execute_plan_steps(
            plan,
            dry_run=dry_run,
            motion_sender=self._send_motion_goal,
            suction_sender=self._send_suction_request,
        )
        for line in execution.logs:
            self.get_logger().info(line)
        self._publish_status(
            {
                "event": "execution_result",
                "succeeded": execution.succeeded,
                "failed_step_label": execution.failed_step_label,
                "logs": execution.logs,
            }
        )

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
    rclpy.init(args=args)
    node = DobotAdapterNode()
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
