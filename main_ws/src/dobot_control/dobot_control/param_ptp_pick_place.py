"""Run a parameter-driven Dobot pick/place PointToPoint sequence."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import rclpy
from action_msgs.msg import GoalStatus
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.action import ActionClient, get_action_names_and_types
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from dobot_control.red_plate_calibration import pose_xy_to_action_target

try:
    from dobot_msgs.action import PointToPoint
except ImportError:  # pragma: no cover - depends on external Dobot overlay.
    PointToPoint = None

try:
    from dobot_msgs.srv import EvaluatePTPTrajectory, SuctionCupControl
except ImportError:  # pragma: no cover - depends on external Dobot overlay.
    EvaluatePTPTrajectory = None
    SuctionCupControl = None


# Existing package coordinates are meters; +0.06 m gives a 6 cm clearance.
# The user-facing prompt said "0.6" but 0.6 m is not a safe default for Dobot.
DEFAULT_HOVER_OFFSET_M = 0.06
MOTION_TYPE_MOVJ_XYZ = 1
MOTION_TYPE_MOVL_XYZ = 2
MOTION_TYPE_MOVJ_ANGLE = 4
FOLDED_HOME_JOINT_POSE = [0.0, 0.0, 0.0, 0.0]


@dataclass(frozen=True)
class PtpPointM:
    """One XYZ point in base-frame meters."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class ParamPtpStep:
    """One deterministic motion or suction step."""

    kind: str
    label: str
    motion_type: int | None = None
    target_pose: list[float] | None = None
    suction_enabled: bool | None = None


def _optional_float(value: Any, name: str) -> float | None:
    """Parse a launch parameter where empty/nan means omitted."""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if text == "" or text.lower() in {"none", "null", "nan"}:
            return None
        value = text
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric or omitted") from exc
    if not math.isfinite(result):
        return None
    return result


def _triplet_from_values(
    values: dict[str, Any],
    prefix: str,
) -> tuple[PtpPointM | None, list[str]]:
    """Return a point only when all x/y/z fields for the prefix are present."""
    names = [f"{prefix}x", f"{prefix}y", f"{prefix}z"]
    parsed = {name: _optional_float(values.get(name), name) for name in names}
    missing = [name for name, value in parsed.items() if value is None]
    if len(missing) == 3:
        return None, missing
    if missing:
        return None, missing
    return PtpPointM(parsed[names[0]], parsed[names[1]], parsed[names[2]]), []


def _xyz_pose(point: PtpPointM, *, z_m: float, yaw_deg: float) -> list[float]:
    return pose_xy_to_action_target(x_m=point.x, y_m=point.y, z_m=z_m, yaw_deg=yaw_deg)


def build_param_ptp_steps(
    *,
    attach: PtpPointM | None,
    detach: PtpPointM | None,
    hover_offset_m: float = DEFAULT_HOVER_OFFSET_M,
    yaw_deg: float = 0.0,
    return_home: bool = True,
) -> list[ParamPtpStep]:
    """Build a partial or full parameter-driven pick/place sequence."""
    hover_offset = float(hover_offset_m)
    yaw = float(yaw_deg)
    if not math.isfinite(hover_offset) or hover_offset < 0.0:
        raise ValueError("hover_offset_m must be a finite non-negative value")
    if not math.isfinite(yaw):
        raise ValueError("yaw_deg must be finite")

    steps: list[ParamPtpStep] = []
    if attach is not None:
        attach_hover_z = attach.z + hover_offset
        steps.extend(
            [
                ParamPtpStep(
                    kind="move",
                    label="MoveJ attach hover",
                    motion_type=MOTION_TYPE_MOVJ_XYZ,
                    target_pose=_xyz_pose(attach, z_m=attach_hover_z, yaw_deg=yaw),
                ),
                ParamPtpStep(
                    kind="move",
                    label="MoveL attach descend",
                    motion_type=MOTION_TYPE_MOVL_XYZ,
                    target_pose=_xyz_pose(attach, z_m=attach.z, yaw_deg=yaw),
                ),
                ParamPtpStep(kind="suction", label="suction ON", suction_enabled=True),
            ]
        )
        # Always leave the contact Z before either moving to D or returning home.
        steps.append(
            ParamPtpStep(
                kind="move",
                label="MoveL attach hover",
                motion_type=MOTION_TYPE_MOVL_XYZ,
                target_pose=_xyz_pose(attach, z_m=attach_hover_z, yaw_deg=yaw),
            )
        )

    if detach is not None:
        detach_hover_z = detach.z + hover_offset
        steps.extend(
            [
                ParamPtpStep(
                    kind="move",
                    label="MoveJ detach hover",
                    motion_type=MOTION_TYPE_MOVJ_XYZ,
                    target_pose=_xyz_pose(detach, z_m=detach_hover_z, yaw_deg=yaw),
                ),
                ParamPtpStep(
                    kind="move",
                    label="MoveL detach descend",
                    motion_type=MOTION_TYPE_MOVL_XYZ,
                    target_pose=_xyz_pose(detach, z_m=detach.z, yaw_deg=yaw),
                ),
                ParamPtpStep(kind="suction", label="suction OFF", suction_enabled=False),
                ParamPtpStep(
                    kind="move",
                    label="MoveL detach hover",
                    motion_type=MOTION_TYPE_MOVL_XYZ,
                    target_pose=_xyz_pose(detach, z_m=detach_hover_z, yaw_deg=yaw),
                ),
            ]
        )

    if steps and return_home:
        steps.append(
            ParamPtpStep(
                kind="move",
                label="MoveJ folded home",
                motion_type=MOTION_TYPE_MOVJ_ANGLE,
                target_pose=list(FOLDED_HOME_JOINT_POSE),
            )
        )
    return steps


