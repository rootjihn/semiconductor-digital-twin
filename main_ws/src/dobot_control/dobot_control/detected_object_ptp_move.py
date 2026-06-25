"""Move a detected object with a parameterized Dobot PTP sequence."""

from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rclpy
from action_msgs.msg import GoalStatus
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String

from dobot_control.click_pick_place import parse_bool
from dobot_control.dobot_adapter_node import (
    DetectionResult,
    parse_detection_results,
    select_detection,
)
from dobot_control.red_plate_calibration import (
    PixelToBaseCalibration,
    apply_pixel_to_base_xy,
    load_calibration,
    pose_xy_to_action_target,
)

try:
    from dobot_msgs.action import PointToPoint
except ImportError:  # pragma: no cover - external Dobot overlay is optional in unit tests.
    PointToPoint = None

try:
    from dobot_msgs.srv import SuctionCupControl
except ImportError:  # pragma: no cover - external Dobot overlay is optional in unit tests.
    SuctionCupControl = None


DEFAULT_MOVEJ_MOTION_TYPE = 1


@dataclass(frozen=True)
class DetectedObjectPtpStep:
    """One Dobot move or suction command in the detected-object sequence."""

    kind: str
    label: str
    motion_type: int | None = None
    target_pose: list[float] | None = None
    suction_enabled: bool | None = None


@dataclass(frozen=True)
class DetectedObjectPtpPlan:
    """Resolved plan from image-space detection to base-frame PTP targets."""

    detection: DetectionResult
    image_xy: tuple[float, float]
    base_xy: tuple[float, float]
    pick_z_m: float
    place_xyz_m: tuple[float, float, float]
    steps: list[DetectedObjectPtpStep]