class ParamPtpPickPlaceNode(Node):
    """Run once from ax/ay/az and/or dx/dy/dz launch parameters."""

    def __init__(self) -> None:
        super().__init__("param_ptp_pick_place")
        dynamic_descriptor = ParameterDescriptor(dynamic_typing=True)
        for name in ["ax", "ay", "az", "dx", "dy", "dz"]:
            self.declare_parameter(name, "", descriptor=dynamic_descriptor)
        self.declare_parameter("dry_run", False)
        self.declare_parameter("ptp_action_name", "PTP_action")
        self.declare_parameter("suction_service_name", "dobot_suction_cup_service")
        self.declare_parameter("validation_service_name", "dobot_PTP_validation_service")
        self.declare_parameter("velocity_ratio", 0.3)
        self.declare_parameter("acceleration_ratio", 0.3)
        self.declare_parameter("action_server_timeout_sec", 5.0)
        self.declare_parameter("motion_goal_timeout_sec", 5.0)
        self.declare_parameter("motion_result_timeout_sec", 120.0)
        self.declare_parameter("suction_service_timeout_sec", 5.0)
        self.declare_parameter("suction_response_timeout_sec", 10.0)
        self.declare_parameter("validation_service_timeout_sec", 10.0)
        self.declare_parameter("validation_response_timeout_sec", 10.0)

        self._action_client = None
        if PointToPoint is not None:
            self._action_client = ActionClient(
                self,
                PointToPoint,
                str(self.get_parameter("ptp_action_name").value),
            )
        self._validation_client = None
        if EvaluatePTPTrajectory is not None:
            self._validation_client = self.create_client(
                EvaluatePTPTrajectory,
                str(self.get_parameter("validation_service_name").value),
            )
        self._suction_client = None
        if SuctionCupControl is not None:
            self._suction_client = self.create_client(
                SuctionCupControl,
                str(self.get_parameter("suction_service_name").value),
            )

    def run_once(self) -> bool:
        """Build and execute the requested complete groups only."""
        try:
            param_names = ["ax", "ay", "az", "dx", "dy", "dz"]
            values = {name: self.get_parameter(name).value for name in param_names}
            attach, attach_missing = _triplet_from_values(values, "a")
            detach, detach_missing = _triplet_from_values(values, "d")
            steps = build_param_ptp_steps(attach=attach, detach=detach)
        except ValueError as exc:
            self.get_logger().error(f"[blocker] invalid parameters: {exc}")
            return False

        if attach is None and attach_missing and len(attach_missing) < 3:
            self.get_logger().warn(
                "[skip] attach group incomplete; missing=%s" % ",".join(attach_missing)
            )
        if detach is None and detach_missing and len(detach_missing) < 3:
            self.get_logger().warn(
                "[skip] detach group incomplete; missing=%s" % ",".join(detach_missing)
            )
        if not steps:
            self.get_logger().error(
                "[blocker] no complete xyz group; provide ax,ay,az and/or dx,dy,dz"
            )
            return False

        self.get_logger().info(
            "[plan] attach=%s detach=%s steps=%d hover_offset_m=%.3f"
            % (attach, detach, len(steps), DEFAULT_HOVER_OFFSET_M)
        )
        for step in steps:
            if step.kind == "move":
                if step.motion_type is None or step.target_pose is None:
                    self.get_logger().error(f"[blocker] malformed move step: {step.label}")
                    return False
                if self._dry_run():
                    self.get_logger().info(
                        "[dry-run] %s motion_type=%d target_pose=%s"
                        % (step.label, step.motion_type, step.target_pose)
                    )
                    continue
                if not self._send_motion_goal(step.motion_type, step.target_pose):
                    self.get_logger().error(
                        "[blocker] sequence incomplete; failed_step=%s" % step.label
                    )
                    return False
                continue
            if step.kind == "suction":
                if step.suction_enabled is None:
                    self.get_logger().error(f"[blocker] malformed suction step: {step.label}")
                    return False
                if self._dry_run():
                    self.get_logger().info(
                        "[dry-run] %s enable_suction=%s" % (step.label, step.suction_enabled)
                    )
                    continue
                if not self._send_suction_request(step.suction_enabled):
                    self.get_logger().error(
                        "[blocker] sequence incomplete; failed_step=%s" % step.label
                    )
                    return False
                continue
            self.get_logger().error(f"[blocker] unsupported step kind: {step.kind}")
            return False

        self.get_logger().info("[done] param PTP pick/place sequence completed")
        return True

    def _dry_run(self) -> bool:
        value = self.get_parameter("dry_run").value
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def _normalize_graph_name(name: str) -> str:
        return name if name.startswith("/") else f"/{name}"

    def _available_action_names(self) -> list[str]:
        try:
            return sorted(name for name, _types in get_action_names_and_types(self))
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

    def _validate_motion_target(self, motion_type: int, target_pose: list[float]) -> bool:
        if EvaluatePTPTrajectory is None or self._validation_client is None:
            self.get_logger().warn(
                "[warn] dobot_msgs.srv.EvaluatePTPTrajectory import 실패; 사전 검증을 건너뜁니다"
            )
            return True
        if not self._validation_client.wait_for_service(
            timeout_sec=float(self.get_parameter("validation_service_timeout_sec").value)
        ):
            requested = self._normalize_graph_name(
                str(self.get_parameter("validation_service_name").value)
            )
            available = ", ".join(self._available_service_names()) or "(none)"
            self.get_logger().error(
                "[blocker] PTP validation service가 없습니다: "
                f"required={requested}, available_services={available}"
            )
            self._log_robot_bringup_hint()
            return False
        request = EvaluatePTPTrajectory.Request()
        request.target = [float(value) for value in target_pose]
        request.motion_type = int(motion_type)
        future = self._validation_client.call_async(request)
        rclpy.spin_until_future_complete(
            self,
            future,
            timeout_sec=float(self.get_parameter("validation_response_timeout_sec").value),
        )
        response = future.result()
        if response is None:
            self.get_logger().error("[blocker] PTP validation response timeout")
            return False
        if not bool(response.is_valid):
            self.get_logger().error(
                "[blocker] PTP validation failed: motion_type=%d target_pose=%s reason=%s"
                % (motion_type, target_pose, response.message)
            )
            return False
        self.get_logger().info(
            "[validation ok] motion_type=%d target_pose=%s message=%s"
            % (motion_type, target_pose, response.message)
        )
        return True

    def _send_motion_goal(self, motion_type: int, target_pose: list[float]) -> bool:
        self.get_logger().info(
            "[target] motion_type=%d target_pose=%s" % (motion_type, target_pose)
        )
        if not self._validate_motion_target(motion_type, target_pose):
            return False
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
        self.get_logger().info(
            f"[motion done] status={status_name} achieved_pose={achieved_pose}"
        )
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
    node = ParamPtpPickPlaceNode()
    try:
        ok = node.run_once()
        if not ok:
            node.get_logger().error("[done] param PTP pick/place failed or skipped")
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