def _finite_float(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def build_detected_object_ptp_plan(
    *,
    detection: DetectionResult,
    calibration: PixelToBaseCalibration,
    pick_hover_z_m: float,
    pick_descend_distance_m: float,
    min_pick_z_m: float,
    place_x_m: float,
    place_y_m: float,
    place_z_m: float,
    place_hover_offset_m: float,
    yaw_deg: float,
    movej_motion_type: int = DEFAULT_MOVEJ_MOTION_TYPE,
    return_to_place_hover: bool = True,
) -> DetectedObjectPtpPlan:
    """Build MoveJ pick-at-detection then fixed-place suction-OFF steps."""
    pick_hover_z = _finite_float(pick_hover_z_m, "pick_hover_z_m")
    descend_distance = abs(_finite_float(pick_descend_distance_m, "pick_descend_distance_m"))
    min_pick_z = _finite_float(min_pick_z_m, "min_pick_z_m")
    place_x = _finite_float(place_x_m, "place_x_m")
    place_y = _finite_float(place_y_m, "place_y_m")
    place_z = _finite_float(place_z_m, "place_z_m")
    place_hover_offset = _finite_float(place_hover_offset_m, "place_hover_offset_m")
    yaw = _finite_float(yaw_deg, "yaw_deg")
    motion_type = int(movej_motion_type)

    if place_hover_offset < 0.0:
        raise ValueError("place_hover_offset_m must be non-negative")
    if pick_hover_z < min_pick_z:
        raise ValueError("pick_hover_z_m must be greater than or equal to min_pick_z_m")

    image_xy = (float(detection.center[0]), float(detection.center[1]))
    pick_x, pick_y = apply_pixel_to_base_xy(calibration, image_xy)
    pick_z = max(min_pick_z, pick_hover_z - descend_distance)
    place_hover_z = place_z + place_hover_offset

    # 사용자 요청대로 모든 위치 이동은 MoveJ 계열 motion_type을 사용한다.
    pick_hover_pose = pose_xy_to_action_target(
        x_m=pick_x,
        y_m=pick_y,
        z_m=pick_hover_z,
        yaw_deg=yaw,
    )
    pick_descend_pose = pose_xy_to_action_target(
        x_m=pick_x,
        y_m=pick_y,
        z_m=pick_z,
        yaw_deg=yaw,
    )
    place_hover_pose = pose_xy_to_action_target(
        x_m=place_x,
        y_m=place_y,
        z_m=place_hover_z,
        yaw_deg=yaw,
    )
    place_pose = pose_xy_to_action_target(
        x_m=place_x,
        y_m=place_y,
        z_m=place_z,
        yaw_deg=yaw,
    )

    steps = [
        DetectedObjectPtpStep(
            kind="move",
            label="MoveJ detected pick hover",
            motion_type=motion_type,
            target_pose=pick_hover_pose,
        ),
        DetectedObjectPtpStep(
            kind="move",
            label="MoveJ detected pick descend",
            motion_type=motion_type,
            target_pose=pick_descend_pose,
        ),
        DetectedObjectPtpStep(kind="suction", label="suction ON", suction_enabled=True),
        DetectedObjectPtpStep(
            kind="move",
            label="MoveJ detected pick hover return",
            motion_type=motion_type,
            target_pose=pick_hover_pose,
        ),
        DetectedObjectPtpStep(
            kind="move",
            label="MoveJ place hover",
            motion_type=motion_type,
            target_pose=place_hover_pose,
        ),
        DetectedObjectPtpStep(
            kind="move",
            label="MoveJ place descend",
            motion_type=motion_type,
            target_pose=place_pose,
        ),
        DetectedObjectPtpStep(kind="suction", label="suction OFF", suction_enabled=False),
    ]
    if return_to_place_hover:
        steps.append(
            DetectedObjectPtpStep(
                kind="move",
                label="MoveJ place hover return",
                motion_type=motion_type,
                target_pose=place_hover_pose,
            )
        )

    return DetectedObjectPtpPlan(
        detection=detection,
        image_xy=image_xy,
        base_xy=(float(pick_x), float(pick_y)),
        pick_z_m=float(pick_z),
        place_xyz_m=(float(place_x), float(place_y), float(place_z)),
        steps=steps,
    )


def plan_to_status(plan: DetectedObjectPtpPlan) -> dict[str, Any]:
    """Serialize a plan for status topic/log inspection."""
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
    return {
        "selected_detection": plan.detection.compact_dict(),
        "image_xy": list(plan.image_xy),
        "base_xy": list(plan.base_xy),
        "pick_z_m": plan.pick_z_m,
        "place_xyz_m": list(plan.place_xyz_m),
        "steps": steps,
    }


class DetectedObjectPtpMoveNode(Node):
    """Subscribe to YOLO detections and execute one configured pick-place sequence."""

    def __init__(self) -> None:
        super().__init__("detected_object_ptp_move")
        self.declare_parameter("detection_topic", "/detection_results")
        self.declare_parameter("status_topic", "/dobot_control/detected_object_ptp_move/status")
        self.declare_parameter("calibration_path", "~/red_plate_pixel_to_base_calibration.json")
        self.declare_parameter("target_label", "")
        self.declare_parameter("min_confidence", 0.25)
        self.declare_parameter("pick_hover_z_m", 0.06)
        self.declare_parameter("pick_descend_distance_m", 0.04)
        self.declare_parameter("min_pick_z_m", 0.02)
        self.declare_parameter("place_x_m", 0.16)
        self.declare_parameter("place_y_m", 0.01)
        self.declare_parameter("place_z_m", 0.04)
        self.declare_parameter("place_hover_offset_m", 0.06)
        self.declare_parameter("yaw_deg", 0.0)
        self.declare_parameter("movej_motion_type", DEFAULT_MOVEJ_MOTION_TYPE)
        self.declare_parameter("return_to_place_hover", True)
        self.declare_parameter("run_once", True)
        self.declare_parameter("auto_execute", False)
        self.declare_parameter("dry_run", True)
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
        self._completed = False
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
            "detected_object_ptp_move ready: "
            "detection_topic=%s auto_execute=%s dry_run=%s run_once=%s"
            % (
                self.get_parameter("detection_topic").value,
                self.get_parameter("auto_execute").value,
                self.get_parameter("dry_run").value,
                self.get_parameter("run_once").value,
            )
        )

    def _load_calibration(self) -> PixelToBaseCalibration | None:
        path = Path(str(self.get_parameter("calibration_path").value)).expanduser()
        try:
            calibration = load_calibration(path)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.get_logger().error(f"[blocker] calibration load failed: {path}: {exc}")
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
        if parse_bool(self.get_parameter("run_once").value) and self._completed:
            return
        if not self._busy_lock.acquire(blocking=False):
            self._publish_status({"event": "busy_skip"})
            return
        try:
            self._handle_detection_message(msg.data)
        finally:
            self._busy_lock.release()

    def _handle_detection_message(self, payload: str) -> None:
        if self._calibration is None:
            self._publish_status({"event": "blocker", "message": "calibration not loaded"})
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
            self._publish_status({"event": "no_detection", "count": len(detections)})
            return

        try:
            plan = build_detected_object_ptp_plan(
                detection=detection,
                calibration=self._calibration,
                pick_hover_z_m=float(self.get_parameter("pick_hover_z_m").value),
                pick_descend_distance_m=float(self.get_parameter("pick_descend_distance_m").value),
                min_pick_z_m=float(self.get_parameter("min_pick_z_m").value),
                place_x_m=float(self.get_parameter("place_x_m").value),
                place_y_m=float(self.get_parameter("place_y_m").value),
                place_z_m=float(self.get_parameter("place_z_m").value),
                place_hover_offset_m=float(self.get_parameter("place_hover_offset_m").value),
                yaw_deg=float(self.get_parameter("yaw_deg").value),
                movej_motion_type=int(self.get_parameter("movej_motion_type").value),
                return_to_place_hover=parse_bool(
                    self.get_parameter("return_to_place_hover").value
                ),
            )
        except (ValueError, RuntimeError) as exc:
            self._publish_status({"event": "blocker", "message": f"plan build failed: {exc}"})
            self.get_logger().error(f"[blocker] plan build failed: {exc}")
            return

        auto_execute = parse_bool(self.get_parameter("auto_execute").value)
        dry_run = parse_bool(self.get_parameter("dry_run").value)
        status = {"event": "detected_object_ptp_plan", **plan_to_status(plan)}
        status["auto_execute"] = auto_execute
        status["dry_run"] = dry_run
        self._publish_status(status)
        self.get_logger().info(
            "[detected-object] image=(%.1f, %.1f) base=(%.4f, %.4f) place=(%.4f, %.4f, %.4f)"
            % (
                plan.image_xy[0],
                plan.image_xy[1],
                plan.base_xy[0],
                plan.base_xy[1],
                plan.place_xyz_m[0],
                plan.place_xyz_m[1],
                plan.place_xyz_m[2],
            )
        )

        if not auto_execute:
            self.get_logger().info("[detected-object] auto_execute=false; plan only")
            self._completed = True
            return

        succeeded, failed_step, logs = self._execute_plan(plan, dry_run=dry_run)
        for line in logs:
            self.get_logger().info(line)
        self._publish_status(
            {
                "event": "execution_result",
                "succeeded": succeeded,
                "failed_step_label": failed_step,
                "logs": logs,
            }
        )
        if succeeded:
            self._completed = True

    def _execute_plan(
        self,
        plan: DetectedObjectPtpPlan,
        *,
        dry_run: bool,
    ) -> tuple[bool, str | None, list[str]]:
        logs: list[str] = []
        for step in plan.steps:
            if step.kind == "move":
                if step.motion_type is None or step.target_pose is None:
                    raise ValueError("move step requires motion_type and target_pose")
                if dry_run:
                    logs.append(f"[dry-run] {step.label}: {step.target_pose}")
                else:
                    logs.append(f"[motion] {step.label}: {step.target_pose}")
                    if not self._send_motion_goal(step.motion_type, step.target_pose):
                        return False, step.label, logs
                continue
            if step.kind == "suction":
                if step.suction_enabled is None:
                    raise ValueError("suction step requires suction_enabled")
                if dry_run:
                    logs.append(f"[dry-run] {step.label}")
                else:
                    logs.append(f"[suction] {step.label}")
                    if not self._send_suction_request(step.suction_enabled):
                        return False, step.label, logs
                continue
            raise ValueError(f"unsupported step kind: {step.kind!r}")
        return True, None, logs

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

    @staticmethod
    def _goal_status_name(status: int) -> str:
        names = {
            GoalStatus.STATUS_UNKNOWN: "UNKNOWN",
            GoalStatus.STATUS_ACCEPTED: "ACCEPTED",
            GoalStatus.STATUS_EXECUTING: "EXECUTING",
            GoalStatus.STATUS_CANCELING: "CANCELING",
            GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED",
            GoalStatus.STATUS_CANCELED: "CANCELED",
            GoalStatus.STATUS_ABORTED: "ABORTED",
        }
        return names.get(int(status), f"STATUS_{status}")

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
        if goal_handle is None:
            self.get_logger().error("[blocker] PointToPoint goal acceptance timeout")
            return False
        if not goal_handle.accepted:
            self.get_logger().error("[blocker] PointToPoint goal rejected")
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
        status_name = self._goal_status_name(result.status)
        achieved_pose = result.result.achieved_pose
        if result.status != GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().error(
                "[blocker] PointToPoint finished with "
                f"status={status_name} achieved_pose={achieved_pose}"
            )
            return False
        self.get_logger().info(f"[motion done] status={status_name} achieved_pose={achieved_pose}")
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
            "[suction done] success=%s message=%s"
            % (response.success, response.message)
        )
        return bool(response.success)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = DetectedObjectPtpMoveNode()
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
